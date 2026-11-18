"""로컬 업무 SQLite 연결과 Alembic 업그레이드를 관리합니다."""

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.orm import DeclarativeBase

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Base(DeclarativeBase):
    """Alembic에서 변경을 감지할 SQLAlchemy 모델을 등록합니다."""


def create_workplace_engine() -> Engine:
    """설정된 SQLite 파일을 가리키는 엔진을 생성합니다."""
    path = Path(os.getenv("WORKPLACE_DB_PATH", str(BACKEND_DIR / ".local/workplace.sqlite3")))
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(URL.create("sqlite", database=str(path)))


def upgrade_workplace(engine: Engine) -> None:
    """애플리케이션 시작 전에 미적용 Alembic 리비전을 실행합니다."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    with engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        connection.commit()
