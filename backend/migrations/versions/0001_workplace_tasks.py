"""업무와 변경 이력 테이블을 등록하고 기존 리뷰 데이터를 보존합니다."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

STATUS_CHECK = "status IN ('todo', 'in_progress', 'done')"
SEED_TASKS = (
    ("LT-21", "헬스 체크 테스트 추가", "API 응답 검증", "LT-011", "todo"),
    ("LT-22", "조직도 화면 검토", "프로필과 보고 체계 확인", "LT-007", "todo"),
    ("LT-19", "워크스페이스 화면 설계", "공통 메뉴와 화면 구조", "LT-005", "in_progress"),
    ("LT-18", "FastAPI 초기 구성", "조직 데이터 조회 API 구성", "LT-004", "done"),
)


def upgrade() -> None:
    """빈 DB에 테이블을 만들고 이전 SQLite DB의 행을 유지합니다."""
    connection = op.get_bind()
    existing = sa.inspect(connection).get_table_names()

    if "tasks" not in existing:
        op.create_table(
            "tasks",
            sa.Column("id", sa.Text(), primary_key=True, comment="업무 식별자"),
            sa.Column("title", sa.Text(), nullable=False, comment="업무 제목"),
            sa.Column("description", sa.Text(), nullable=False, comment="업무 상세 설명"),
            sa.Column("assignee_id", sa.Text(), nullable=False, comment="업무를 담당하는 직원 식별자"),
            sa.Column("status", sa.Text(), nullable=False, comment="현재 업무 상태"),
            sa.CheckConstraint(STATUS_CHECK),
        )
    else:
        with op.batch_alter_table("tasks", table_args=(sa.CheckConstraint(STATUS_CHECK),)) as batch:
            batch.alter_column("id", existing_type=sa.Text(), nullable=False)

    if "task_events" not in existing:
        op.create_table(
            "task_events",
            sa.Column("id", sa.Integer(), primary_key=True, comment="업무 변경 기록 식별자"),
            sa.Column("task_id", sa.Text(), nullable=False, comment="상태가 바뀐 업무 식별자"),
            sa.Column("actor_id", sa.Text(), nullable=False, comment="상태를 변경한 직원 식별자"),
            sa.Column("previous_status", sa.Text(), nullable=False, comment="변경 전 업무 상태"),
            sa.Column("status", sa.Text(), nullable=False, comment="변경 후 업무 상태"),
            sa.Column(
                "occurred_at", sa.Text(), nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"), comment="상태 변경 시각(UTC)",
            ),
        )
    else:
        with op.batch_alter_table("task_events") as batch:
            batch.alter_column("id", existing_type=sa.Integer(), nullable=False)

    connection.exec_driver_sql(
        "INSERT OR IGNORE INTO tasks (id, title, description, assignee_id, status) VALUES (?, ?, ?, ?, ?)",
        list(SEED_TASKS),
    )


def downgrade() -> None:
    """초기 리비전에서 관리하는 업무와 이력 테이블을 제거합니다."""
    op.drop_table("task_events")
    op.drop_table("tasks")
