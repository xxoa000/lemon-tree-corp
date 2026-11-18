"""공고 직무를 기록하고 기존 지원은 백엔드로 연결합니다."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """기존 지원과 면접 기록을 유지하면서 직무 컬럼을 추가합니다."""
    op.add_column(
        "job_applications",
        sa.Column(
            "role",
            sa.Text().with_variant(sa.String(20), "mysql"),
            nullable=False,
            server_default="backend",
            comment="지원한 공고의 직무 코드",
        ),
    )


def downgrade() -> None:
    """지원 건에서 직무 컬럼을 제거합니다."""
    with op.batch_alter_table("job_applications") as batch:
        batch.drop_column("role")
