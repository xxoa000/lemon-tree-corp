"""로그인 요청과 세션 응답의 구조를 정의합니다."""

from pydantic import BaseModel, Field


class Login(BaseModel):
    """로그인에 필요한 아이디와 비밀번호를 전달합니다."""

    username: str = Field(max_length=128)
    password: str = Field(max_length=256)


class Session(BaseModel):
    """인증된 세션과 연결된 직원 식별자를 반환합니다."""

    employee_id: str
