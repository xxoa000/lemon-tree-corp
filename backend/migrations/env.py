"""업무 모델을 Alembic 변경 감지에 연결하고 마이그레이션을 실행합니다."""

from alembic import context
from sqlalchemy import Connection

from app.database import Base, create_workplace_engine
from app.modules.task import task_model  # noqa: F401


def run_migrations(connection: Connection) -> None:
    """열린 SQLite 연결에서 모델 비교와 리비전 실행을 설정합니다."""
    context.configure(
        connection=connection, target_metadata=Base.metadata,
        compare_type=True, compare_server_default=True, render_as_batch=True,
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
        with engine.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            run_migrations(connection)
            connection.commit()
    finally:
        engine.dispose()


migrate()
