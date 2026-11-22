"""지원 건과 면접 답변을 영속화하는 모델입니다."""

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Application(Base):
    """지원자의 이력서와 현재 전형 단계를 저장합니다."""

    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="지원 건 식별자")
    applicant: Mapped[str] = mapped_column(
        Text().with_variant(String(40), "mysql"),
        index=True,
        comment="지원자 세션 식별자",
    )
    role: Mapped[str] = mapped_column(
        Text().with_variant(String(20), "mysql"),
        server_default="backend",
        comment="지원한 공고의 직무 코드",
    )
    filename: Mapped[str] = mapped_column(Text, comment="제출한 이력서 파일명")
    resume: Mapped[str] = mapped_column(
        Text().with_variant(MEDIUMTEXT(), "mysql"), comment="이력서에서 추출한 텍스트"
    )
    stage: Mapped[str] = mapped_column(Text, comment="지원 건의 현재 전형")
    feedback: Mapped[str] = mapped_column(Text, comment="최근 전형의 결과 및 피드백")
    created_at: Mapped[str] = mapped_column(
        Text().with_variant(DateTime(), "mysql"),
        server_default=text("CURRENT_TIMESTAMP"),
        comment="지원 접수 시각(UTC)",
    )


class InterviewAnswer(Base):
    """질문별 응답과 평가를 기록합니다."""

    __tablename__ = "job_answers"
    __table_args__ = (UniqueConstraint("application_id", "question_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="응답 식별자")
    application_id: Mapped[int] = mapped_column(
        ForeignKey("job_applications.id"),
        comment="응답이 속한 지원 건 식별자",
    )
    question_id: Mapped[str] = mapped_column(
        Text().with_variant(String(30), "mysql"), comment="응답 대상 질문 식별자"
    )
    answer: Mapped[str] = mapped_column(Text, comment="지원자가 입력한 면접 답변")
    score: Mapped[int] = mapped_column(Integer, comment="질문 평가 기준의 충족 개수")

    evaluation: Mapped[str | None] = mapped_column(
        Text, comment="로컬 AI의 평가 항목과 피드백 JSON"
    )


class InterviewQuestion(Base):
    """답변이 제출되기 전에 생성 및 확정한 질문입니다."""

    __tablename__ = "job_questions"

    application_id: Mapped[int] = mapped_column(
        ForeignKey("job_applications.id"),
        primary_key=True,
        comment="지원 건 식별자",
    )
    question_id: Mapped[str] = mapped_column(
        String(30), primary_key=True, comment="전형 내 질문 식별자"
    )
    prompt: Mapped[str] = mapped_column(Text, comment="생성된 질문 원문")
    criteria: Mapped[str] = mapped_column(
        Text, comment="답변 전에 확정한 세 평가 기준 JSON"
    )
