"""로그인 요청과 세션 응답의 구조를 정의합니다."""

from pydantic import BaseModel, EmailStr, Field


class Login(BaseModel):
    """로그인에 필요한 아이디와 비밀번호를 전달합니다."""

    username: str = Field(max_length=128)
    password: str = Field(max_length=256)


class Session(BaseModel):
    """인증된 세션과 연결된 직원 식별자를 반환합니다."""

    employee_id: str


class Signup(Login):
    """가입 이메일과 새 자격 증명을 검증합니다."""

    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=10, max_length=256)
    email: EmailStr = Field(max_length=254)


class Recovery(BaseModel):
    """가입 이메일과 복구 코드로 계정 소유 여부를 확인합니다."""

    email: EmailStr = Field(max_length=254)
    recovery_code: str = Field(min_length=20, max_length=100)


class Reset(Recovery):
    """새 비밀번호를 지정합니다."""

    password: str = Field(min_length=10, max_length=256)
