"""이력서 업로드, 조회, 편집과 원본 다운로드를 처리합니다."""

from fastapi import HTTPException, UploadFile
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.database import lock_sqlite_write
from app.modules.auth.auth_model import Account
from app.modules.jobs.jobs_service import MAX_SIZE, read_resume

from .cv_model import Resume
from .cv_schemas import ResumeEdit, ResumeSections, ResumeView


def view(row: Resume) -> ResumeView:
    """DB 초안에서 원본 이름과 구조화한 편집본을 반환합니다."""
    return ResumeView(
        filename=row.filename,
        content=row.content,
        sections=ResumeSections.model_validate_json(row.sections)
        if row.sections
        else None,
    )


def read(engine: Engine, owner: int) -> ResumeView | None:
    """로그인한 소유자의 초안을 반환합니다."""
    with Session(engine) as db:
        row = db.get(Resume, owner)
        return view(row) if row else None


def upload(engine: Engine, owner: int, file: UploadFile) -> ResumeView:
    """기존 이력서 추출 규칙을 사용해 원본과 초안을 저장합니다."""
    filename, content = read_resume(file)
    file.file.seek(0)
    original = file.file.read(MAX_SIZE)
    with Session(engine) as db, db.begin():
        lock_sqlite_write(db)
        db.get(Account, owner, with_for_update=True)
        row = db.get(Resume, owner)
        if row is None:
            row = Resume(
                owner_id=owner, filename=filename, original=original, content=content
            )
            db.add(row)
        else:
            row.filename, row.original, row.content = filename, original, content
        return view(row)


def edit(engine: Engine, owner: int, data: ResumeEdit) -> ResumeView:
    """직접 작성 또는 추출 텍스트 중 하나 이상을 소유자의 초안에 저장합니다."""
    content = data.content.strip()
    if not content and not (data.sections and any(data.sections.model_dump().values())):
        raise HTTPException(422, "이력서 내용을 입력하세요.")
    with Session(engine) as db, db.begin():
        lock_sqlite_write(db)
        db.get(Account, owner, with_for_update=True)
        row = db.get(Resume, owner, with_for_update=True)
        if row is None:
            row = Resume(owner_id=owner, filename="", original=b"", content=content)
            db.add(row)
        row.content = content
        if data.sections is not None:
            row.sections = data.sections.model_dump_json()
        return view(row)


def original(engine: Engine, owner: int) -> tuple[str, bytes]:
    """소유자의 원본을 반환합니다."""
    with Session(engine) as db:
        row = db.get(Resume, owner)
        if row is None or not row.filename:
            raise HTTPException(404, "이력서 원본이 없습니다.")
        return row.filename, row.original
