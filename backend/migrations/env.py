"""업무 모델을 Alembic 변경 감지에 연결하고 마이그레이션을 실행합니다."""

from alembic import context
from alembic.migration import MigrationContext
from sqlalchemy import Column, Connection
from sqlalchemy.schema import DefaultClause

from app.database import Base, create_workplace_engine, migration_connection
from app.modules.auth import auth_model  # noqa: F401
from app.modules.code import code_model  # noqa: F401
from app.modules.cv import cv_model  # noqa: F401
from app.modules.jobs import jobs_model  # noqa: F401
from app.modules.llm import llm_model  # noqa: F401
from app.modules.talk import talk_model  # noqa: F401
from app.modules.task import task_model  # noqa: F401
from app.modules.vlog import vlog_model  # noqa: F401
from app.modules.work import work_model  # noqa: F401


def compare_defaults(
    migration: MigrationContext,
    inspected_column: Column,
    metadata_column: Column,
    inspected: str | None,
    metadata_default: DefaultClause | None,
    rendered: str | None,
) -> bool | None:
    """MySQL이 반환하는 동등한 현재 시각 기본값을 정규화합니다."""
    if migration.dialect.name == "mysql" and inspected and rendered:
        current = {
            "current_timestamp",
            "current_timestamp()",
            "(current_timestamp)",
            "now()",
            "(now())",
        }
        if inspected.strip().lower() in current and rendered.strip().lower() in current:
            return False
    return None


def run_migrations(connection: Connection) -> None:
    """열린 데이터베이스 연결에서 모델 비교와 리비전 실행을 설정합니다."""
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        compare_type=True,
        compare_server_default=compare_defaults,
        render_as_batch=connection.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


def migrate() -> None:
    """API 시작 시 전달된 연결 또는 CLI용 자체 연결을 사용합니다."""
    if context.is_offline_mode():
        raise RuntimeError("기존 SQLite 스키마 확인을 위해 DB 연결이 필요합니다.")

    supplied = context.config.attributes.get("connection")
    if supplied is not None:
        run_migrations(supplied)
        return

    engine = create_workplace_engine()
    try:
        with migration_connection(engine) as connection:
            run_migrations(connection)
    finally:
        engine.dispose()


migrate()
