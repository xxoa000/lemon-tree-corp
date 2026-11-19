"""TechVlog 글 조회, 생성, 수정과 삭제 API입니다."""

from fastapi import APIRouter, Request

from app.modules.auth.auth_profile import account_id
from app.modules.auth.auth_router import Subject

from . import vlog_service
from .vlog_schemas import Article, Draft

router = APIRouter(prefix="/api/v1/vlog")


@router.get("")
def list_posts(request: Request) -> list[Article]:
    """릴리스 노트와 게시글을 조회합니다."""
    return vlog_service.list_posts(request.app.state.workplace_engine)


@router.post("", status_code=201)
def create(data: Draft, request: Request, subject: Subject) -> Article:
    """로그인한 사용자의 새 게시글을 등록합니다."""
    return vlog_service.save(
        request.app.state.workplace_engine, account_id(subject), data
    )


@router.patch("/{post_id}")
def update(post_id: int, data: Draft, request: Request, subject: Subject) -> Article:
    """작성자 또는 관리자가 글을 수정합니다."""
    return vlog_service.save(
        request.app.state.workplace_engine, account_id(subject), data, post_id
    )


@router.delete("/{post_id}", status_code=204)
def remove(post_id: int, request: Request, subject: Subject) -> None:
    """작성자 또는 관리자가 글을 삭제합니다."""
    vlog_service.remove(
        request.app.state.workplace_engine, account_id(subject), post_id
    )
