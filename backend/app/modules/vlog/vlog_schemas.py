"""TechVlog 작성 및 조회 형식을 정의합니다."""

from pydantic import BaseModel, ConfigDict, Field


class Draft(BaseModel):
    """게시판에 입력할 제목과 글입니다."""

    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=12000)


class Article(Draft):
    """화면에 표시할 게시판 글 또는 릴리스 노트입니다."""

    id: str
    author_id: int | None = None
    author: str
    created_at: str
