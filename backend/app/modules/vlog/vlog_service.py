"""Git에 포함된 릴리스 노트와 DB에 저장된 게시글을 관리합니다."""

from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.database import lock_sqlite_write
from app.modules.auth.auth_model import Account

from .vlog_model import Post
from .vlog_schemas import Article, Draft

RELEASES = Path(__file__).parent / "releases"


def view(row: Post, author: Account) -> Article:
    """사용자 글을 공개 조회 형식으로 변환합니다."""
    return Article(
        id=str(row.id),
        title=row.title,
        body=row.body,
        author_id=row.author_id,
        author=author.display_name or author.username,
        created_at=row.created_at,
    )


def list_posts(engine: Engine) -> list[Article]:
    """릴리스와 게시판의 글 목록을 최신순으로 반환합니다."""
    releases = []
    for path in RELEASES.glob("*.md"):
        header, _, body = path.read_text(encoding="utf-8").partition("\n")
        releases.append(
            Article(
                id=f"release:{path.stem}",
                title=header.removeprefix("# ").strip(),
                body=body.strip(),
                author="LemonTree",
                created_at=path.name[:10],
            )
        )
    with Session(engine) as db:
        rows = db.execute(
            select(Post, Account).join(Account).order_by(Post.id.desc()).limit(100)
        )
        releases.extend(view(row, account) for row, account in rows)
    return sorted(releases, key=lambda row: row.created_at, reverse=True)


def save(
    engine: Engine, author_id: int, data: Draft, post_id: int | None = None
) -> Article:
    """글을 생성하거나 작성자 또는 관리자가 수정합니다."""
    with Session(engine) as db, db.begin():
        lock_sqlite_write(db)
        actor = db.get(Account, author_id)
        if actor is None:
            raise HTTPException(401, "로그인이 필요합니다.")
        if post_id is None:
            row = Post(
                author_id=author_id,
                title=data.title,
                body=data.body,
                created_at=datetime.now(UTC).isoformat(timespec="seconds"),
            )
            db.add(row)
            db.flush()
        else:
            row = editable(db, post_id, actor)
            row.title, row.body = data.title, data.body
        author = db.get(Account, row.author_id)
        if author is None:
            raise HTTPException(404, "작성자를 찾을 수 없습니다.")
        return view(row, author)


def editable(db: Session, post_id: int, actor: Account) -> Post:
    """사용자 글의 수정 및 삭제 권한을 확인합니다."""
    row = db.get(Post, post_id, with_for_update=True)
    if row is None:
        raise HTTPException(404, "게시글이 없습니다.")
    if row.author_id != actor.id and actor.role != "admin":
        raise HTTPException(403, "작성자 또는 관리자만 변경할 수 있습니다.")
    return row


def remove(engine: Engine, author_id: int, post_id: int) -> None:
    """권한이 있는 게시판 글을 삭제합니다."""
    with Session(engine) as db, db.begin():
        lock_sqlite_write(db)
        actor = db.get(Account, author_id)
        if actor is None:
            raise HTTPException(401, "로그인이 필요합니다.")
        db.delete(editable(db, post_id, actor))
