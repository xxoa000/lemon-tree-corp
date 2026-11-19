"""mock llm budgets and stream cursor

Revision ID: 0008
Revises: 0007
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """이 리비전의 스키마 변경을 적용합니다."""
    op.create_table(
        "llm_budgets",
        sa.Column(
            "employee_id", sa.String(length=24), nullable=False, comment="직원 사번"
        ),
        sa.Column("salary", sa.Integer(), nullable=False, comment="연간 가상 연봉(원)"),
        sa.Column(
            "monthly_limit",
            sa.Integer(),
            nullable=False,
            comment="월간 모의 사용 한도(원)",
        ),
        sa.PrimaryKeyConstraint("employee_id"),
    )
    op.create_table(
        "llm_usage",
        sa.Column("id", sa.Integer(), nullable=False, comment="사용 내역 ID"),
        sa.Column(
            "employee_id",
            sa.String(length=24),
            nullable=False,
            comment="예산을 사용하는 직원",
        ),
        sa.Column(
            "month",
            sa.String(length=7),
            nullable=False,
            comment="예산 적용 월(한국 시간)",
        ),
        sa.Column(
            "charged",
            sa.Integer(),
            nullable=False,
            comment="예약 또는 정산된 가상 비용(원)",
        ),
        sa.Column(
            "state",
            sa.String(length=12),
            nullable=False,
            comment="예약, 정산 또는 반환 상태",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["llm_budgets.employee_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("llm_usage", schema=None) as batch_op:
        batch_op.create_index(
            "ix_llm_usage_staff_month", ["employee_id", "month"], unique=False
        )

    with op.batch_alter_table("talk_members", schema=None) as batch_op:
        batch_op.alter_column(
            "joined_after",
            existing_type=sa.INTEGER(),
            type_=sa.BigInteger(),
            existing_nullable=False,
            existing_comment="참여 전에 존재한 마지막 메시지 ID",
        )

    salaries = {
        "LT-001": 120_000_000,
        "LT-002": 110_000_000,
        "LT-003": 84_000_000,
        "LT-004": 90_000_000,
        "LT-005": 65_000_000,
        "LT-006": 96_000_000,
        "LT-007": 78_000_000,
        "LT-008": 86_000_000,
        "LT-009": 82_000_000,
        "LT-010": 70_000_000,
        "LT-SYS-001": 100_000_000,
    }
    table = sa.table(
        "llm_budgets",
        sa.column("employee_id"),
        sa.column("salary"),
        sa.column("monthly_limit"),
    )
    op.bulk_insert(
        table,
        [
            {"employee_id": employee, "salary": salary, "monthly_limit": salary // 1200}
            for employee, salary in salaries.items()
        ],
    )


def downgrade() -> None:
    """Redis 메시지 식별자를 축소해 기존 참여 기록을 손상시키지 않습니다."""
    raise RuntimeError("Redis 전환 후 되돌리려면 이전 DB 백업을 복원해야 합니다.")
