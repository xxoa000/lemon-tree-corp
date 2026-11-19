"""내 이력서 조회 및 수정 요청의 구조를 정의합니다."""

from pydantic import BaseModel, Field


class ResumeEdit(BaseModel):
    """지원자가 확인하고 수정한 이력서 텍스트입니다."""

    content: str = Field(min_length=1, max_length=24000)


class ResumeView(ResumeEdit):
    """원본 이름과 현재 편집본을 반환합니다."""

    filename: str
