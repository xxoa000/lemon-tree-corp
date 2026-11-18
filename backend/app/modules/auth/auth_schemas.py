"""로그인 요청과 세션 응답의 구조를 정의합니다."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Role = Literal["member", "admin"]


class Login(BaseModel):
    """로그인에 필요한 아이디와 비밀번호를 전달합니다."""

    username: str = Field(max_length=128)
    password: str = Field(max_length=256)


class Session(BaseModel):
    """인증된 세션과 연결된 직원 식별자를 반환합니다."""

    employee_id: str
    org_employee_id: str | None = None
    role: Role = "member"


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


class ProfileUpdate(BaseModel):
    """본인이 변경할 수 있는 프로필 필드를 받습니다."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    display_name: str = Field(min_length=1, max_length=80)
    email: EmailStr = Field(max_length=254)
    phone: str = Field(max_length=32)
    bio: str = Field(max_length=1000)


class AccountProfile(BaseModel):
    """비공개 마이페이지에 필요한 본인의 계정 정보를 응답합니다."""

    username: str
    display_name: str
    email: str
    phone: str
    bio: str
    role: Role
    has_avatar: bool


class StaffAccount(BaseModel):
    """관리자가 조회하는 직원 계정의 요약 정보입니다."""

    employee_id: str
    username: str
    display_name: str
    role: Role
    enabled: bool
