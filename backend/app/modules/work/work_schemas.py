"""업무 페이지의 개발 요청과 실행 상태 응답을 정의합니다."""

from pydantic import BaseModel, ConfigDict, Field


class Draft(BaseModel):
    """관리자가 등록하는 사내 개발 요청입니다."""

    model_config = ConfigDict(str_strip_whitespace=True)
    employee_id: str = Field(min_length=1, max_length=24)
    title: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=6000)


class ImageView(BaseModel):
    """이미지의 표시 이름과 요청 내 순서입니다."""

    position: int
    name: str


class WorkView(Draft):
    """담당 직원의 작업 상태와 예산 표시용 정보입니다."""

    id: int
    state: str
    progress: str
    tokens: int | None
    summary: str
    has_patch: bool
    images: list[ImageView] = Field(default_factory=list)
