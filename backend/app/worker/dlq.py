"""
Dead letter queue handler for failed Celery tasks.

Failed tasks are written to a Redis list keyed by ``dlq:{queue}`` with
a 7-day TTL so they can be inspected by operators without accumulating
indefinitely.

Uses the shared Redis client from ``app.cache.redis_client``.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# TTL for the DLQ key: 7 days in seconds
DLQ_TTL_SECONDS = 7 * 24 * 60 * 60


async def handle_task_failure(
    task_id: str,
    task_name: str,
    args: tuple | list,
    kwargs: dict,
    exc: Exception | str,
    queue: str = "default",
) -> None:
    """Write a failed task entry to the dead letter queue in Redis.

    Each entry is a JSON string pushed to the Redis list ``dlq:{queue}``.
    The list key is given a 7-day TTL (refreshed on each push) so stale
    entries are garbage-collected automatically.
    """
    client = await get_redis_client()
    entry = json.dumps({
        "task_id": task_id,
        "task_name": task_name,
        "args": list(args) if args else [],
        "kwargs": kwargs or {},
        "error": str(exc),
        "error_type": type(exc).__name__ if isinstance(exc, Exception) else "str",
        "failed_at": datetime.now(timezone.utc).isoformat(),
    })
    key = f"dlq:{queue}"
    await client.lpush(key, entry)
    await client.expire(key, DLQ_TTL_SECONDS)
    logger.warning(
        "Task %s (%s) sent to DLQ queue=%s: %s",
        task_id,
        task_name,
        queue,
        str(exc)[:200],
    )


async def get_dlq_contents(queue: str = "default", limit: int = 50) -> list[dict]:
    """Return the most recent failed task entries from the DLQ.

    Returns up to *limit* entries, each parsed from JSON.
    """
    client = await get_redis_client()
    key = f"dlq:{queue}"
    raw_entries = await client.lrange(key, 0, limit - 1)
    return [json.loads(entry) for entry in raw_entries]


async def dlq_length(queue: str = "default") -> int:
    """Return the number of items in the dead letter queue."""
    client = await get_redis_client()
    return await client.llen(f"dlq:{queue}")


async def clear_dlq(queue: str = "default") -> int:
    """Clear all entries from the dead letter queue.

    Returns the number of entries that were removed.
    """
    client = await get_redis_client()
    key = f"dlq:{queue}"
    count = await client.llen(key)
    await client.delete(key)
    return count
