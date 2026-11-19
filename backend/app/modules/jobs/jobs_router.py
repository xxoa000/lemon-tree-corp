"""공고, 지원 이력 및 면접 답변 API를 제공합니다."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile

from app.modules.auth.auth_router import session_employee

from . import jobs_service
from .jobs_schemas import Answer, ApplicationView, Posting

router = APIRouter(prefix="/api/v1/jobs")
Applicant = Annotated[str, Depends(session_employee)]


@router.get("/posting")
def posting() -> Posting:
    """공개된 주니어 백엔드 개발자 공고를 조회합니다."""
    return jobs_service.posting()


@router.get("/postings")
def postings() -> list[Posting]:
    """모든 채용 공고를 조회합니다."""
    return jobs_service.postings()


@router.get("/applications")
def applications(
    request: Request, response: Response, applicant: Applicant
) -> list[ApplicationView]:
    """로그인한 지원자의 지원 내역을 조회합니다."""
    response.headers["Cache-Control"] = "no-store"
    return jobs_service.applications(request.app.state.workplace_engine, applicant)


@router.post("/applications", status_code=201)
def apply(
    request: Request,
    applicant: Applicant,
    resume: Annotated[UploadFile | None, File()] = None,
    role: Annotated[str, Form(max_length=20)] = "backend",
) -> ApplicationView:
    """이력서를 접수하고 서류 심사 결과를 기록합니다."""
    return jobs_service.apply(
        request.app.state.workplace_engine, applicant, resume, role
    )


@router.post("/applications/{application_id}/answers")
def answer(
    application_id: int, data: Answer, request: Request, applicant: Applicant
) -> ApplicationView:
    """현재 면접 질문에 대한 답변을 처리합니다."""
    return jobs_service.submit_answer(
        request.app.state.workplace_engine, applicant, application_id, data
    )
