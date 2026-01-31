"""
Health check endpoint for the JobPilot API.

Reports application status including optional checks for database
and Redis connectivity.  Both external checks degrade gracefully --
the health endpoint always returns 200 so load-balancers can
distinguish "app is running" from "dependency is down".
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


async def _check_redis() -> bool:
    """Return True if Redis is reachable, False otherwise."""
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await client.ping()
        await client.aclose()
        return True
    except Exception as exc:
        logger.debug("Redis health check failed: %s", exc)
        return False


async def _check_db() -> bool:
    """Return True if the database is reachable, False otherwise."""
    try:
        from sqlalchemy import text

        from app.db.engine import engine

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.debug("Database health check failed: %s", exc)
        return False


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Application health check.

    Returns overall status, version, environment, and per-dependency
    connectivity results.  Status is ``healthy`` when all checks pass
    or ``degraded`` when at least one external dependency is unreachable.
    """
    redis_ok = await _check_redis()
    db_ok = await _check_db()

    services: Dict[str, bool] = {
        "redis": redis_ok,
        "database": db_ok,
    }

    overall = "healthy" if all(services.values()) else "degraded"

    return {
        "status": overall,
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "services": services,
    }
