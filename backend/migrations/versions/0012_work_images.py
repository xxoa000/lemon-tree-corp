"""Add image attachments to Codex work.

Revision ID: 0012
Revises: 0011
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import MEDIUMBLOB

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Codex 요청의 이미지 첨부 테이블을 추가합니다."""
    op.create_table(
        "codex_work_images",
        sa.Column(
            "work_id",
            sa.Integer(),
            sa.ForeignKey("codex_work.id", ondelete="CASCADE"),
            primary_key=True,
            comment="첨부가 속한 작업 ID",
        ),
        sa.Column(
            "position", sa.Integer(), primary_key=True, comment="작업 내 첨부 순서"
        ),
        sa.Column("name", sa.String(255), nullable=False, comment="첨부 표시 이름"),
        sa.Column(
            "content",
            sa.LargeBinary().with_variant(MEDIUMBLOB(), "mysql"),
            nullable=False,
            comment="정규화된 PNG 데이터",
        ),
    )


def downgrade() -> None:
    """이미지 첨부 테이블을 제거합니다."""
    op.drop_table("codex_work_images")
