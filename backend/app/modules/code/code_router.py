"""로그인 사용자를 위한 코딩 연습 풀이 API입니다."""

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response

from app.modules.auth.auth_profile import account_id
from app.modules.auth.auth_router import Subject

from . import code_service
from .code_schemas import DraftEdit

router = APIRouter(prefix="/api/v1/practice")


@router.get("/drafts")
def drafts(request: Request, response: Response, subject: Subject) -> list[str]:
    """이전에 풀이를 저장한 문제를 반환합니다."""
    response.headers["Cache-Control"] = "private, no-store"
    return code_service.problems(
        request.app.state.workplace_engine, account_id(subject)
    )


@router.get("/draft")
def read(
    request: Request,
    response: Response,
    subject: Subject,
    problem: Annotated[str, Query(max_length=255)],
) -> DraftEdit | None:
    """현재 문제의 저장된 풀이를 반환합니다."""
    response.headers["Cache-Control"] = "private, no-store"
    return code_service.read(
        request.app.state.workplace_engine, account_id(subject), problem
    )


@router.put("/draft")
def update(
    data: DraftEdit,
    request: Request,
    subject: Subject,
    problem: Annotated[str, Query(max_length=255)],
) -> DraftEdit:
    """현재 문제의 풀이를 저장합니다."""
    return code_service.save(
        request.app.state.workplace_engine, account_id(subject), problem, data
    )
