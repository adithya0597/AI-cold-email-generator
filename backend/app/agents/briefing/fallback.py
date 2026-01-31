"""
Briefing fallback module for JobPilot.

Wraps the full briefing generator with error handling: on failure, returns
a lite briefing from Redis cache (48h TTL) and schedules a retry in 1 hour.

Fallback hierarchy:
    1. Full briefing (generator.py) -- LLM-summarised, fresh data
    2. Lite briefing from Redis cache -- last successful briefing data
    3. Minimal briefing -- "check back soon" message (no cache available)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

logger = logging.getLogger(__name__)


async def generate_briefing_with_fallback(user_id: str) -> Dict[str, Any]:
    """Generate a briefing with lite fallback on failure.

    Attempts the full briefing pipeline. On any failure:
        1. Logs to Sentry (if configured)
        2. Returns a lite briefing from cache
        3. Schedules a retry in 1 hour

    Returns:
        Briefing content dict (full or lite).
    """
    try:
        from app.agents.briefing.generator import generate_full_briefing

        briefing = await generate_full_briefing(user_id)
        return briefing

    except Exception as exc:
        logger.error(
            "Briefing generation failed for user=%s: %s", user_id, exc, exc_info=True
        )

        # Alert ops team via Sentry
        try:
            import sentry_sdk

            sentry_sdk.capture_exception(exc)
        except Exception:
            pass  # Sentry not configured

        # Generate lite briefing from cache
        lite = await generate_lite_briefing(user_id)

        # Store the lite briefing in DB
        try:
            from app.agents.briefing.generator import _store_briefing

            now = datetime.now(timezone.utc)
            briefing_id = await _store_briefing(user_id, lite, now)
            lite["briefing_id"] = briefing_id
        except Exception as store_exc:
            logger.error(
                "Failed to store lite briefing for user=%s: %s", user_id, store_exc
            )

        # Schedule retry in 1 hour
        try:
            from app.worker.celery_app import celery_app

            celery_app.send_task(
                "app.worker.tasks.briefing_generate",
                args=[user_id],
                countdown=3600,  # 1 hour
                queue="briefings",
            )
            logger.info("Briefing retry scheduled in 1h for user=%s", user_id)
        except Exception as retry_exc:
            logger.warning(
                "Failed to schedule briefing retry for user=%s: %s",
                user_id,
                retry_exc,
            )

        return lite


async def generate_lite_briefing(user_id: str) -> Dict[str, Any]:
    """Generate a lite briefing from cached data.

    Checks Redis for the last successful briefing (cached with 48h TTL).
    If cache hit: returns a lite briefing with the cached data.
    If cache miss: returns a minimal "check back soon" message.

    Returns:
        Lite briefing content dict.
    """
    now = datetime.now(timezone.utc)

    try:
        import redis.asyncio as aioredis

        from app.config import settings

        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            cached = await r.get(f"briefing_cache:{user_id}")
        finally:
            await r.aclose()

        if cached:
            previous = json.loads(cached)
            return {
                "briefing_type": "lite",
                "summary": (
                    "We're having some trouble generating your full briefing today. "
                    "Here's what we know from your last briefing:"
                ),
                "actions_needed": previous.get("actions_needed", []),
                "new_matches": previous.get("new_matches", [])[:5],
                "activity_log": previous.get("activity_log", [])[:5],
                "metrics": previous.get("metrics", {
                    "total_matches": 0,
                    "pending_approvals": 0,
                    "applications_sent": 0,
                }),
                "last_known_pipeline": previous.get("activity_log", [])[:3],
                "cached_matches": previous.get("new_matches", [])[:5],
                "generated_at": now.isoformat(),
                "cached_from": previous.get("generated_at"),
            }

    except Exception as exc:
        logger.warning(
            "Failed to read briefing cache for user=%s: %s", user_id, exc
        )

    # No cache available -- minimal briefing
    return {
        "briefing_type": "lite",
        "summary": "We're having some trouble today. Check back soon!",
        "actions_needed": [],
        "new_matches": [],
        "activity_log": [],
        "metrics": {
            "total_matches": 0,
            "pending_approvals": 0,
            "applications_sent": 0,
        },
        "generated_at": now.isoformat(),
    }
