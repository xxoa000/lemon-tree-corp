"""공식 문제 링크별로 사용자의 편집 내용을 읽고 씁니다."""

import re
from urllib.parse import urlsplit, urlunsplit

from fastapi import HTTPException
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.database import lock_sqlite_write
from app.modules.auth.auth_model import Account

from .code_model import Draft
from .code_schemas import DraftEdit

LOCAL_PROBLEMS = {"sum-pairs", "first-duplicate"}
PROVIDERS = {
    "school.programmers.co.kr": r"/learn/courses/\d+/lessons/\d+/?",
    "www.acmicpc.net": r"/problem/\d+/?",
    "leetcode.com": r"/problems/[a-zA-Z0-9-]+(?:/description)?/?",
    "atcoder.jp": r"/contests/[\w-]+/tasks/[\w-]+/?",
}


def problem_key(problem: str) -> str:
    """실습 키 또는 지원 사이트의 HTTPS 문제 URL을 정규화합니다."""
    if problem in LOCAL_PROBLEMS:
        return problem
    try:
        parts = urlsplit(problem)
        pattern = PROVIDERS.get(parts.hostname or "")
        if (
            parts.scheme == "https"
            and pattern
            and re.fullmatch(pattern, parts.path)
            and not parts.username
            and not parts.password
            and parts.port in (None, 443)
        ):
            return urlunsplit(
                ("https", parts.hostname or "", parts.path.rstrip("/"), "", "")
            )
    except ValueError:
        pass
    raise HTTPException(
        422, "프로그래머스, 백준, LeetCode 또는 AtCoder의 문제 주소를 입력해 주세요."
    )


def read(engine: Engine, owner: int, problem: str) -> DraftEdit | None:
    """내가 저장한 문제 풀이를 읽습니다."""
    with Session(engine) as db:
        row = db.get(Draft, (owner, problem_key(problem)))
        return DraftEdit(language=row.language, code=row.code) if row else None


def save(engine: Engine, owner: int, problem: str, data: DraftEdit) -> DraftEdit:
    """이미 존재하는 풀이를 갱신하거나 처음 저장합니다."""
    key = problem_key(problem)
    with Session(engine) as db, db.begin():
        lock_sqlite_write(db)
        db.get(Account, owner, with_for_update=True)
        row = db.get(Draft, (owner, key))
        if row is None:
            db.add(
                Draft(
                    owner_id=owner, problem=key, language=data.language, code=data.code
                )
            )
        else:
            row.language, row.code = data.language, data.code
    return data


def problems(engine: Engine, owner: int) -> list[str]:
    """내가 이전에 저장한 문제를 나열합니다."""
    from sqlalchemy import select

    with Session(engine) as db:
        return list(
            db.scalars(
                select(Draft.problem)
                .where(Draft.owner_id == owner)
                .order_by(Draft.problem)
            )
        )
