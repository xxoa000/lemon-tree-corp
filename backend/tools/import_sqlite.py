"""업무 SQLite 백업을 현재 MySQL 스키마로 복사합니다."""

import argparse
import sqlite3
from contextlib import closing
from datetime import datetime
from importlib import import_module
from pathlib import Path

from sqlalchemy import Connection, MetaData, Table, or_, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.database import create_workplace_engine, migration_connection

TABLES = ("tasks", "task_events", "accounts", "job_applications", "job_answers")
QUESTIONS = "job_questions"
QUESTION_KEY = ("application_id", "question_id")
TIMESTAMPS = {"task_events": "occurred_at", "job_applications": "created_at"}
SEED = import_module("migrations.versions.0001_workplace_tasks").SEED_TASKS
TASK_FIELDS = ("id", "title", "description", "assignee_id", "status")
SEED_ROWS = {values[0]: dict(zip(TASK_FIELDS, values, strict=True)) for values in SEED}


def load_source(path: Path) -> dict[str, list[dict]]:
    """읽기 전용 SQLite 스냅샷에서 지원하는 테이블을 읽습니다."""
    source: dict[str, list[dict]] = {}
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("BEGIN")
        for name in TABLES:
            rows = [
                dict(row) for row in db.execute(f"SELECT * FROM {name} ORDER BY id")
            ]
            for row in rows:
                if (
                    name != "tasks"
                    and row["id"] <= 0
                    and not (
                        name == "accounts" and row["id"] < 0 and row.get("employee_id")
                    )
                ):
                    raise ValueError(f"{name}: 0 이하 식별자가 있어 이전을 중단합니다.")
                if name == "job_applications":
                    row.setdefault("role", "backend")
                if name in TIMESTAMPS:
                    field = TIMESTAMPS[name]
                    row[field] = datetime.fromisoformat(row[field])
            source[name] = rows

        exists = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (QUESTIONS,),
        ).fetchone()
        if exists:
            source[QUESTIONS] = [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM job_questions ORDER BY application_id, question_id"
                )
            ]

    accounts = {f"acct:{row['id']}" for row in source["accounts"]}
    applications = {row["id"] for row in source["job_applications"]}
    if any(
        row["applicant"] not in accounts and row["applicant"] != "LT-011"
        for row in source["job_applications"]
    ) or any(
        row["application_id"] not in applications
        for name in ("job_answers", QUESTIONS)
        for row in source.get(name, [])
    ):
        raise ValueError("SQLite 지원 내역에 연결된 계정 또는 지원 건이 없습니다.")
    return source


def remap_seeded_accounts(
    db: Connection, table: Table, source: dict[str, list[dict]]
) -> dict[str, list[dict]]:
    """시드 행이 차지한 ID의 충돌을 피하고 해당 지원 기록의 소유권을 보존합니다."""
    staff_names = import_module(
        "migrations.versions.0005_staff_identity"
    ).STAFF_USERNAMES
    target = {row["id"]: row for row in db.execute(select(table)).mappings()}
    by_employee = {
        row["employee_id"]: row for row in target.values() if row["employee_id"]
    }
    by_username = {row["username"]: row for row in target.values()}
    next_id = max([0, *target, *(row["id"] for row in source["accounts"])]) + 1
    mapping: dict[str, str] = {}
    accounts = []
    applicants = {row["applicant"] for row in source["job_applications"]}
    for original in source["accounts"]:
        row = dict(original)
        old_id = row["id"]
        employee_id = row.get("employee_id")
        if employee_id == "LT-011" and employee_id not in by_employee:
            if not (
                row["password_hash"] not in (None, "!")
                or row["recovery_hash"] not in (None, "!")
                or f"acct:{old_id}" in applicants
            ):
                continue
            row.update(employee_id=None, username="staff:lt-011")
            if row.get("display_name") == "사용자":
                row["display_name"] = ""
            employee_id = None
            if old_id < 0:
                row["session_version"] += 1
        if employee_id:
            registered = by_employee.get(employee_id)
            if registered is None or employee_id not in staff_names:
                raise ValueError("대상 DB에 연결할 직원 시드가 없습니다.")
            row.update(id=registered["id"], username=staff_names[employee_id])
            if old_id < 0:
                row["session_version"] += 1
        elif row["username"] in by_username:
            row["id"] = by_username[row["username"]]["id"]
        elif old_id < 0 or (old_id in target and target[old_id]["employee_id"]):
            row["id"] = next_id
            next_id += 1
        for key in ("password_hash", "recovery_hash"):
            if row[key] == "!":
                row[key] = None
        if row["id"] != old_id:
            mapping[f"acct:{old_id}"] = f"acct:{row['id']}"
        accounts.append(row)

    if len({row["id"] for row in accounts}) != len(accounts):
        raise ValueError("여러 원본 계정이 같은 대상 계정으로 연결됩니다.")
    applications = [
        {**row, "applicant": mapping.get(row["applicant"], row["applicant"])}
        for row in source["job_applications"]
    ]
    if mapping:
        print(
            f"시드와 충돌하거나 이름이 변경된 계정 ID {len(mapping)}개를 연결했습니다."
        )
    return {**source, "accounts": accounts, "job_applications": applications}


