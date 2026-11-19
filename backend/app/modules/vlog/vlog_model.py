"""TechVlog 게시판의 사용자 작성 글을 저장합니다."""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Post(Base):
    """게시판 글 한 건입니다."""

    __tablename__ = "vlog_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="게시글 ID")
    author_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"), comment="작성 계정 ID"
    )
    title: Mapped[str] = mapped_column(String(120), comment="글 제목")
    body: Mapped[str] = mapped_column(Text, comment="Markdown 글 본문")
    created_at: Mapped[str] = mapped_column(String(32), comment="등록 UTC 시각")
