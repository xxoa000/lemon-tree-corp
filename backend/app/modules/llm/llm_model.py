"""직원별 가상 연봉, 월 한도 및 요청 정산 내역을 저장합니다."""

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Budget(Base):
    """직원 한 명에 설정한 운영 예산입니다."""

    __tablename__ = "llm_budgets"

    employee_id: Mapped[str] = mapped_column(
        String(24), primary_key=True, comment="직원 사번"
    )
    salary: Mapped[int] = mapped_column(Integer, comment="연간 가상 연봉(원)")
    monthly_limit: Mapped[int] = mapped_column(
        Integer, comment="월간 모의 사용 한도(원)"
    )


class Usage(Base):
    """모의 응답 한 건의 예산 예약 및 정산 내역입니다."""

    __tablename__ = "llm_usage"
    __table_args__ = (Index("ix_llm_usage_staff_month", "employee_id", "month"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="사용 내역 ID")
    employee_id: Mapped[str] = mapped_column(
        ForeignKey("llm_budgets.employee_id"), comment="예산을 사용하는 직원"
    )
    month: Mapped[str] = mapped_column(String(7), comment="예산 적용 월(한국 시간)")
    charged: Mapped[int] = mapped_column(
        Integer, comment="예약 또는 정산된 가상 비용(원)"
    )
    state: Mapped[str] = mapped_column(String(12), comment="예약, 정산 또는 반환 상태")
