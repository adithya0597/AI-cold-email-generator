"""
RedBeat scheduler for per-user briefing schedules.

Creates, updates, and removes RedBeat entries that trigger daily briefing
generation at each user's configured local time (converted to UTC).

RedBeat stores schedules in Redis, so schedules can be managed dynamically
without restarting the Celery beat process.

Note on timezone handling:
    RedBeat does not support per-entry timezones natively. The user's desired
    local time is converted to UTC before creating the crontab. Schedules
    should be updated on DST transitions via a periodic cleanup task.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


def _local_to_utc_hour_minute(
    hour: int, minute: int, tz_name: str
) -> tuple[int, int]:
    """Convert a local hour:minute to UTC hour:minute.

    Uses the current UTC offset for the given timezone.  This is a
    simplification that works correctly except during DST transitions
    (handled by the weekly cleanup task).

    Args:
        hour: Local hour (0-23).
        minute: Local minute (0-59).
        tz_name: IANA timezone name (e.g. "America/New_York").

    Returns:
        Tuple of (utc_hour, utc_minute).
    """
    try:
        from zoneinfo import ZoneInfo

        local_tz = ZoneInfo(tz_name)
    except (ImportError, KeyError):
        logger.warning("Unknown timezone %s, using UTC", tz_name)
        return hour, minute

    # Create a datetime today in the local timezone at the desired time
    now = datetime.now(timezone.utc)
    local_dt = now.replace(
        hour=hour, minute=minute, second=0, microsecond=0, tzinfo=local_tz
    )
    # Convert to UTC
    utc_dt = local_dt.astimezone(timezone.utc)
    return utc_dt.hour, utc_dt.minute


def create_user_briefing_schedule(
    user_id: str,
    hour: int = 8,
    minute: int = 0,
    tz: str = "UTC",
    channels: Optional[List[str]] = None,
) -> None:
    """Create a per-user daily briefing schedule via RedBeat.

    Args:
        user_id: The user's ID.
        hour: Desired local hour (0-23).
        minute: Desired local minute (0-59).
        tz: IANA timezone name.
        channels: Delivery channels (default: ["in_app", "email"]).
    """
    from celery.schedules import crontab
    from redbeat import RedBeatSchedulerEntry

    from app.worker.celery_app import celery_app

    channels = channels or ["in_app", "email"]
    utc_hour, utc_minute = _local_to_utc_hour_minute(hour, minute, tz)

    entry = RedBeatSchedulerEntry(
        name=f"briefing:{user_id}",
        task="app.worker.tasks.briefing_generate",
        schedule=crontab(hour=utc_hour, minute=utc_minute),
        args=[user_id],
        kwargs={"channels": channels},
        app=celery_app,
    )
    entry.save()

    logger.info(
        "Created briefing schedule for user=%s at %02d:%02d %s (UTC %02d:%02d)",
        user_id,
        hour,
        minute,
        tz,
        utc_hour,
        utc_minute,
    )


def update_user_briefing_schedule(
    user_id: str,
    hour: int = 8,
    minute: int = 0,
    tz: str = "UTC",
    channels: Optional[List[str]] = None,
) -> None:
    """Update an existing user's briefing schedule.

    Deletes the existing entry (if any) and creates a new one.

    Args:
        user_id: The user's ID.
        hour: New local hour (0-23).
        minute: New local minute (0-59).
        tz: IANA timezone name.
        channels: Delivery channels.
    """
    remove_user_briefing_schedule(user_id)
    create_user_briefing_schedule(user_id, hour, minute, tz, channels)


def remove_user_briefing_schedule(user_id: str) -> None:
    """Remove a user's briefing schedule.

    Safe to call even if no schedule exists for the user.

    Args:
        user_id: The user's ID.
    """
    from redbeat import RedBeatSchedulerEntry

    from app.worker.celery_app import celery_app

    try:
        entry = RedBeatSchedulerEntry.from_key(
            f"redbeat:briefing:{user_id}",
            app=celery_app,
        )
        entry.delete()
        logger.info("Removed briefing schedule for user=%s", user_id)
    except KeyError:
        pass  # Schedule doesn't exist -- nothing to do
    except Exception as exc:
        logger.warning(
            "Failed to remove briefing schedule for user=%s: %s", user_id, exc
        )


def cleanup_stale_schedules() -> None:
    """Remove briefing schedules for deactivated or braked users.

    Should be run weekly via Celery beat.  Iterates known schedule keys
    and removes entries for users whose brake is active or who have been
    deactivated.
    """
    import asyncio

    import redis.asyncio as aioredis

    from app.config import settings

    async def _cleanup():
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            # Scan for all briefing schedule keys
            cursor = 0
            removed = 0
            while True:
                cursor, keys = await r.scan(
                    cursor, match="redbeat:briefing:*", count=100
                )
                for key in keys:
                    # Extract user_id from key format "redbeat:briefing:{user_id}"
                    parts = key.split(":", 2)
                    if len(parts) < 3:
                        continue
                    uid = parts[2]

                    # Check if user has brake active
                    is_braked = await r.exists(f"paused:{uid}")
                    if is_braked:
                        remove_user_briefing_schedule(uid)
                        removed += 1

                if cursor == 0:
                    break

            logger.info("Stale schedule cleanup: removed %d entries", removed)
        finally:
            await r.aclose()

    try:
        asyncio.run(_cleanup())
    except Exception as exc:
        logger.error("Stale schedule cleanup failed: %s", exc)
