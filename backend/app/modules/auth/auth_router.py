"""JWT 쿠키를 사용하는 로그인, 세션 조회, 로그아웃 경로를 등록합니다."""

import os
from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile

from . import auth_profile, auth_service
from .auth_schemas import (
    AccountProfile,
    Login,
    ProfileUpdate,
    Recovery,
    Reset,
    Session,
    Signup,
    StaffAccount,
)

router = APIRouter(prefix="/api/v1")
COOKIE = "lemontree_session"


def session_employee(request: Request) -> str:
    """요청의 세션 쿠키에서 인증된 직원 식별자를 확인합니다."""
    return auth_service.authenticated_employee(
        request.app.state.workplace_engine, request.cookies.get(COOKIE)
    )


@router.post("/session")
def login(credentials: Login, response: Response, request: Request) -> Session:
    """로그인에 성공하면 JWT를 HTTP 전용 쿠키에 저장합니다."""
    subject, token = auth_service.issue_token(
        request.app.state.workplace_engine, credentials
    )
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(
        COOKIE,
        token,
        max_age=auth_service.SESSION_SECONDS,
        httponly=True,
        samesite="strict",
        secure=os.getenv("WORKPLACE_SECURE_COOKIE") == "1",
    )
    return auth_profile.session_view(request.app.state.workplace_engine, subject)


@router.get("/session")
def session(request: Request, response: Response) -> Session:
    """현재 세션에 연결된 직원 식별자를 응답합니다."""
    response.headers["Cache-Control"] = "no-store"
    return auth_profile.session_view(
        request.app.state.workplace_engine, session_employee(request)
    )


@router.delete("/session", status_code=204)
def logout(response: Response) -> None:
    """브라우저에서 세션 쿠키를 제거합니다."""
    response.delete_cookie(COOKIE)


@router.post("/accounts", status_code=201)
def signup(data: Signup, request: Request, response: Response) -> dict[str, str]:
    """신규 계정을 만들고 복구 코드를 응답합니다."""
    response.headers["Cache-Control"] = "no-store"
    return {
        "recovery_code": auth_service.signup(request.app.state.workplace_engine, data)
    }


@router.post("/accounts/find")
def find_username(
    data: Recovery, request: Request, response: Response
) -> dict[str, str]:
    """복구 코드를 검증하고 아이디를 응답합니다."""
    response.headers["Cache-Control"] = "no-store"
    return {
        "username": auth_service.find_username(request.app.state.workplace_engine, data)
    }


@router.post("/accounts/reset")
def reset_password(data: Reset, request: Request, response: Response) -> dict[str, str]:
    """새 비밀번호를 설정하고 새 복구 코드를 응답합니다."""
    response.headers["Cache-Control"] = "no-store"
    response.delete_cookie(COOKIE)
    return {
        "recovery_code": auth_service.reset_password(
            request.app.state.workplace_engine, data
        )
    }


Subject = Annotated[str, Depends(session_employee)]


def task_employee(request: Request, subject: Subject) -> str:
    """업무 권한에 사용할 조직 식별자를 확인합니다."""
    return (
        auth_profile.session_view(
            request.app.state.workplace_engine, subject
        ).org_employee_id
        or subject
    )


@router.get("/accounts/me")
def profile(request: Request, response: Response, subject: Subject) -> AccountProfile:
    """내 마이페이지에 표시할 정보를 반환합니다."""
    response.headers["Cache-Control"] = "private, no-store"
    return auth_profile.read_profile(request.app.state.workplace_engine, subject)


@router.patch("/accounts/me")
def update_profile(
    data: ProfileUpdate, request: Request, subject: Subject
) -> AccountProfile:
    """로그인한 계정의 회원정보를 수정합니다."""
    return auth_profile.update_profile(
        request.app.state.workplace_engine, subject, data
    )


@router.get("/accounts/me/avatar")
def avatar(request: Request, subject: Subject) -> Response:
    """내 프로필 이미지를 반환합니다."""
    return Response(
        auth_profile.read_avatar(request.app.state.workplace_engine, subject),
        media_type="image/webp",
        headers={"Cache-Control": "private, no-store"},
    )


@router.put("/accounts/me/avatar", status_code=204)
def update_avatar(
    request: Request, subject: Subject, image: Annotated[UploadFile, File()]
) -> None:
    """내 프로필 이미지를 검사 후 교체합니다."""
    auth_profile.update_avatar(request.app.state.workplace_engine, subject, image)


@router.get("/accounts/staff")
def staff(request: Request, response: Response, subject: Subject) -> list[StaffAccount]:
    """관리자에게 직원 계정 목록을 제공합니다."""
    response.headers["Cache-Control"] = "private, no-store"
    return auth_profile.list_staff(request.app.state.workplace_engine, subject)
