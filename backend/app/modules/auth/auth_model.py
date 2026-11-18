"""가입 계정의 로그인 및 복구 정보를 저장합니다."""

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Account(Base):
    """자체 가입한 사용자 계정입니다."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="사용자 식별자")
    username: Mapped[str] = mapped_column(Text, unique=True, comment="로그인 아이디")
    email: Mapped[str] = mapped_column(Text, unique=True, comment="가입 이메일")
    password_hash: Mapped[str] = mapped_column(
        Text, comment="솔트가 포함된 비밀번호 해시"
    )
    recovery_hash: Mapped[str] = mapped_column(Text, comment="계정 복구 코드 해시")
    session_version: Mapped[int] = mapped_column(
        Integer, comment="현재 유효한 세션 버전"
    )
