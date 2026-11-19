"""관리자가 직원별 가상 예산을 조회하는 API입니다."""

from fastapi import APIRouter, Request, Response

from app.modules.auth.auth_router import Subject

from . import llm_service
from .llm_schemas import BudgetEdit, BudgetView

router = APIRouter(prefix="/api/v1/llm")


@router.get("/budgets")
def budgets(request: Request, response: Response, subject: Subject) -> list[BudgetView]:
    """직원 가상 연봉, 월 예산과 사용액을 조회합니다."""
    response.headers["Cache-Control"] = "private, no-store"
    return llm_service.summaries(request.app.state.workplace_engine, subject)


@router.patch("/budgets/{employee}", status_code=204)
def edit_budget(
    employee: str, data: BudgetEdit, request: Request, subject: Subject
) -> None:
    """직원 연봉과 월 예산 한도를 변경합니다."""
    llm_service.edit_budget(request.app.state.workplace_engine, subject, employee, data)
