"""사용자 전용 이력서 초안과 제출 원본을 저장합니다."""

from sqlalchemy import ForeignKey, LargeBinary, String, Text
from sqlalchemy.dialects.mysql import MEDIUMBLOB, MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Resume(Base):
    """한 계정의 이력서 초안 한 건입니다."""

    __tablename__ = "resumes"

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"), primary_key=True, comment="소유 계정 ID"
    )
    filename: Mapped[str] = mapped_column(String(255), comment="업로드한 파일 이름")
    original: Mapped[bytes] = mapped_column(
        LargeBinary().with_variant(MEDIUMBLOB(), "mysql"),
        deferred=True,
        comment="원본 PDF 또는 TXT",
    )
    content: Mapped[str] = mapped_column(
        Text().with_variant(MEDIUMTEXT(), "mysql"),
        comment="확인 및 수정 가능한 이력서 텍스트",
    )
