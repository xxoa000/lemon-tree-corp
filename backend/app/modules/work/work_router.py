"""업무 페이지의 관리자 전용 Codex 실행 요청 API입니다."""

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import PlainTextResponse

from app.modules.auth.auth_profile import account_id, session_view
from app.modules.auth.auth_router import Subject

from . import work_images, work_service
from .work_schemas import Draft, WorkView


def admin(request: Request, subject: Subject, response: Response) -> int:
    """개발 요청 및 결과는 관리자에게만 공개합니다."""
    response.headers["Cache-Control"] = "private, no-store"
    if (
        not subject.startswith("acct:")
        or session_view(request.app.state.workplace_engine, subject).role != "admin"
    ):
        raise HTTPException(403, "관리자 권한이 필요합니다.")
    return account_id(subject)


Admin = Annotated[int, Depends(admin)]


router = APIRouter(prefix="/api/v1/codex-work", dependencies=[Depends(admin)])


@router.get("")
def dashboard(request: Request) -> dict:
    """최근 요청과 직원별 예산을 보여줍니다."""
    return work_service.dashboard(request.app.state.workplace_engine)


@router.post("", status_code=201)
def create(request: Request, data: Draft, actor: Admin) -> WorkView:
    """개발 요청을 초안으로 등록합니다."""
    return work_service.create(request.app.state.workplace_engine, actor, data)


@router.post("/with-images", status_code=201)
def create_with_images(
    request: Request,
    actor: Admin,
    employee_id: Annotated[str, Form(min_length=1, max_length=24)],
    title: Annotated[str, Form(min_length=1, max_length=120)],
    prompt: Annotated[str, Form(min_length=1, max_length=6000)],
    images: Annotated[list[UploadFile], File()],
) -> WorkView:
    """이미지와 개발 요청을 함께 저장합니다."""
    from pydantic import ValidationError

    try:
        data = Draft(employee_id=employee_id, title=title, prompt=prompt)
    except ValidationError as error:
        raise HTTPException(
            422, "담당 직원, 제목과 개발 요청을 입력해 주세요."
        ) from error
    return work_service.create(
        request.app.state.workplace_engine, actor, data, work_images.normalize(images)
    )


@router.get("/{job_id}/images/{position}")
def image(request: Request, job_id: int, position: int) -> Response:
    """권한이 있는 관리자에게 첨부 이미지를 반환합니다."""
    return Response(
        work_service.image_content(
            request.app.state.workplace_engine, job_id, position
        ),
        media_type="image/png",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/{job_id}/approve")
def approve(request: Request, job_id: int, actor: Admin) -> WorkView:
    """승인된 요청을 실행 대기열에 등록합니다."""
    return work_service.approve(request.app.state.workplace_engine, actor, job_id)


@router.get("/{job_id}/patch", response_class=PlainTextResponse)
def patch(request: Request, job_id: int) -> PlainTextResponse:
    """작업 공간에서 수집한 변경 내역을 표시합니다."""
    return PlainTextResponse(
        work_service.patch(request.app.state.workplace_engine, job_id),
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
