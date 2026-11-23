"""LemonTalk HTTP 및 라이브 이벤트 API입니다."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.concurrency import run_in_threadpool

from app.modules.auth.auth_profile import account_id
from app.modules.auth.auth_router import Subject, session_employee

from . import talk_service, talk_store
from .talk_schemas import Dm, Group, Read, Send


def private_response(response: Response) -> None:
    """대화 데이터를 브라우저와 중간 프록시에 캐시하지 않습니다."""
    response.headers["Cache-Control"] = "private, no-store"


router = APIRouter(prefix="/api/v1/talk", dependencies=[Depends(private_response)])


def owner_id(subject: Subject) -> int:
    """채팅을 사용하는 로그인 계정의 ID를 구합니다."""
    return account_id(subject)


Owner = Annotated[int, Depends(owner_id)]


@router.get("/contacts")
def contacts(request: Request, owner: Owner) -> list[dict]:
    """LemonTalk 연락처를 반환합니다."""
    return talk_service.contacts(request.app.state.workplace_engine, owner)


@router.get("/contacts/{contact_id}/avatar")
def avatar(contact_id: int, request: Request, owner: Owner) -> Response:
    """인증된 연락망에서 프로필 사진을 제공합니다."""
    return Response(
        talk_service.avatar(request.app.state.workplace_engine, contact_id),
        media_type="image/webp",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/rooms")
def rooms(request: Request, owner: Owner) -> list[dict]:
    """참여 중인 방과 읽지 않은 수를 반환합니다."""
    return talk_service.room_snapshot(request.app.state.workplace_engine, owner)


@router.get("/events")
async def events(request: Request, owner: Owner) -> StreamingResponse:
    """별도 큐 없이 DB의 변경을 로그인한 클라이언트에 전달합니다."""
    engine = request.app.state.workplace_engine

    async def stream():
        """계정 채널을 구독해 알림이 올 때만 새 목록을 보냅니다."""
        previous = ""
        try:
            async with (
                Redis.from_url(talk_store.redis_url(), decode_responses=True) as redis,
                redis.pubsub(ignore_subscribe_messages=True) as pubsub,
            ):
                await pubsub.subscribe(talk_store.channel(owner))
                while not await request.is_disconnected():
                    await run_in_threadpool(session_employee, request)
                    snapshot = await run_in_threadpool(
                        talk_service.room_snapshot, engine, owner
                    )
                    payload = json.dumps(snapshot, ensure_ascii=False)
                    if payload != previous:
                        previous = payload
                        yield f"data: {payload}\n\n"
                    else:
                        yield ": keep-alive\n\n"
                    await pubsub.get_message(timeout=20, ignore_subscribe_messages=True)
        except (HTTPException, RedisError):
            return

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "private, no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/dm")
def dm(data: Dm, request: Request, owner: Owner) -> dict:
    """상대와의 1:1 방을 엽니다."""
    return {
        "id": talk_service.dm(request.app.state.workplace_engine, owner, data.contact)
    }


@router.post("/groups", status_code=201)
def group(data: Group, request: Request, owner: Owner) -> dict:
    """새 팀 대화방을 만듭니다."""
    return {
        "id": talk_service.group(
            request.app.state.workplace_engine, owner, data.name, data.team
        )
    }


@router.get("/rooms/{room_id}")
def detail(
    room_id: int, request: Request, owner: Owner, before: int | None = None
) -> dict:
    """대화 기록과 방 참여자를 조회합니다."""
    return talk_service.detail(
        request.app.state.workplace_engine, room_id, owner, before
    )


@router.post("/rooms/{room_id}/messages", status_code=201)
def send(room_id: int, data: Send, request: Request, owner: Owner) -> dict:
    """메시지를 저장하고 새로운 식별자를 반환합니다."""
    return talk_service.send(
        request.app.state.workplace_engine, room_id, owner, data.body
    )


@router.post("/rooms/{room_id}/read", status_code=204)
def read(room_id: int, data: Read, request: Request, owner: Owner) -> None:
    """사용자가 확인한 마지막 메시지를 기록합니다."""
    talk_service.read(
        request.app.state.workplace_engine, room_id, owner, data.message_id
    )


@router.put("/rooms/{room_id}/members/{contact}", status_code=204)
def invite(room_id: int, contact: int, request: Request, owner: Owner) -> None:
    """팀방에 연락처를 초대합니다."""
    talk_service.change_member(
        request.app.state.workplace_engine, room_id, owner, contact, remove=False
    )


@router.delete("/rooms/{room_id}/members/{contact}", status_code=204)
def remove(room_id: int, contact: int, request: Request, owner: Owner) -> None:
    """팀방에서 참여자를 내보냅니다."""
    talk_service.change_member(
        request.app.state.workplace_engine, room_id, owner, contact, remove=True
    )
