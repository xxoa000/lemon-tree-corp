"""대화방 접근 권한, 전송, 읽음과 멤버 변경을 처리합니다."""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import lock_sqlite_write
from app.modules.auth.auth_model import Account

from .talk_model import Member, Message, Room


def contact_view(row: Account) -> dict:
    """연락처의 공개 이름과 사번만 반환합니다."""
    return {
        "id": row.id,
        "name": row.display_name or row.username,
        "employee_id": row.employee_id,
    }


def contacts(engine: Engine, owner: int) -> list[dict]:
    """본인을 제외한 직원과 사용자 연락처를 조회합니다."""
    with Session(engine) as db:
        return [
            contact_view(row)
            for row in db.scalars(
                select(Account)
                .where(Account.id != owner)
                .order_by(Account.display_name, Account.id)
            )
        ]


def room_snapshot(engine: Engine, owner: int) -> list[dict]:
    """내 대화방 목록과 읽지 않은 메시지 수를 반환합니다."""
    with Session(engine) as db:
        entries = db.execute(
            select(Room, Member)
            .join(Member)
            .where(Member.account_id == owner)
            .order_by(Room.id)
        )
        results = []
        for room, member in entries:
            name = room.name
            if room.dm_key:
                peer = db.scalar(
                    select(Account)
                    .join(Member)
                    .where(Member.room_id == room.id, Account.id != owner)
                )
                name = contact_view(peer)["name"] if peer else "1:1 대화"
            participants = (
                db.scalar(
                    select(func.count())
                    .select_from(Member)
                    .where(Member.room_id == room.id)
                )
                or 0
            )
            latest = (
                db.scalar(
                    select(func.max(Message.id)).where(Message.room_id == room.id)
                )
                or 0
            )
            unread = (
                db.scalar(
                    select(func.count())
                    .select_from(Message)
                    .where(
                        Message.room_id == room.id,
                        Message.id > member.last_read,
                        Message.sender != owner,
                    )
                )
                or 0
            )
            results.append(
                {
                    "id": room.id,
                    "name": name,
                    "team": room.team,
                    "owner": room.owner_id == owner,
                    "latest": latest,
                    "unread": unread,
                    "participants": participants,
                }
            )
        return results


def membership(db: Session, room_id: int, owner: int) -> Member:
    """대화방에 참여 중인 경우에만 접근을 허용합니다."""
    row = db.get(Member, (room_id, owner))
    if row is None:
        raise HTTPException(404, "대화방을 찾을 수 없습니다.")
    return row


def lock_room(db: Session, room_id: int) -> Room:
    """메시지와 멤버 변경을 같은 대화방 행 잠금으로 직렬화합니다."""
    lock_sqlite_write(db)
    room = db.get(Room, room_id, with_for_update=True)
    if not room:
        raise HTTPException(404, "대화방을 찾을 수 없습니다.")
    return room


def dm(engine: Engine, owner: int, peer: int) -> int:
    """참여자 쌍마다 하나의 DM을 열거나 재사용합니다."""
    if owner == peer:
        raise HTTPException(422, "다른 연락처를 선택하세요.")
    key = ":".join(map(str, sorted((owner, peer))))
    try:
        with Session(engine) as db, db.begin():
            lock_sqlite_write(db)
            if not db.get(Account, peer):
                raise HTTPException(404, "연락처를 찾을 수 없습니다.")
            existing = db.scalar(select(Room.id).where(Room.dm_key == key))
            if existing is not None:
                return existing
            room = Room(owner_id=owner, name="", team=None, dm_key=key)
            db.add(room)
            db.flush()
            db.add_all(
                [
                    Member(
                        room_id=room.id, account_id=account, joined_after=0, last_read=0
                    )
                    for account in (owner, peer)
                ]
            )
            return room.id
    except IntegrityError:
        with Session(engine) as db:
            existing = db.scalar(select(Room.id).where(Room.dm_key == key))
            if existing is None:
                raise
            return existing


def group(engine: Engine, owner: int, name: str, team: str) -> int:
    """팀 대화방을 만들고 만든 사람을 관리자로 등록합니다."""
    with Session(engine) as db, db.begin():
        room = Room(owner_id=owner, name=name, team=team, dm_key=None)
        db.add(room)
        db.flush()
        db.add(Member(room_id=room.id, account_id=owner, joined_after=0, last_read=0))
        return room.id


def change_member(
    engine: Engine, room_id: int, owner: int, contact: int, remove: bool
) -> None:
    """팀방 관리자만 다른 사용자를 초대하거나 내보낼 수 있습니다."""
    with Session(engine) as db, db.begin():
        room = lock_room(db, room_id)
        membership(db, room_id, owner)
        if room.team is None or room.owner_id != owner or contact == owner:
            raise HTTPException(403, "팀 대화방 관리자만 참여자를 변경할 수 있습니다.")
        member = db.get(Member, (room_id, contact))
        if remove and member:
            db.delete(member)
        elif not remove and not member:
            if not db.get(Account, contact):
                raise HTTPException(404, "연락처를 찾을 수 없습니다.")
            latest = (
                db.scalar(
                    select(func.max(Message.id)).where(Message.room_id == room_id)
                )
                or 0
            )
            db.add(
                Member(
                    room_id=room_id,
                    account_id=contact,
                    joined_after=latest,
                    last_read=latest,
                )
            )


def detail(engine: Engine, room_id: int, owner: int, before: int | None) -> dict:
    """참여 이후의 최근 메시지와 현재 참여자를 반환합니다."""
    with Session(engine) as db:
        member = membership(db, room_id, owner)
        contacts = db.scalars(
            select(Account)
            .join(Member)
            .where(Member.room_id == room_id)
            .order_by(Account.id)
        )
        members = [contact_view(account) for account in contacts]
        query = (
            select(Message, Account)
            .join(Account)
            .where(Message.room_id == room_id, Message.id > member.joined_after)
        )
        if before is not None:
            query = query.where(Message.id < before)
        rows = list(db.execute(query.order_by(Message.id.desc()).limit(51)))
        messages = [
            {
                "id": msg.id,
                "sender": msg.sender,
                "name": contact_view(account)["name"],
                "body": msg.body,
                "sent_at": msg.sent_at,
            }
            for msg, account in reversed(rows[:50])
        ]
        return {
            "members": members,
            "messages": messages,
            "has_more": len(rows) > 50,
            "me": owner,
        }


def send(engine: Engine, room_id: int, owner: int, body: str) -> int:
    """소속을 확인하고 메시지를 저장합니다."""
    with Session(engine) as db, db.begin():
        lock_room(db, room_id)
        membership(db, room_id, owner)
        message = Message(
            room_id=room_id,
            sender=owner,
            body=body,
            sent_at=datetime.now(UTC).isoformat(timespec="seconds"),
        )
        db.add(message)
        db.flush()
        return message.id


def read(engine: Engine, room_id: int, owner: int, message_id: int) -> None:
    """해당 방에서 확인한 메시지까지만 읽음으로 처리합니다."""
    with Session(engine) as db, db.begin():
        lock_room(db, room_id)
        member = membership(db, room_id, owner)
        message = db.get(Message, message_id)
        if not message or message.room_id != room_id:
            raise HTTPException(404, "메시지를 찾을 수 없습니다.")
        member.last_read = max(member.last_read, message_id)
