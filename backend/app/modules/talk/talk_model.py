"""LemonTalk 대화방, 참여자와 메시지를 영속화합니다."""

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Room(Base):
    """DM 또는 팀 대화방입니다."""

    __tablename__ = "talk_rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="대화방 ID")
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"), comment="대화방 관리자"
    )
    name: Mapped[str] = mapped_column(String(80), comment="팀 대화방 이름")
    team: Mapped[str | None] = mapped_column(String(40), comment="대화방의 팀")
    dm_key: Mapped[str | None] = mapped_column(
        String(64), unique=True, comment="DM 참여자 쌍의 고유 키"
    )


class Member(Base):
    """방 참여 시점과 마지막으로 읽은 메시지를 기록합니다."""

    __tablename__ = "talk_members"

    room_id: Mapped[int] = mapped_column(
        ForeignKey("talk_rooms.id"), primary_key=True, comment="대화방 ID"
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"), primary_key=True, index=True, comment="참여 계정 ID"
    )
    joined_after: Mapped[int] = mapped_column(
        BigInteger, comment="참여 전에 존재한 마지막 메시지 ID"
    )
    last_read: Mapped[int] = mapped_column(
        Integer, comment="마지막으로 확인한 메시지 ID"
    )


class Message(Base):
    """한 대화방에 보낸 텍스트 메시지입니다."""

    __tablename__ = "talk_messages"
    __table_args__ = (Index("ix_talk_messages_room_id_id", "room_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="메시지 ID")
    room_id: Mapped[int] = mapped_column(
        ForeignKey("talk_rooms.id"), comment="대화방 ID"
    )
    sender: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"), comment="보낸 계정 ID"
    )
    body: Mapped[str] = mapped_column(Text, comment="메시지 본문")
    sent_at: Mapped[str] = mapped_column(String(32), comment="메시지 전송 UTC 시각")
