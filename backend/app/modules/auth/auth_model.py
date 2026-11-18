"""가입 계정의 로그인 및 복구 정보를 저장합니다."""

from sqlalchemy import Index, Integer, LargeBinary, String, Text, text
from sqlalchemy.dialects.mysql import MEDIUMBLOB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

from .auth_schemas import Role


class Account(Base):
    """자체 가입한 사용자 계정입니다."""

    __tablename__ = "accounts"
    __table_args__ = (Index("uq_accounts_employee_id", "employee_id", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="사용자 식별자")
    username: Mapped[str] = mapped_column(
        Text().with_variant(String(40), "mysql"), unique=True, comment="로그인 아이디"
    )
    email: Mapped[str] = mapped_column(
        Text().with_variant(String(254), "mysql"), unique=True, comment="가입 이메일"
    )
    password_hash: Mapped[str | None] = mapped_column(
        Text, comment="솔트가 포함된 비밀번호 해시"
    )
    recovery_hash: Mapped[str | None] = mapped_column(
        Text, comment="계정 복구 코드 해시"
    )
    session_version: Mapped[int] = mapped_column(
        Integer, comment="현재 유효한 세션 버전"
    )
    role: Mapped[Role] = mapped_column(
        String(12), server_default="member", comment="계정 권한"
    )
    employee_id: Mapped[str | None] = mapped_column(
        String(24), comment="연결된 조직 구성원 식별자"
    )
    display_name: Mapped[str] = mapped_column(
        String(80), server_default=text("''"), comment="프로필 표시 이름"
    )
    phone: Mapped[str] = mapped_column(
        String(32), server_default=text("''"), comment="연락처 전화번호"
    )
    bio: Mapped[str] = mapped_column(
        String(1000), server_default=text("''"), comment="프로필 자기소개"
    )
    avatar: Mapped[bytes | None] = mapped_column(
        LargeBinary().with_variant(MEDIUMBLOB(), "mysql"),
        deferred=True,
        comment="정규화된 WebP 프로필 이미지",
    )
