"""마이페이지의 비공개 이력서 API입니다."""

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, File, Request, Response, UploadFile

from app.modules.auth.auth_profile import account_id
from app.modules.auth.auth_router import Subject

from . import cv_service
from .cv_schemas import ResumeEdit, ResumeView

router = APIRouter(prefix="/api/v1/accounts/me/resume")


@router.get("")
def resume(request: Request, subject: Subject, response: Response) -> ResumeView | None:
    """내 이력서 초안을 조회합니다."""
    response.headers["Cache-Control"] = "private, no-store"
    return cv_service.read(request.app.state.workplace_engine, account_id(subject))


@router.put("/file")
def upload(
    request: Request, subject: Subject, file: Annotated[UploadFile, File()]
) -> ResumeView:
    """이력서 파일을 업로드하거나 교체합니다."""
    return cv_service.upload(
        request.app.state.workplace_engine, account_id(subject), file
    )


@router.patch("")
def edit(data: ResumeEdit, request: Request, subject: Subject) -> ResumeView:
    """이력서 초안의 텍스트를 갱신합니다."""
    return cv_service.edit(
        request.app.state.workplace_engine, account_id(subject), data.content
    )


@router.get("/file")
def download(request: Request, subject: Subject) -> Response:
    """내 이력서 원본을 첨부 형식으로 다운로드합니다."""
    name, data = cv_service.original(
        request.app.state.workplace_engine, account_id(subject)
    )
    return Response(
        data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": "attachment; filename*=UTF-8''"
            + quote(name, safe=""),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
