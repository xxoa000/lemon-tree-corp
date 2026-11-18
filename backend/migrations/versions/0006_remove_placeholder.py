"""조직에서 비어 있는 주니어 백엔드 자리를 정리합니다."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """미사용 계정을 제거하고 실제 자격 증명 또는 지원이 있으면 보존합니다."""
    db = op.get_bind()
    accounts = sa.table(
        "accounts",
        sa.column("id"),
        sa.column("employee_id"),
        sa.column("password_hash"),
        sa.column("recovery_hash"),
        sa.column("display_name"),
    )
    applications = sa.table("job_applications", sa.column("applicant"))
    placeholder = (
        db.execute(sa.select(accounts).where(accounts.c.employee_id == "LT-011"))
        .mappings()
        .one_or_none()
    )
    if placeholder:
        row = accounts.c.id == placeholder["id"]
        has_application = db.scalar(
            sa.select(sa.literal(1))
            .where(applications.c.applicant == f"acct:{placeholder['id']}")
            .limit(1)
        )
        if (
            placeholder["password_hash"]
            or placeholder["recovery_hash"]
            or has_application
        ):
            changes = {"employee_id": None}
            if placeholder["display_name"] == "사용자":
                changes["display_name"] = ""
            db.execute(accounts.update().where(row).values(**changes))
        else:
            db.execute(accounts.delete().where(row))
    tasks = sa.table("tasks", sa.column("assignee_id"))
    db.execute(
        tasks.update().where(tasks.c.assignee_id == "LT-011").values(assignee_id="")
    )


def downgrade() -> None:
    """삭제한 시드와 과거 담당자를 추정해 복원하지 않습니다."""
    raise RuntimeError("제거한 계정과 업무 배정은 백업에서 복원해야 합니다.")
