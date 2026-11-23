"""개발 요청 승인, 월 가상 예산 예약 및 작업 상태를 관리합니다."""

import time
from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, defer

from app.database import lock_sqlite_write
from app.modules.llm.llm_model import Budget, Usage
from app.modules.llm.llm_service import month_key, reserve_usage, used_amount
from app.modules.org.org_service import employees, manager

from .work_model import Attachment, Work
from .work_schemas import Draft, ImageView, WorkView

VIRTUAL_CHARGE = 500
RUN_TIMEOUT = 360
QUEUE_TIMEOUT = 86400


def view(
    row: Work, has_patch: bool | None = None, images: list[ImageView] | None = None
) -> WorkView:
    """작업 목록에 표시할 진행 상황과 검토 가능 여부를 반환합니다."""
    return WorkView(
        id=row.id,
        employee_id=row.employee_id,
        title=row.title,
        prompt=row.prompt,
        state=row.state,
        progress=row.progress,
        tokens=row.tokens,
        summary=row.summary,
        has_patch=bool(row.patch) if has_patch is None else has_patch,
        images=images or [],
    )


def dashboard(engine: Engine) -> dict:
    """담당 직원의 가상 예산 잔액과 최근 개발 요청을 반환합니다."""
    staff_names = {person.id: person.name for person in [*employees(), manager()]}
    with Session(engine) as db:
        rows = list(
            db.execute(
                select(Work, Work.patch != "")
                .options(defer(Work.patch))
                .order_by(Work.id.desc())
                .limit(40)
            )
        )
        metadata = image_metadata(db, [row.id for row, _ in rows])
        return {
            "charge": VIRTUAL_CHARGE,
            "staff": [
                {
                    "id": budget.employee_id,
                    "name": staff_names.get(budget.employee_id, budget.employee_id),
                    "salary": budget.salary,
                    "remaining": max(
                        0,
                        budget.monthly_limit
                        - used_amount(db, budget.employee_id, month_key()),
                    ),
                }
                for budget in db.scalars(select(Budget).order_by(Budget.employee_id))
            ],
            "jobs": [view(row, available, metadata[row.id]) for row, available in rows],
        }


def image_metadata(db: Session, job_ids: list[int]) -> dict[int, list[ImageView]]:
    """목록에는 이미지 데이터 없이 표시 정보만 묶어서 조회합니다."""
    metadata: dict[int, list[ImageView]] = defaultdict(list)
    if job_ids:
        rows = db.execute(
            select(Attachment.work_id, Attachment.position, Attachment.name)
            .where(Attachment.work_id.in_(job_ids))
            .order_by(Attachment.position)
        )
        for job_id, position, name in rows:
            metadata[job_id].append(ImageView(position=position, name=name))
    return metadata


def image_content(engine: Engine, job_id: int, position: int) -> bytes:
    """관리자가 미리 볼 한 장의 PNG를 반환합니다."""
    with Session(engine) as db:
        attachment = db.get(Attachment, (job_id, position))
        if attachment is None:
            raise HTTPException(404, "첨부 이미지를 찾을 수 없습니다.")
        return attachment.content


def execution_images(engine: Engine, job_id: int) -> list[bytes]:
    """승인된 작업을 실행할 때 첨부 PNG를 원래 순서로 반환합니다."""
    with Session(engine) as db:
        return list(
            db.scalars(
                select(Attachment.content)
                .where(Attachment.work_id == job_id)
                .order_by(Attachment.position)
            )
        )


def create(
    engine: Engine, data: Draft, images: list[tuple[str, bytes]] | None = None
) -> WorkView:
    """선택한 직원의 요청을 승인 대기 상태로 저장합니다."""
    with Session(engine) as db, db.begin():
        if db.get(Budget, data.employee_id) is None:
            raise HTTPException(422, "담당 직원을 확인해 주세요.")
        row = Work(
            **data.model_dump(),
            state="draft",
            progress="승인 대기",
            summary="",
            patch="",
        )
        db.add(row)
        db.flush()
        attachments = [
            Attachment(work_id=row.id, position=position, name=name, content=content)
            for position, (name, content) in enumerate(images or [], 1)
        ]
        db.add_all(attachments)
        return view(
            row,
            images=[
                ImageView(position=image.position, name=image.name)
                for image in attachments
            ],
        )


