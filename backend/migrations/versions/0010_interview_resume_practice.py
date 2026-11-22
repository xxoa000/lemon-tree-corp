"""interview review resume and coding practice

Revision ID: 0010
Revises: 0009
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """이 리비전의 스키마 변경을 적용합니다."""
    op.create_table(
        "code_drafts",
        sa.Column("owner_id", sa.Integer(), nullable=False, comment="풀이 소유자"),
        sa.Column(
            "problem",
            sa.String(length=255),
            nullable=False,
            comment="로컬 문제 키 또는 외부 문제 URL",
        ),
        sa.Column(
            "language",
            sa.String(length=24),
            nullable=False,
            comment="사용자가 선택한 언어",
        ),
        sa.Column("code", sa.Text(), nullable=False, comment="저장한 소스 코드"),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["accounts.id"],
        ),
        sa.PrimaryKeyConstraint("owner_id", "problem"),
    )
    op.create_table(
        "job_questions",
        sa.Column(
            "application_id", sa.Integer(), nullable=False, comment="지원 건 식별자"
        ),
        sa.Column(
            "question_id",
            sa.String(length=30),
            nullable=False,
            comment="전형 내 질문 식별자",
        ),
        sa.Column("prompt", sa.Text(), nullable=False, comment="생성된 질문 원문"),
        sa.Column(
            "criteria",
            sa.Text(),
            nullable=False,
            comment="답변 전에 확정한 세 평가 기준 JSON",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["job_applications.id"],
        ),
        sa.PrimaryKeyConstraint("application_id", "question_id"),
    )
    with op.batch_alter_table("resumes", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "sections",
                sa.Text().with_variant(mysql.MEDIUMTEXT(), "mysql"),
                nullable=True,
                comment="직접 작성한 이력서 항목 JSON",
            )
        )


def downgrade() -> None:
    """이 리비전의 스키마 변경을 되돌립니다."""
    with op.batch_alter_table("resumes", schema=None) as batch_op:
        batch_op.drop_column("sections")

    op.drop_table("job_questions")
    op.drop_table("code_drafts")
