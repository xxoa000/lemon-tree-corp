"""사용자의 문제별 코드 풀이 초안을 저장합니다."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

from .code_schemas import Language


class Draft(Base):
    """한 계정의 문제별 최신 풀이입니다."""

    __tablename__ = "code_drafts"

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"), primary_key=True, comment="풀이 소유자"
    )
    problem: Mapped[str] = mapped_column(
        String(255), primary_key=True, comment="로컬 문제 키 또는 외부 문제 URL"
    )
    language: Mapped[Language] = mapped_column(
        String(24), comment="사용자가 선택한 언어"
    )
    code: Mapped[str] = mapped_column(Text, comment="저장한 소스 코드")
