"""대화방 접근 권한, 전송, 읽음과 멤버 변경을 처리합니다."""

import os

from fastapi import HTTPException
from redis.exceptions import RedisError
from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import lock_sqlite_write
from app.modules.auth.auth_model import Account
from app.modules.llm import llm_service
from app.modules.llm.llm_ollama import OllamaBusy

from . import talk_ai, talk_store
from .talk_model import Member, Room


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
            {
                **contact_view(row),
                "avatar_url": f"/api/v1/talk/contacts/{row.id}/avatar"
                if has_avatar
                else None,
            }
            for row, has_avatar in db.execute(
                select(Account, Account.avatar.is_not(None))
                .where(Account.id != owner)
                .order_by(Account.display_name, Account.id)
            )
        ]


def avatar(engine: Engine, contact: int) -> bytes:
    """LemonTalk 연락처에서 공개하는 프로필 사진을 반환합니다."""
    with Session(engine) as db:
        image = db.scalar(select(Account.avatar).where(Account.id == contact))
        if not image:
            raise HTTPException(404, "연락처 사진이 없습니다.")
        return image


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
            people = list(
                db.scalars(
                    select(Account).join(Member).where(Member.room_id == room.id)
                )
            )
            participants = len(people)
            peer = next((person for person in people if person.id != owner), None)
            name = contact_view(peer)["name"] if room.dm_key and peer else room.name
            latest = talk_store.latest(room.id)
            unread = talk_store.unread(room.id, owner, member.joined_after)
            results.append(
                {
                    "id": room.id,
                    "name": name,
                    "team": room.team,
                    "owner": room.owner_id == owner,
                    "latest": latest,
                    "earliest": talk_store.earliest(room.id),
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
            room_id = room.id
        talk_store.notify(owner, peer)
        return room_id
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
        room_id = room.id
    talk_store.notify(owner)
    return room_id


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
            latest = talk_store.latest(room_id)
            db.add(
                Member(
                    room_id=room_id,
                    account_id=contact,
                    joined_after=latest,
                    last_read=0,
                )
            )
        other_members = list(
            db.scalars(select(Member.account_id).where(Member.room_id == room_id))
        )
    talk_store.notify(owner, contact, *other_members)


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
        rows = talk_store.page(room_id, member.joined_after, before)
        return {
            "members": members,
            "messages": list(reversed(rows[:50])),
            "has_more": len(rows) > 50,
            "me": owner,
        }


def send(engine: Engine, room_id: int, owner: int, body: str) -> dict:
    """Redis에 메시지를 전송하고 직원 DM에서는 설정에 맞춘 자동 답장을 보냅니다."""
    with Session(engine) as db, db.begin():
        room = lock_room(db, room_id)
        member = membership(db, room_id, owner)
        joined_after = member.joined_after
        people = list(
            db.scalars(select(Account).join(Member).where(Member.room_id == room_id))
        )
        sender = next(account for account in people if account.id == owner)
        peer = next(
            (account for account in people if room.dm_key and account.id != owner), None
        )
        recipients = [account.id for account in people]
        message_id = talk_store.add(
            room_id, owner, contact_view(sender)["name"], body, recipients
        )
        staff = (
            (peer.id, peer.employee_id, contact_view(peer)["name"])
            if peer and peer.employee_id
            else None
        )
    result = {"id": message_id, "mock": "not_applicable"}
    if staff is None:
        return result

    staff_id, employee_id, staff_name = staff
    if os.getenv("WORKPLACE_LLM_MODE", "ollama") == "ollama":
        result["mock"] = send_ai_reply(
            engine, room_id, owner, body, message_id, joined_after, staff, recipients
        )
        return result
    status, reply, reservation = llm_service.prepare(engine, employee_id, body)
    result["mock"] = status
    if reservation is not None:
        delivered = False
        try:
            talk_store.add(
                room_id, staff_id, staff_name, reply, recipients, simulated=True
            )
            delivered = True
            result["mock"] = "sent"
        except RedisError:
            result["mock"] = "unavailable"
        finally:
            llm_service.settle(engine, reservation, delivered)
    return result


def send_ai_reply(
    engine: Engine,
    room_id: int,
    owner: int,
    body: str,
    message_id: int,
    joined_after: int,
    staff: tuple[int, str, str],
    recipients: list[int],
) -> str:
    """가상 예산을 예약하고 현재 방에 AI 답장을 저장한 뒤 정산합니다."""
    staff_id, employee_id, staff_name = staff
    try:
        recent = talk_store.page(room_id, joined_after, message_id, limit=6)
    except RedisError:
        return "ai_unavailable"
    charge = max(
        1,
        (len(body) + 420 + sum(min(len(row["body"]), 360) for row in recent) + 49)
        // 50,
    )
    reservation = llm_service.reserve(engine, employee_id, charge)
    if reservation is None:
        return "budget_exhausted"
    delivered = False
    try:
        reply = talk_ai.reply(employee_id, owner, body, recent)
        talk_store.add(room_id, staff_id, staff_name, reply, recipients, ai=True)
        delivered = True
        return "ai_sent"
    except OllamaBusy:
        return "ai_busy"
    except (HTTPException, RedisError):
        return "ai_unavailable"
    finally:
        llm_service.settle(engine, reservation, delivered)


def read(engine: Engine, room_id: int, owner: int, message_id: int) -> None:
    """해당 방에서 실제로 확인한 메시지만 읽음으로 저장합니다."""
    with Session(engine) as db, db.begin():
        lock_room(db, room_id)
        member = membership(db, room_id, owner)
        if message_id <= member.joined_after or not talk_store.client().xrange(
            talk_store.key(room_id),
            min=f"{message_id}-0",
            max=f"{message_id}-0",
            count=1,
        ):
            raise HTTPException(404, "보관 중인 메시지를 찾을 수 없습니다.")
        talk_store.mark(room_id, owner, message_id)
