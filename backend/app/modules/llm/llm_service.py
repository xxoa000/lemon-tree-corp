"""외부 호출 없이 직원 모의 응답과 월 예산 예약·정산을 처리합니다."""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.database import lock_sqlite_write
from app.modules.auth.auth_profile import session_view
from app.modules.org.org_service import employees, manager

from .llm_model import Budget, Usage
from .llm_schemas import BudgetEdit, BudgetView

TOTAL_MONTHLY_LIMIT = 50_000


def month_key() -> str:
    """한국 시간 기준으로 현재 예산 월을 반환합니다."""
    return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m")


def mock_reply(employee_id: str, message: str) -> str:
    """직원 역할과 간단한 키워드로 로컬 모의 답장을 만듭니다."""
    person = next((row for row in employees() if row.id == employee_id), None)
    if any(word in message for word in ("이력서", "면접", "지원")):
        return "공고에서 직무를 선택하면 이력서 없이도 모의면접을 시작할 수 있어요. 가상의 프로젝트를 예로 들어 연습해 보세요."
    if any(word in message for word in ("예산", "비용", "연봉")):
        return (
            "지금은 가상 예산만 사용하고 있어요. 실제 모델 API에는 연결하지 않았습니다."
        )
    focus = person.specialty if person else "조직 운영과 기능 기획"
    return f"메시지 확인했습니다. {focus} 관점에서 살펴볼게요. 현재 상황과 원하는 결과를 한 가지씩 알려주시겠어요?"


def used_amount(db: Session, employee: str, month: str) -> int:
    """완료하거나 아직 예약 중인 비용을 합산합니다."""
    return (
        db.scalar(
            select(func.coalesce(func.sum(Usage.charged), 0)).where(
                Usage.employee_id == employee,
                Usage.month == month,
                Usage.state != "released",
            )
        )
        or 0
    )


def reserve(engine: Engine, employee: str, charge: int) -> int | None:
    """동시 요청에서도 월 한도를 넘기지 않게 예상 비용을 예약합니다."""
    with Session(engine) as db, db.begin():
        lock_sqlite_write(db)
        budget = db.get(Budget, employee, with_for_update=True)
        month = month_key()
        if (
            budget is None
            or used_amount(db, employee, month) + charge > budget.monthly_limit
        ):
            return None
        usage = Usage(
            employee_id=employee, month=month, charged=charge, state="reserved"
        )
        db.add(usage)
        db.flush()
        return usage.id


def settle(engine: Engine, usage_id: int, sent: bool) -> None:
    """답장을 저장했으면 정산하고 전송에 실패했으면 예약을 반환합니다."""
    with Session(engine) as db, db.begin():
        lock_sqlite_write(db)
        usage = db.get(Usage, usage_id, with_for_update=True)
        if usage and usage.state == "reserved":
            usage.state = "settled" if sent else "released"


def prepare(engine: Engine, employee: str, message: str) -> tuple[str, str, int | None]:
    """모의 답장과 가상 비용 예약을 준비합니다."""
    if os.getenv("WORKPLACE_LLM_MODE", "mock") != "mock":
        return "disabled", "", None
    reply = mock_reply(employee, message)
    charge = max(1, (len(message) + len(reply) + 49) // 50)
    reservation = reserve(engine, employee, charge)
    return (
        "ready" if reservation is not None else "budget_exhausted",
        reply,
        reservation,
    )


def summaries(engine: Engine, subject: str) -> list[BudgetView]:
    """관리자에게 월별 모의 사용 현황을 제공합니다."""
    if session_view(engine, subject).role != "admin":
        raise HTTPException(403, "관리자 권한이 필요합니다.")
    names = {row.id: row.name for row in employees()}
    system_manager = manager()
    names[system_manager.id] = system_manager.name
    month = month_key()
    with Session(engine) as db:
        return [
            BudgetView(
                employee_id=row.employee_id,
                name=names.get(row.employee_id, row.employee_id),
                salary=row.salary,
                monthly_limit=row.monthly_limit,
                used=used_amount(db, row.employee_id, month),
                month=month,
            )
            for row in db.scalars(select(Budget).order_by(Budget.employee_id))
        ]


def edit_budget(engine: Engine, subject: str, employee: str, data: BudgetEdit) -> None:
    """관리자만 직원 예산을 바꾸며 동시 예약과 충돌하지 않게 합니다."""
    if session_view(engine, subject).role != "admin":
        raise HTTPException(403, "관리자 권한이 필요합니다.")
    with Session(engine) as db, db.begin():
        lock_sqlite_write(db)
        budgets = list(
            db.scalars(select(Budget).order_by(Budget.employee_id).with_for_update())
        )
        row = next(
            (budget for budget in budgets if budget.employee_id == employee), None
        )
        if row is None:
            raise HTTPException(404, "직원 예산을 찾을 수 없습니다.")
        allocated = sum(budget.monthly_limit for budget in budgets)
        if allocated - row.monthly_limit + data.monthly_limit > TOTAL_MONTHLY_LIMIT:
            raise HTTPException(422, "전체 월 예산은 50,000원을 초과할 수 없습니다.")
        row.salary, row.monthly_limit = data.salary, data.monthly_limit