def copy_rows(db: Connection, source: dict[str, list[dict]], apply: bool) -> None:
    """식별자와 제약 조건을 확인하고 적용 모드에서만 대상에 씁니다."""
    revision = db.scalar(text("SELECT version_num FROM alembic_version"))
    if revision not in {f"{number:04d}" for number in range(3, 13)}:
        raise ValueError(
            "대상 MySQL에 지원하는 Alembic 리비전(0003~0012)을 먼저 적용하세요."
        )

    schema = int(revision)
    if schema < 10 and source.get(QUESTIONS):
        raise ValueError(
            "생성한 면접 질문도 복사하려면 대상에 Alembic 0010 이상을 적용하세요."
        )
    if schema < 9 and any(row.get("evaluation") for row in source["job_answers"]):
        raise ValueError(
            "면접 피드백도 복사하려면 대상에 Alembic 0009 이상을 적용하세요."
        )
    names = (*TABLES, QUESTIONS) if schema >= 10 and QUESTIONS in source else TABLES
    metadata = MetaData()
    tables = {name: Table(name, metadata, autoload_with=db) for name in names}
    engines = {
        name: engine
        for name, engine in db.execute(
            text(
                "SELECT TABLE_NAME, ENGINE FROM information_schema.tables WHERE TABLE_SCHEMA = DATABASE()"
            )
        )
    }
    if any(engines.get(name) != "InnoDB" for name in names):
        raise ValueError("대상 업무 테이블이 모두 InnoDB여야 합니다.")

    if schema >= 5:
        source = remap_seeded_accounts(db, tables["accounts"], source)

    task_events = tables["task_events"]
    changed_tasks = set(db.scalars(select(task_events.c.task_id)))
    for name, table in tables.items():
        fields = QUESTION_KEY if name == QUESTIONS else ("id",)
        existing = {
            tuple(row[field] for field in fields): dict(row)
            for row in db.execute(select(table)).mappings()
        }
        inserted, updated = [], []
        skipped = 0
        for original in source[name]:
            row = original
            if name == "tasks" and schema >= 6 and row["assignee_id"] == "LT-011":
                row = {**row, "assignee_id": ""}
            if name == "accounts" and schema >= 4:
                row = {
                    "role": "member",
                    "employee_id": None,
                    "display_name": "",
                    "phone": "",
                    "bio": "",
                    "avatar": None,
                    **row,
                }
            if name == "job_answers" and schema >= 9 and "evaluation" not in row:
                row = {**row, "evaluation": None}
            if set(row) != set(table.c.keys()):
                raise ValueError(
                    f"{name}: 대상 DB와 백업의 컬럼이 다릅니다. 대상 스키마를 업데이트하세요."
                )
            key = tuple(row[field] for field in fields)
            current = existing.get(key)
            seed = SEED_ROWS.get(row["id"]) if name == "tasks" else None
            if seed and schema >= 6 and seed["assignee_id"] == "LT-011":
                seed = {**seed, "assignee_id": ""}
            if current == row:
                skipped += 1
            elif current is None:
                if name == "accounts":
                    conflict = db.scalar(
                        select(table.c.id).where(
                            or_(
                                table.c.username == row["username"],
                                table.c.email == row["email"],
                            )
                        )
                    )
                elif name == "job_answers":
                    conflict = db.scalar(
                        select(table.c.id).where(
                            table.c.application_id == row["application_id"],
                            table.c.question_id == row["question_id"],
                        )
                    )
                else:
                    conflict = None
                if conflict is not None:
                    raise ValueError(
                        f"{name}: 대상 DB의 고유값이 충돌합니다. 이전을 중단합니다."
                    )
                inserted.append(row)
            elif (
                (name == "tasks" and current == seed and key not in changed_tasks)
                or (
                    name == "accounts"
                    and current.get("employee_id") is not None
                    and current["password_hash"] in (None, "!")
                    and all(
                        current[field] == row[field]
                        for field in ("employee_id", "username", "role")
                    )
                    and not (current["phone"] or current["bio"] or current["avatar"])
                )
                or (
                    name == "job_answers"
                    and current.get("evaluation") is None
                    and bool(row.get("evaluation"))
                    and current == {**row, "evaluation": None}
                )
            ):
                updated.append(row)
            else:
                raise ValueError(
                    f"{name}: 대상 DB에 다른 내용의 동일 식별자가 있습니다. 이전을 중단합니다."
                )

        if apply:
            if inserted:
                db.execute(table.insert(), inserted)
            for row in updated:
                values = {key: value for key, value in row.items() if key not in fields}
                condition = [table.c[field] == row[field] for field in fields]
                db.execute(table.update().where(*condition).values(values))
        print(
            f"{name}: 추가 {len(inserted)}, 기존 데이터 보완 {len(updated)}, 동일 {skipped}"
        )


def main() -> int:
    """연결을 확인하고 가져오기 계획 또는 적용 결과를 출력합니다."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="SQLite 백업 경로")
    parser.add_argument(
        "--apply", action="store_true", help="확인한 데이터를 MySQL에 저장합니다."
    )
    args = parser.parse_args()
    try:
        source = load_source(args.source)
        engine = create_workplace_engine()
        try:
            if engine.dialect.name != "mysql":
                raise ValueError("대상이 MySQL로 설정되어 있어야 합니다.")
            print(f"대상 MySQL 데이터베이스: {engine.url.database}")
            with migration_connection(engine) as db:
                copy_rows(db, source, args.apply)
        finally:
            engine.dispose()
    except ValueError as error:
        print(f"이전 중단: {error}")
        return 1
    except (sqlite3.Error, SQLAlchemyError):
        print(
            "이전 중단: DB 연결 또는 제약 조건을 확인하세요. 저장된 이전 내역은 없습니다."
        )
        return 1

    print("이전 완료." if args.apply else "미리보기 완료. 실제 데이터 변경은 없습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
