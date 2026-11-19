"""직원 예산의 관리자 응답 형식을 정의합니다."""

from pydantic import BaseModel, Field


class BudgetView(BaseModel):
    """직원별 가상 연봉과 이번 달 사용 한도를 표시합니다."""

    employee_id: str
    name: str
    salary: int
    monthly_limit: int
    used: int
    month: str


class BudgetEdit(BaseModel):
    """관리자가 설정하는 연봉과 월 사용 한도입니다."""

    salary: int = Field(ge=0, le=2_000_000_000)
    monthly_limit: int = Field(ge=0, le=2_000_000_000)
