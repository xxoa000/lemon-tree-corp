"""업무 상태 변경 요청과 업무 조회 응답의 구조를 정의합니다."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

Status = Literal["todo", "in_progress", "done"]


class TaskUpdate(BaseModel):
    """업무에 적용할 상태를 검증합니다."""

    status: Status


class TaskResponse(BaseModel):
    """업무 보드에서 사용하는 업무 정보와 담당자를 응답합니다."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    assignee_id: str
    status: Status
