"""계정의 프로필 컬럼을 추가하고 조직 구성원 계정을 등록합니다."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import MEDIUMBLOB

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

STAFF = (
    ("LT-001", "차민석"),
    ("LT-002", "강도윤"),
    ("LT-003", "윤서진"),
    ("LT-004", "이준혁"),
    ("LT-005", "한유리"),
    ("LT-006", "박현우"),
    ("LT-007", "최나린"),
    ("LT-008", "정하은"),
    ("LT-009", "오태민"),
    ("LT-010", "서지안"),
    ("LT-011", "사용자"),
    ("LT-SYS-001", "백서윤"),
)


def upgrade() -> None:
    """기존 가입 계정을 사원으로 유지하고, 비활성 직원 계정을 추가합니다."""
    op.add_column(
        "accounts",
        sa.Column(
            "role",
            sa.String(12),
            server_default="member",
            nullable=False,
            comment="계정 권한",
        ),
    )
    op.add_column(
        "accounts",
        sa.Column("employee_id", sa.String(24), comment="연결된 조직 구성원 식별자"),
    )
    op.create_index("uq_accounts_employee_id", "accounts", ["employee_id"], unique=True)
    op.add_column(
        "accounts",
        sa.Column(
            "display_name",
            sa.String(80),
            server_default="",
            nullable=False,
            comment="프로필 표시 이름",
        ),
    )
    op.add_column(
        "accounts",
        sa.Column(
            "phone",
            sa.String(32),
            server_default="",
            nullable=False,
            comment="연락처 전화번호",
        ),
    )
    op.add_column(
        "accounts",
        sa.Column(
            "bio",
            sa.String(1000),
            server_default="",
            nullable=False,
            comment="프로필 자기소개",
        ),
    )
    op.add_column(
        "accounts",
        sa.Column(
            "avatar",
            sa.LargeBinary().with_variant(MEDIUMBLOB(), "mysql"),
            comment="정규화된 WebP 프로필 이미지",
        ),
    )
    names = (
        "id",
        "username",
        "email",
        "password_hash",
        "recovery_hash",
        "session_version",
        "role",
        "employee_id",
        "display_name",
    )
    accounts = sa.table("accounts", *(sa.column(name) for name in names))
    op.bulk_insert(
        accounts,
        [
            dict(
                zip(
                    names,
                    (
                        -index,
                        f"staff:{employee_id.lower()}",
                        f"{employee_id.lower()}@lemontree.invalid",
                        "!",
                        "!",
                        1,
                        "admin" if employee_id == "LT-SYS-001" else "member",
                        employee_id,
                        name,
                    ),
                    strict=True,
                )
            )
            for index, (employee_id, name) in enumerate(STAFF, start=1)
        ],
    )


def downgrade() -> None:
    """사용된 직원 계정을 보존하고 빈 시드 계정만 정리합니다."""
    connection = op.get_bind()
    used = connection.scalar(
        sa.text(
            "SELECT COUNT(*) FROM accounts WHERE employee_id IS NOT NULL AND "
            "(password_hash <> '!' OR EXISTS (SELECT 1 FROM job_applications "
            "WHERE applicant = CONCAT('acct:', accounts.id)))"
            if connection.dialect.name == "mysql"
            else "SELECT COUNT(*) FROM accounts WHERE employee_id IS NOT NULL AND "
            "(password_hash <> '!' OR EXISTS (SELECT 1 FROM job_applications "
            "WHERE applicant = 'acct:' || accounts.id))"
        )
    )
    if used:
        raise RuntimeError(
            "활성 직원 계정 또는 직원 지원 기록이 있어 0004를 되돌릴 수 없습니다."
        )
    connection.execute(sa.text("DELETE FROM accounts WHERE employee_id IS NOT NULL"))
    op.drop_index("uq_accounts_employee_id", table_name="accounts")
    with op.batch_alter_table("accounts") as batch:
        for column in ("avatar", "bio", "phone", "display_name", "employee_id", "role"):
            batch.drop_column(column)
