"""Codex 작업의 요청, 예산과 검토 결과를 보관합니다."""

from sqlalchemy import ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.mysql import MEDIUMBLOB, MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Work(Base):
    """독립적으로 승인하고 실행하는 직원 작업 한 건입니다."""

    __tablename__ = "codex_work"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="작업 ID")
    employee_id: Mapped[str] = mapped_column(
        ForeignKey("llm_budgets.employee_id"), comment="담당 직원 사번"
    )
    title: Mapped[str] = mapped_column(String(120), comment="작업 제목")
    prompt: Mapped[str] = mapped_column(Text, comment="승인할 개발 요청")
    state: Mapped[str] = mapped_column(String(16), index=True, comment="작업 상태")
    progress: Mapped[str] = mapped_column(String(120), comment="최근 작업 단계")
    usage_id: Mapped[int | None] = mapped_column(
        ForeignKey("llm_usage.id"), comment="월 가상 예산 예약 ID"
    )
    expires_at: Mapped[int | None] = mapped_column(
        Integer, comment="작업 만료 시각의 유닉스 초"
    )
    tokens: Mapped[int | None] = mapped_column(
        Integer, comment="보고된 입력과 출력 토큰 합계"
    )
    summary: Mapped[str] = mapped_column(Text, comment="완료 또는 실패 요약")
    patch: Mapped[str] = mapped_column(
        Text().with_variant(MEDIUMTEXT(), "mysql"), comment="검토용 Git 패치"
    )


class Attachment(Base):
    """개발 요청에 첨부된 검증된 PNG입니다."""

    __tablename__ = "codex_work_images"

    work_id: Mapped[int] = mapped_column(
        ForeignKey("codex_work.id", ondelete="CASCADE"),
        primary_key=True,
        comment="첨부가 속한 작업 ID",
    )
    position: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="작업 내 첨부 순서"
    )
    name: Mapped[str] = mapped_column(String(255), comment="첨부 표시 이름")
    content: Mapped[bytes] = mapped_column(
        LargeBinary().with_variant(MEDIUMBLOB(), "mysql"),
        comment="정규화된 PNG 데이터",
    )
