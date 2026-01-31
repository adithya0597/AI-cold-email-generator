"""
Celery task definitions for JobPilot.

IMPORTANT: All database and async imports are done LAZILY inside task
functions, never at module level.  This prevents the Celery worker from
creating an asyncio event loop at import time, which would conflict with
the loop that ``asyncio.run()`` creates when executing the task.

Future agent types will follow the naming convention used in queue routing
(see celery_app.py):
    agent_*    -> "agents" queue
    briefing_* -> "briefings" queue
    scrape_*   -> "scraping" queue
    *          -> "default" queue

Pub/sub channels for future agent control:
    agent:pause:{user_id}   -- pause a running agent
    agent:resume:{user_id}  -- resume a paused agent
    agent:status:{user_id}  -- agent status updates (consumed by WebSocket)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: run an async function from within a sync Celery task
# ---------------------------------------------------------------------------

def _run_async(coro):
    """Execute an async coroutine from a synchronous Celery task.

    Uses ``asyncio.run()`` which creates a fresh event loop, executes the
    coroutine, and tears down the loop.  This is the recommended pattern
    for calling async code from Celery tasks.
    """
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Example / proof-of-concept task
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    name="app.worker.tasks.example_task",
    max_retries=3,
    default_retry_delay=30,
)
def example_task(self, user_id: str, task_data: dict) -> Dict[str, Any]:
    """Proof-of-concept task that writes to PostgreSQL via SQLAlchemy.

    Demonstrates the lazy-import + asyncio.run() pattern that all future
    tasks should follow.

    Args:
        user_id: The ID of the user who triggered the task.
        task_data: Arbitrary JSON-serialisable payload.

    Returns:
        Dict with status, user_id, and timestamp.
    """
    logger.info("example_task started for user=%s data=%s", user_id, task_data)

    async def _execute():
        # Lazy imports -- only loaded when the task actually runs,
        # NOT when the worker process starts.
        from sqlalchemy import text

        from app.db.engine import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            # Simple proof-of-life query -- confirms the worker can
            # reach PostgreSQL through SQLAlchemy's async engine.
            result = await session.execute(
                text("SELECT 1 AS ok")
            )
            row = result.scalar_one()
            logger.info("DB check returned: %s", row)

            # In a real task you would create/update domain objects here.
            # For example:
            #   user = await session.get(User, user_id)
            #   user.last_task_at = datetime.now(timezone.utc)
            #   await session.commit()

        return row

    try:
        db_result = _run_async(_execute())
    except Exception as exc:
        logger.exception("example_task failed for user=%s", user_id)
        raise self.retry(exc=exc)

    return {
        "status": "completed",
        "user_id": user_id,
        "db_check": db_result,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Health-check task (used by /health to verify worker liveness)
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.worker.tasks.health_check_task",
    ignore_result=False,
)
def health_check_task() -> Dict[str, str]:
    """Lightweight task used by the health endpoint to verify the worker
    is alive and processing messages.

    Returns:
        Dict with status and the worker's current UTC timestamp.
    """
    return {
        "status": "ok",
        "worker_time": datetime.now(timezone.utc).isoformat(),
    }
