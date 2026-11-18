"""업무와 업무 상태 변경 이력을 저장하는 SQLAlchemy 모델을 정의합니다."""

from sqlalchemy import CheckConstraint, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

from .task_schemas import Status


class Task(Base):
    """업무 보드의 업무 한 건을 저장합니다."""

    __tablename__ = "tasks"
    __table_args__ = (CheckConstraint("status IN ('todo', 'in_progress', 'done')"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True, comment="업무 식별자")
    title: Mapped[str] = mapped_column(Text, comment="업무 제목")
    description: Mapped[str] = mapped_column(Text, comment="업무 상세 설명")
    assignee_id: Mapped[str] = mapped_column(Text, comment="업무를 담당하는 직원 식별자")
    status: Mapped[Status] = mapped_column(Text, comment="현재 업무 상태")


class TaskEvent(Base):
    """담당자가 변경한 업무 상태를 기록합니다."""

    __tablename__ = "task_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="업무 변경 기록 식별자")
    task_id: Mapped[str] = mapped_column(Text, comment="상태가 바뀐 업무 식별자")
    actor_id: Mapped[str] = mapped_column(Text, comment="상태를 변경한 직원 식별자")
    previous_status: Mapped[Status] = mapped_column(Text, comment="변경 전 업무 상태")
    status: Mapped[Status] = mapped_column(Text, comment="변경 후 업무 상태")
    occurred_at: Mapped[str] = mapped_column(
        Text, server_default=text("CURRENT_TIMESTAMP"), comment="상태 변경 시각(UTC)",
    )
