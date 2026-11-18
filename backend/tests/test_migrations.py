"""Alembic이 이전 리뷰용 SQLite 데이터와 모델 정의를 유지하는지 검증합니다."""

import sqlite3
from contextlib import closing

from alembic import command
from alembic.config import Config

from app.database import BACKEND_DIR, create_workplace_engine, upgrade_workplace


def test_upgrade_preserves_legacy_tasks_and_events(tmp_path, monkeypatch):
    """리비전 없이 생성된 업무와 이력을 보존하고 모델 차이가 없는지 확인합니다."""
    path = tmp_path / "legacy.sqlite3"
    monkeypatch.setenv("WORKPLACE_DB_PATH", str(path))
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript("""
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL,
                assignee_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('todo', 'in_progress', 'done'))
            );
            CREATE TABLE task_events (
                id INTEGER PRIMARY KEY, task_id TEXT NOT NULL, actor_id TEXT NOT NULL,
                previous_status TEXT NOT NULL, status TEXT NOT NULL,
                occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO tasks VALUES ('LT-21', '기존 제목', '기존 설명', 'LT-011', 'done');
            INSERT INTO task_events VALUES (
                42, 'LT-21', 'LT-011', 'todo', 'done', '2026-11-18 00:00:00'
            );
        """)

    engine = create_workplace_engine()
    try:
        upgrade_workplace(engine)
        upgrade_workplace(engine)
        with engine.connect() as connection:
            assert connection.exec_driver_sql(
                "SELECT title, status FROM tasks WHERE id = 'LT-21'"
            ).one() == ("기존 제목", "done")
            assert connection.exec_driver_sql("SELECT * FROM task_events").one() == (
                42,
                "LT-21",
                "LT-011",
                "todo",
                "done",
                "2026-11-18 00:00:00",
            )
            assert (
                connection.exec_driver_sql("SELECT count(*) FROM tasks").scalar_one()
                == 4
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT version_num FROM alembic_version"
                ).scalar_one()
                == "0003"
            )
    finally:
        engine.dispose()

    command.check(Config(str(BACKEND_DIR / "alembic.ini")))


def test_role_migration_keeps_existing_application(tmp_path, monkeypatch):
    """직무 추가 이전의 지원과 답변이 백엔드 지원으로 유지되는지 확인합니다."""
    monkeypatch.setenv("WORKPLACE_DB_PATH", str(tmp_path / "jobs.sqlite3"))
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    command.upgrade(config, "0002")
    engine = create_workplace_engine()
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "INSERT INTO job_applications (id, applicant, filename, resume, stage, feedback) "
                "VALUES (1, 'acct:1', 'resume.txt', 'example resume', 'technical', 'passed')"
            )
            connection.exec_driver_sql(
                "INSERT INTO job_answers (application_id, question_id, answer, score) "
                "VALUES (1, 'tech-api', 'example answer', 3)"
            )
        upgrade_workplace(engine)
        with engine.connect() as connection:
            assert connection.exec_driver_sql(
                "SELECT role, stage FROM job_applications WHERE id = 1"
            ).one() == ("backend", "technical")
            assert connection.exec_driver_sql(
                "SELECT question_id, score FROM job_answers WHERE application_id = 1"
            ).one() == ("tech-api", 3)
    finally:
        engine.dispose()
    command.check(config)
