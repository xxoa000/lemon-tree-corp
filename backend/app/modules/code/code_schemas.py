"""풀이 조회와 저장의 데이터 형식을 정의합니다."""

from typing import Literal

from pydantic import BaseModel, Field

Language = Literal["python", "javascript", "java", "cpp"]


class DraftEdit(BaseModel):
    """사용자의 언어와 코드 내용입니다."""

    language: Language
    code: str = Field(max_length=15000)
