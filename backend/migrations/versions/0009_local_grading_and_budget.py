"""로컬 면접 평가 근거를 저장하고 가상 예산을 재배분합니다."""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

# 예상 개발 호출 순서는 백엔드, 프런트엔드, 기술 설계, AI/QA,
# 데이터·인프라, 기획·디자인·조직 운영, 경영으로 잡았습니다.
ALLOCATION = {
    "LT-001": (38_000_000, 1_100),
    "LT-002": (49_000_000, 7_000),
    "LT-003": (33_000_000, 2_500),
    "LT-004": (43_000_000, 9_000),
    "LT-005": (32_000_000, 7_500),
    "LT-006": (42_000_000, 4_000),
    "LT-007": (34_000_000, 2_200),
    "LT-008": (36_000_000, 5_500),
    "LT-009": (39_000_000, 3_500),
    "LT-010": (37_000_000, 5_500),
    "LT-SYS-001": (40_000_000, 2_200),
}


def upgrade() -> None:
    """기존 사용량과 점수를 보존하고 새 기준을 적용합니다."""
    op.add_column(
        "job_answers",
        sa.Column("evaluation", sa.Text(), comment="로컬 AI의 평가 항목과 피드백 JSON"),
    )
    budgets = sa.table(
        "llm_budgets",
        sa.column("employee_id"),
        sa.column("salary"),
        sa.column("monthly_limit"),
    )
    connection = op.get_bind()
    for employee, (salary, limit) in ALLOCATION.items():
        connection.execute(
            budgets.update()
            .where(budgets.c.employee_id == employee)
            .values(
                salary=salary,
                monthly_limit=limit,
            )
        )


def downgrade() -> None:
    """AI 평가 데이터 컬럼을 제거합니다. 조정된 예산은 유지합니다."""
    with op.batch_alter_table("job_answers") as batch:
        batch.drop_column("evaluation")
