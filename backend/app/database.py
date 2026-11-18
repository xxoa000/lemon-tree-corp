"""API와 Alembic이 공유하는 DB 연결과 마이그레이션 잠금을 관리합니다."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import URL, Connection, Engine, create_engine, make_url, text
from sqlalchemy.orm import DeclarativeBase, Session

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Base(DeclarativeBase):
    """Alembic에서 변경을 감지할 SQLAlchemy 모델을 등록합니다."""


def create_workplace_engine() -> Engine:
    """명시적으로 설정한 MySQL 또는 기존 로컬 SQLite에 연결합니다."""
    configured = os.getenv("DATABASE_URL")
    if configured:
        url = make_url(configured)
        if url.drivername == "mysql":
            url = url.set(drivername="mysql+pymysql")
    elif os.getenv("MYSQL_HOST"):
        url = URL.create(
            "mysql+pymysql",
            username=os.environ["MYSQL_USER"],
            password=os.environ["MYSQL_PASSWORD"],
            host=os.environ["MYSQL_HOST"],
            port=int(os.getenv("MYSQL_PORT", "3306")),
            database=os.environ["MYSQL_DATABASE"],
        )
    else:
        path = Path(
            os.getenv(
                "WORKPLACE_DB_PATH", str(BACKEND_DIR / ".local/workplace.sqlite3")
            )
        )
        url = URL.create("sqlite", database=str(path))

    if url.drivername == "mysql+pymysql":
        if not url.database:
            raise ValueError("DATABASE_URL에 MySQL 데이터베이스 이름을 지정하세요.")
        query = {"charset": "utf8mb4", **url.query}
        return create_engine(url.set(query=query), pool_pre_ping=True)
    if url.drivername != "sqlite":
        raise ValueError("DATABASE_URL은 mysql+pymysql 또는 sqlite 형식이어야 합니다.")
    if url.database and url.database != ":memory:":
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url)


@contextmanager
def migration_connection(engine: Engine) -> Iterator[Connection]:
    """같은 DB로 향하는 여러 마이그레이션 실행을 직렬화합니다."""
    with engine.connect() as connection:
        mysql = engine.dialect.name == "mysql"
        if mysql:
            acquired = connection.scalar(
                text("SELECT GET_LOCK(SHA2(DATABASE(), 256), 30)")
            )
            if acquired != 1:
                raise RuntimeError("MySQL 마이그레이션 잠금을 획득하지 못했습니다.")
        else:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            yield connection
            connection.commit()
        finally:
            if mysql:
                connection.rollback()
                connection.execute(text("SELECT RELEASE_LOCK(SHA2(DATABASE(), 256))"))


def lock_sqlite_write(session: Session) -> None:
    """행 잠금을 지원하지 않는 SQLite에서 쓰기 트랜잭션을 먼저 엽니다."""
    if session.get_bind().dialect.name == "sqlite":
        session.execute(text("BEGIN IMMEDIATE"))


def upgrade_workplace(engine: Engine) -> None:
    """애플리케이션 시작 전에 미적용 Alembic 리비전을 실행합니다."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    with migration_connection(engine) as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
