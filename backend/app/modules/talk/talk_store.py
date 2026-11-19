"""Redis Streams, 보관 한도와 읽음 위치를 관리합니다."""

import logging
import os
from datetime import UTC, datetime
from functools import lru_cache
from typing import cast

from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)
StreamRows = list[tuple[str, dict[str, str]]]

PREFIX = "lemontree:talk:"
APPEND = """
local clock = redis.call('TIME')
local now = tonumber(clock[1]) * 1000000 + tonumber(clock[2])
local seq = math.max(now, tonumber(redis.call('GET', KEYS[3]) or '0') + 1)
local id = string.format('%.0f', seq) .. '-0'
redis.call('SET', KEYS[3], string.format('%.0f', seq))
redis.call('XADD', KEYS[1], id, 'sender', ARGV[2], 'name', ARGV[3],
    'body', ARGV[4], 'sent_at', ARGV[5], 'simulated', ARGV[6])
redis.call('EXPIRE', KEYS[1], tonumber(ARGV[7]))
redis.call('EXPIRE', KEYS[4], tonumber(ARGV[7]))
redis.call('ZADD', KEYS[2], seq, KEYS[1] .. '|' .. id)
local overflow = redis.call('XLEN', KEYS[1]) - tonumber(ARGV[8])
if overflow > 0 then
    for _, item in ipairs(redis.call('XRANGE', KEYS[1], '-', '+', 'COUNT', overflow)) do
        redis.call('XDEL', KEYS[1], item[1])
        redis.call('ZREM', KEYS[2], KEYS[1] .. '|' .. item[1])
    end
end
overflow = redis.call('ZCARD', KEYS[2]) - tonumber(ARGV[9])
if overflow > 0 then
    local oldest = redis.call('ZPOPMIN', KEYS[2], overflow)
    for i = 1, #oldest, 2 do
        local stream, entry = string.match(oldest[i], '^(.*)|([^|]+)$')
        redis.call('XDEL', stream, entry)
    end
end
for i = 10, #ARGV do
    redis.call('PUBLISH', ARGV[i], 'changed')
end
return id
"""


def redis_url() -> str:
    """Compose 또는 로컬 Redis 연결 주소를 가져옵니다."""
    return os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")


@lru_cache
def connection(url: str) -> Redis:
    """서버 프로세스의 Redis 커넥션 풀을 재사용합니다."""
    return Redis.from_url(
        url, decode_responses=True, socket_connect_timeout=3, socket_timeout=3
    )


def client() -> Redis:
    """현재 설정의 Redis 클라이언트를 반환합니다."""
    return connection(redis_url())


def channel(account: int) -> str:
    """계정별 알림 채널 이름을 반환합니다."""
    return f"{PREFIX}events:{account}"


def key(room: int) -> str:
    """대화방 메시지 키를 반환합니다."""
    return f"{PREFIX}room:{room}"


def ttl() -> int:
    """비활성 대화방의 보관 시간을 초로 반환합니다."""
    return max(1, int(os.getenv("TALK_TTL_SECONDS", "604800")))


def notify(*accounts: int) -> None:
    """대화 내용 없이 계정의 목록 변경만 발행합니다."""
    try:
        with client().pipeline(transaction=False) as pipe:
            for account in set(accounts):
                pipe.publish(channel(account), "changed")
            pipe.execute()
    except RedisError:
        logger.warning("Could not publish LemonTalk membership update")


def add(
    room: int,
    sender: int,
    name: str,
    body: str,
    members: list[int],
    simulated: bool = False,
) -> int:
    """메시지를 쓰고 방별·전역 오래된 기록을 원자적으로 정리합니다."""
    raw = cast(
        str,
        client().eval(
            APPEND,
            4,
            key(room),
            PREFIX + "timeline",
            PREFIX + "clock",
            f"{PREFIX}read:{room}",
            str(room),
            str(sender),
            name,
            body,
            datetime.now(UTC).isoformat(timespec="seconds"),
            str(int(simulated)),
            str(ttl()),
            str(max(1, int(os.getenv("TALK_ROOM_LIMIT", "1000")))),
            str(max(1, int(os.getenv("TALK_TOTAL_LIMIT", "3000")))),
            *(channel(account) for account in members),
        ),
    )
    return int(raw.split("-")[0])


def earliest(room: int) -> int:
    """보관 중인 첫 메시지 ID를 반환합니다."""
    rows = cast(StreamRows, client().xrange(key(room), count=1))
    return int(rows[0][0].split("-")[0]) if rows else 0


def latest(room: int) -> int:
    """현재 남은 마지막 메시지 ID를 반환합니다."""
    rows = cast(StreamRows, client().xrevrange(key(room), count=1))
    return int(rows[0][0].split("-")[0]) if rows else 0


def page(room: int, after: int, before: int | None) -> list[dict]:
    """접근 가능한 최근 51개 메시지를 최신순으로 조회합니다."""
    rows = cast(
        StreamRows,
        client().xrevrange(
            key(room),
            max=f"({before}-0" if before else "+",
            min=f"({after}-0",
            count=51,
        ),
    )
    return [
        {
            "id": int(raw.split("-")[0]),
            "sender": int(fields["sender"]),
            "name": fields["name"],
            "body": fields["body"],
            "sent_at": fields["sent_at"],
            "simulated": fields["simulated"] == "1",
        }
        for raw, fields in rows
    ]


def unread(room: int, account: int, after: int) -> int:
    """남아 있는 상대의 메시지만 읽지 않은 수로 계산합니다."""
    cursor = int(
        cast(str | None, client().hget(f"{PREFIX}read:{room}", str(account))) or 0
    )
    rows = cast(StreamRows, client().xrange(key(room), min=f"({max(cursor, after)}-0"))
    return sum(int(fields["sender"]) != account for _, fields in rows)


def mark(room: int, account: int, message: int) -> None:
    """시청한 메시지까지 읽음 위치를 갱신합니다."""
    redis = client()
    redis_key = f"{PREFIX}read:{room}"
    cursor = int(cast(str | None, redis.hget(redis_key, str(account))) or 0)
    with redis.pipeline() as pipe:
        pipe.hset(redis_key, str(account), str(max(cursor, message)))
        pipe.expire(redis_key, ttl())
        pipe.publish(channel(account), "changed")
        pipe.execute()
