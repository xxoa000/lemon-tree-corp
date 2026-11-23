"""Add the Codex work queue.

Revision ID: 0011
Revises: 0010
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import MEDIUMTEXT

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """개발 요청과 실행 결과를 저장할 테이블을 생성합니다."""
    op.create_table(
        "codex_work",
        sa.Column("id", sa.Integer(), primary_key=True, comment="작업 ID"),
        sa.Column(
            "employee_id",
            sa.String(24),
            sa.ForeignKey("llm_budgets.employee_id"),
            nullable=False,
            comment="담당 직원 사번",
        ),
        sa.Column("title", sa.String(120), nullable=False, comment="작업 제목"),
        sa.Column("prompt", sa.Text(), nullable=False, comment="승인할 개발 요청"),
        sa.Column("state", sa.String(16), nullable=False, comment="작업 상태"),
        sa.Column("progress", sa.String(120), nullable=False, comment="최근 작업 단계"),
        sa.Column(
            "usage_id",
            sa.Integer(),
            sa.ForeignKey("llm_usage.id"),
            comment="월 가상 예산 예약 ID",
        ),
        sa.Column("expires_at", sa.Integer(), comment="작업 만료 시각의 유닉스 초"),
        sa.Column("tokens", sa.Integer(), comment="보고된 입력과 출력 토큰 합계"),
        sa.Column("summary", sa.Text(), nullable=False, comment="완료 또는 실패 요약"),
        sa.Column(
            "patch",
            sa.Text().with_variant(MEDIUMTEXT(), "mysql"),
            nullable=False,
            comment="검토용 Git 패치",
        ),
    )
    op.create_index("ix_codex_work_state", "codex_work", ["state"])


def downgrade() -> None:
    """Codex 작업 테이블을 제거합니다."""
    op.drop_index("ix_codex_work_state", table_name="codex_work")
    op.drop_table("codex_work")
