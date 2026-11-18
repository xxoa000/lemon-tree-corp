"""직원 계정의 ID, 로그인 이름 및 비활성 상태를 정리합니다."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

STAFF_USERNAMES = {
    "LT-001": "minseok",
    "LT-002": "doyoon",
    "LT-003": "seojin",
    "LT-004": "junhyeok",
    "LT-005": "yuri",
    "LT-006": "hyeonwoo",
    "LT-007": "narin",
    "LT-008": "haeun",
    "LT-009": "taemin",
    "LT-010": "jian",
    "LT-011": "staff:lt-011",
    "LT-SYS-001": "seoyun",
}
HASH_COMMENTS = {
    "password_hash": "솔트가 포함된 비밀번호 해시",
    "recovery_hash": "계정 복구 코드 해시",
}


def set_hash_nullable(connection: sa.Connection, nullable: bool) -> None:
    """두 자격 증명 컬럼의 NULL 허용 여부를 변경합니다."""
    columns = {
        col["name"]: col for col in sa.inspect(connection).get_columns("accounts")
    }
    with op.batch_alter_table("accounts") as batch:
        for name, comment in HASH_COMMENTS.items():
            if columns[name]["nullable"] != nullable:
                batch.alter_column(
                    name,
                    existing_type=sa.Text(),
                    existing_comment=comment,
                    existing_nullable=columns[name]["nullable"],
                    nullable=nullable,
                )


def remap_account(
    connection: sa.Connection,
    accounts: sa.Table,
    old_id: int,
    new_id: int,
    username: str,
) -> None:
    """지원 기록의 소유권을 유지하며 계정 ID를 바꾸고 이전 세션을 만료시킵니다."""
    applications = sa.table("job_applications", sa.column("applicant"))
    connection.execute(
        accounts.update()
        .where(accounts.c.id == old_id)
        .values(
            id=new_id,
            username=username,
            session_version=accounts.c.session_version + 1,
        )
    )
    connection.execute(
        applications.update()
        .where(applications.c.applicant == f"acct:{old_id}")
        .values(
            applicant=f"acct:{new_id}",
        )
    )


def upgrade() -> None:
    """직원 계정만 바꾸고 기존 가입 계정과 활성 자격 증명을 보존합니다."""
    connection = op.get_bind()
    accounts = sa.Table("accounts", sa.MetaData(), autoload_with=connection)
    employees = list(
        connection.execute(
            sa.select(accounts.c.id, accounts.c.employee_id)
            .where(accounts.c.employee_id.in_(list(STAFF_USERNAMES)))
            .order_by(accounts.c.employee_id)
        ).mappings()
    )
    for row in employees:
        username = STAFF_USERNAMES[row["employee_id"]]
        conflict = connection.scalar(
            sa.select(accounts.c.id).where(
                accounts.c.username == username,
                accounts.c.id != row["id"],
            )
        )
        if conflict is not None:
            raise RuntimeError(
                f"직원 로그인 아이디 '{username}'이 이미 사용 중입니다. 기존 계정은 변경하지 않았습니다."
            )

    set_hash_nullable(connection, nullable=True)
    next_id = max(0, connection.scalar(sa.select(sa.func.max(accounts.c.id))) or 0) + 1
    for row in employees:
        if row["id"] < 0:
            remap_account(
                connection,
                accounts,
                row["id"],
                next_id,
                STAFF_USERNAMES[row["employee_id"]],
            )
            next_id += 1
    for field in HASH_COMMENTS:
        connection.execute(
            accounts.update().where(accounts.c[field] == "!").values({field: None})
        )


def downgrade() -> None:
    """이전 시드 식별자와 미설정 표시를 복원합니다."""
    connection = op.get_bind()
    accounts = sa.Table("accounts", sa.MetaData(), autoload_with=connection)
    for index, employee_id in enumerate(STAFF_USERNAMES, start=1):
        old_id = connection.scalar(
            sa.select(accounts.c.id).where(accounts.c.employee_id == employee_id)
        )
        if old_id is not None:
            remap_account(
                connection, accounts, old_id, -index, f"staff:{employee_id.lower()}"
            )
    for field in HASH_COMMENTS:
        connection.execute(
            accounts.update().where(accounts.c[field].is_(None)).values({field: "!"})
        )
    set_hash_nullable(connection, nullable=False)
