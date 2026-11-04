"""Redis helpers for the daily job queue."""

from __future__ import annotations

from redis import Redis

from app.core.config import settings

DAILY_QUEUE = "qatra:daily:queue"
DAILY_LOCK = "qatra:daily:lock"


def get_redis() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def enqueue_plot(public_id: str) -> int:
    r = get_redis()
    return int(r.rpush(DAILY_QUEUE, public_id))


def enqueue_many(public_ids: list[str], queue: str = DAILY_QUEUE) -> int:
    if not public_ids:
        return 0
    r = get_redis()
    r.rpush(queue, *public_ids)
    return len(public_ids)


def pop_plot(timeout: int = 2, queue: str = DAILY_QUEUE) -> str | None:
    r = get_redis()
    item = r.blpop(queue, timeout=timeout)
    if not item:
        return None
    return item[1]


def queue_length(queue: str = DAILY_QUEUE) -> int:
    return int(get_redis().llen(queue))
