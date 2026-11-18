"""로컬 리뷰 계정 인증과 JWT 발급 및 검증을 담당합니다."""

import hmac
import os
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException

from .auth_schemas import Login

EMPLOYEE_ID = "LT-011"
SESSION_SECONDS = 8 * 60 * 60


def configured_secret() -> str:
    """설정된 JWT 서명 키의 최소 길이를 확인합니다."""
    secret = os.getenv("WORKPLACE_JWT_SECRET", "")
    if len(secret.encode()) < 32:
        raise HTTPException(503, "로그인 설정이 필요합니다.")
    return secret


def issue_token(credentials: Login) -> str:
    """리뷰 계정을 인증하고 만료 시간이 있는 JWT를 발급합니다."""
    password = os.getenv("WORKPLACE_PASSWORD", "")
    if not password:
        raise HTTPException(503, "로그인 설정이 필요합니다.")
    secret = configured_secret()
    valid_password = hmac.compare_digest(credentials.password.encode(), password.encode())
    if credentials.username != os.getenv("WORKPLACE_USERNAME", "junior") or not valid_password:
        raise HTTPException(401, "아이디 또는 비밀번호를 확인해 주세요.")

    now = datetime.now(UTC)
    return jwt.encode(
        {"sub": EMPLOYEE_ID, "iat": now, "exp": now + timedelta(seconds=SESSION_SECONDS)},
        secret, algorithm="HS256",
    )


def authenticated_employee(token: str | None) -> str:
    """JWT를 검증하고 연결된 직원 식별자를 반환합니다."""
    if token:
        try:
            claims = jwt.decode(
                token, configured_secret(), algorithms=["HS256"],
                options={"require": ["exp", "iat", "sub"]},
            )
            if claims["sub"] == EMPLOYEE_ID:
                return EMPLOYEE_ID
        except jwt.InvalidTokenError:
            pass
    raise HTTPException(401, "로그인이 필요합니다.")