def job(db: Session, job_id: int, lock: bool = False) -> Work:
    """요청한 작업을 읽고 필요하면 갱신 잠금을 얻습니다."""
    row = db.get(Work, job_id, with_for_update=lock)
    if row is None:
        raise HTTPException(404, "개발 요청을 찾을 수 없습니다.")
    return row


def approve(engine: Engine, job_id: int) -> WorkView:
    """중복 승인 없이 월 예산을 예약하고 실행 대기열에 등록합니다."""
    with Session(engine) as db, db.begin():
        lock_sqlite_write(db)
        row = job(db, job_id, lock=True)
        images = image_metadata(db, [job_id])[job_id]
        if row.state != "draft":
            return view(row, images=images)
        usage = reserve_usage(db, row.employee_id, VIRTUAL_CHARGE)
        if usage is None:
            raise HTTPException(409, "담당 직원의 월 가상 예산이 부족합니다.")
        row.usage_id = usage.id
        row.state, row.progress = "queued", "실행기 대기"
        row.expires_at = int(time.time()) + QUEUE_TIMEOUT
        return view(row, images=images)


def patch(engine: Engine, job_id: int) -> str:
    """검토 가능한 Git 변경 내용을 반환합니다."""
    with Session(engine) as db:
        row = job(db, job_id)
        if not row.patch:
            raise HTTPException(404, "검토할 변경이 없습니다.")
        return row.patch


def update_result(
    db: Session,
    row: Work,
    summary: str,
    *,
    success: bool = False,
    started: bool = False,
    tokens: int | None = None,
    changes: str = "",
) -> None:
    """실행 결과와 가상 예산 정산을 같은 트랜잭션으로 기록합니다."""
    row.state = "review" if success else "failed"
    row.progress = "리뷰 준비" if success else "실행 중단"
    row.summary, row.patch, row.tokens = summary, changes, tokens
    row.expires_at = None
    usage = db.get(Usage, row.usage_id) if row.usage_id is not None else None
    if usage and usage.state == "reserved":
        usage.state = "settled" if started else "released"


def claim(engine: Engine) -> WorkView | None:
    """기한이 지난 작업을 정리하고 승인된 요청을 한 실행기에 배정합니다."""
    now = int(time.time())
    with Session(engine) as db, db.begin():
        lock_sqlite_write(db)
        expired = db.scalars(
            select(Work)
            .where(Work.state.in_(("queued", "running")), Work.expires_at <= now)
            .with_for_update()
        )
        for row in expired:
            update_result(
                db,
                row,
                "실행기 응답 시간이 만료됐습니다.",
                started=row.state == "running",
            )
        row = db.scalar(
            select(Work)
            .where(Work.state == "queued")
            .order_by(Work.id)
            .limit(1)
            .with_for_update()
        )
        if row is None:
            return None
        row.state, row.progress = "running", "격리된 작업 공간 준비"
        row.expires_at = now + RUN_TIMEOUT + 180
        return view(row)


def progress(engine: Engine, job_id: int, label: str) -> None:
    """실행 이벤트에 대응하는 단계만 저장합니다."""
    with Session(engine) as db, db.begin():
        lock_sqlite_write(db)
        row = job(db, job_id, lock=True)
        if row.state == "running":
            row.progress = label


def finish(engine: Engine, job_id: int, summary: str, **result) -> None:
    """아직 실행 중인 요청에만 결과를 기록합니다."""
    with Session(engine) as db, db.begin():
        lock_sqlite_write(db)
        row = job(db, job_id, lock=True)
        if row.state == "running":
            update_result(db, row, summary, **result)
