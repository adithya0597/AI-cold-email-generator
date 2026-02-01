"""
Celery task definitions for JobPilot.

IMPORTANT: All database and async imports are done LAZILY inside task
functions, never at module level.  This prevents the Celery worker from
creating an asyncio event loop at import time, which would conflict with
the loop that ``asyncio.run()`` creates when executing the task.

Task naming convention (used for queue routing -- see celery_app.py):
    agent_*    -> "agents" queue
    briefing_* -> "briefings" queue
    scrape_*   -> "scraping" queue
    *          -> "default" queue

Langfuse tracing: Each agent task creates an explicit Langfuse trace at
the start because Python ``contextvars`` do NOT propagate across Celery
process boundaries.  ``flush_traces()`` is called in every ``finally`` block.

Agent tasks are placeholders until their respective agents are built in
later phases.  The task structure and Langfuse integration are ready now.
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
# Agent tasks (agents queue)
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name="app.worker.tasks.agent_job_scout",
    queue="agents",
    max_retries=2,
    default_retry_delay=60,
)
def agent_job_scout(self, user_id: str, task_data: dict) -> Dict[str, Any]:
    """Run the Job Scout agent for a user.

    Queries job board APIs, deduplicates, scores against preferences,
    and creates Match records. Langfuse trace wraps the full execution.
    """
    logger.info("agent_job_scout started for user=%s", user_id)

    async def _execute():
        from app.agents.core.job_scout import JobScoutAgent
        from app.observability.langfuse_client import create_agent_trace, flush_traces

        trace = create_agent_trace(
            user_id=user_id,
            agent_type="job_scout",
            celery_task_id=self.request.id,
        )
        try:
            agent = JobScoutAgent()
            result = await agent.run(user_id, task_data)
            trace.update(output=result.to_dict())
            return result.to_dict()
        except Exception as exc:
            trace.update(level="ERROR", status_message=str(exc))
            raise
        finally:
            flush_traces()

    try:
        return _run_async(_execute())
    except Exception as exc:
        logger.exception("agent_job_scout failed for user=%s", user_id)
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="app.worker.tasks.agent_resume",
    queue="agents",
    max_retries=2,
    default_retry_delay=60,
)
def agent_resume(self, user_id: str, task_data: dict) -> Dict[str, Any]:
    """Run the Resume Tailoring agent for a user.

    Loads the user's profile and a target job, then produces a tailored
    resume via LLM and stores it in the documents table.
    """
    logger.info("agent_resume started for user=%s", user_id)

    async def _execute():
        from app.agents.pro.resume_agent import ResumeAgent
        from app.observability.langfuse_client import create_agent_trace, flush_traces

        trace = create_agent_trace(
            user_id=user_id,
            agent_type="resume",
            celery_task_id=self.request.id,
        )
        try:
            agent = ResumeAgent()
            result = await agent.run(user_id, task_data)
            trace.update(output=result.to_dict())
            return result.to_dict()
        except Exception as exc:
            trace.update(level="ERROR", status_message=str(exc))
            raise
        finally:
            flush_traces()

    try:
        return _run_async(_execute())
    except Exception as exc:
        logger.exception("agent_resume failed for user=%s", user_id)
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="app.worker.tasks.agent_apply",
    queue="agents",
    max_retries=1,
    default_retry_delay=120,
)
def agent_apply(self, user_id: str, task_data: dict) -> Dict[str, Any]:
    """Run the Application agent for a user.

    Placeholder -- the ApplyAgent class will be implemented in Phase 8.
    Fewer retries than other agents because application submission is
    not idempotent.
    """
    logger.info("agent_apply started for user=%s", user_id)

    async def _execute():
        from app.observability.langfuse_client import create_agent_trace, flush_traces

        trace = create_agent_trace(
            user_id=user_id,
            agent_type="apply",
            celery_task_id=self.request.id,
        )
        try:
            from app.agents.pro.apply_agent import ApplyAgent

            agent = ApplyAgent()
            result = await agent.run(user_id, task_data)
            trace.update(output=result.to_dict())
            return result.to_dict()
        except Exception as exc:
            trace.update(level="ERROR", status_message=str(exc))
            raise
        finally:
            flush_traces()

    try:
        return _run_async(_execute())
    except Exception as exc:
        logger.exception("agent_apply failed for user=%s", user_id)
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Briefing tasks (briefings queue)
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name="app.worker.tasks.briefing_generate",
    queue="briefings",
    max_retries=2,
    default_retry_delay=300,
)
def briefing_generate(
    self, user_id: str, channels: list | None = None
) -> Dict[str, Any]:
    """Generate and deliver a daily briefing for a user.

    Called by RedBeat per-user schedule or on-demand.  The actual
    briefing generator is implemented in Plan 05.
    """
    logger.info("briefing_generate started for user=%s channels=%s", user_id, channels)

    async def _execute():
        from app.observability.langfuse_client import create_agent_trace, flush_traces

        trace = create_agent_trace(
            user_id=user_id,
            agent_type="briefing",
            celery_task_id=self.request.id,
        )
        try:
            from app.agents.briefing.fallback import generate_briefing_with_fallback
            from app.agents.briefing.delivery import deliver_briefing

            briefing = await generate_briefing_with_fallback(user_id)
            if channels:
                await deliver_briefing(user_id, briefing, channels)
            trace.update(output=briefing)
            return briefing
        except Exception as exc:
            trace.update(level="ERROR", status_message=str(exc))
            raise
        finally:
            flush_traces()

    try:
        return _run_async(_execute())
    except Exception as exc:
        logger.exception("briefing_generate failed for user=%s", user_id)
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Infrastructure tasks (default queue)
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.worker.tasks.verify_brake_completion",
    queue="default",
    max_retries=1,
)
def verify_brake_completion(user_id: str) -> Dict[str, Any]:
    """Verify all agent tasks have stopped after emergency brake activation.

    Called 30 seconds after ``activate_brake()`` to transition the brake
    state from PAUSING to PAUSED (or PARTIAL if tasks are stuck).
    """
    logger.info("verify_brake_completion for user=%s", user_id)

    async def _execute():
        from app.agents.brake import verify_brake_completion as _verify

        return await _verify(user_id)

    return _run_async(_execute())


@celery_app.task(
    name="app.worker.tasks.cleanup_expired_approvals",
    queue="default",
)
def cleanup_expired_approvals() -> Dict[str, Any]:
    """Mark expired approval queue items as 'expired'.

    Runs periodically (every 6 hours) via Celery beat to prevent stale
    actions from being approved after their context is no longer valid.
    """
    logger.info("cleanup_expired_approvals started")

    async def _execute():
        from sqlalchemy import update

        from app.db.engine import AsyncSessionLocal
        from app.db.models import ApprovalQueueItem

        now = datetime.now(timezone.utc)

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                update(ApprovalQueueItem)
                .where(
                    ApprovalQueueItem.status == "pending",
                    ApprovalQueueItem.expires_at < now,
                )
                .values(status="expired")
            )
            await session.commit()
            expired_count = result.rowcount

        logger.info("Expired %d approval queue items", expired_count)
        return {"expired_count": expired_count}

    return _run_async(_execute())


# ---------------------------------------------------------------------------
# Zombie task cleanup (default queue)
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.worker.tasks.cleanup_zombie_tasks",
    queue="default",
    max_retries=0,
)
def cleanup_zombie_tasks() -> Dict[str, Any]:
    """Detect and revoke tasks that have been running longer than the hard timeout.

    Uses Celery's inspect API to list active tasks on all workers, then
    revokes any that started more than ``task_time_limit`` seconds ago
    (default 300s).  Runs every 5 minutes via beat_schedule.

    Returns dict with ``revoked_count`` and ``details`` list.
    """
    hard_timeout = celery_app.conf.task_time_limit or 300
    inspector = celery_app.control.inspect()
    active = inspector.active()

    if active is None:
        logger.warning("cleanup_zombie_tasks: no workers online (inspect returned None)")
        return {"revoked_count": 0, "details": [], "note": "no workers online"}

    now = datetime.now(timezone.utc).timestamp()
    revoked = []

    for worker_name, task_list in active.items():
        for task_info in task_list:
            # task_info["time_start"] is a Unix timestamp (float)
            time_start = task_info.get("time_start")
            if time_start is None:
                continue
            elapsed = now - time_start
            if elapsed > hard_timeout:
                task_id = task_info["id"]
                celery_app.control.revoke(task_id, terminate=True)
                logger.warning(
                    "Revoked zombie task %s (%s) on %s — running for %.0fs (limit %ds)",
                    task_id,
                    task_info.get("name", "unknown"),
                    worker_name,
                    elapsed,
                    hard_timeout,
                )
                revoked.append({
                    "task_id": task_id,
                    "task_name": task_info.get("name", "unknown"),
                    "worker": worker_name,
                    "elapsed_seconds": round(elapsed),
                })

    logger.info("cleanup_zombie_tasks: revoked %d tasks", len(revoked))
    return {"revoked_count": len(revoked), "details": revoked}


# ---------------------------------------------------------------------------
# Celery beat schedule (periodic tasks)
# ---------------------------------------------------------------------------

celery_app.conf.beat_schedule = {
    "cleanup-expired-approvals": {
        "task": "app.worker.tasks.cleanup_expired_approvals",
        "schedule": 6 * 60 * 60,  # Every 6 hours (in seconds)
    },
    "cleanup-zombie-tasks": {
        "task": "app.worker.tasks.cleanup_zombie_tasks",
        "schedule": 300,  # Every 5 minutes (in seconds)
    },
}


# ---------------------------------------------------------------------------
# Legacy tasks (kept for backward compatibility)
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
        from sqlalchemy import text

        from app.db.engine import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1 AS ok"))
            row = result.scalar_one()
            logger.info("DB check returned: %s", row)
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


@celery_app.task(
    name="app.worker.tasks.gdpr_permanent_delete",
    ignore_result=False,
)
def gdpr_permanent_delete(clerk_user_id: str) -> Dict[str, Any]:
    """Permanently delete all user data after the 30-day grace period.

    Checks whether the user cancelled deletion (cleared ``deleted_at``)
    before proceeding.  If ``deleted_at`` is still set, hard-deletes the
    user row — ``ON DELETE CASCADE`` removes all related data.

    Also cleans up files in Supabase Storage.
    """
    logger.info("GDPR permanent delete starting for user %s", clerk_user_id)

    def _run_async(coro):  # noqa: ANN001
        return asyncio.run(coro)

    async def _execute() -> Dict[str, Any]:
        from sqlalchemy import text

        from app.db.engine import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            # Check if deletion was cancelled
            result = await session.execute(
                text("SELECT deleted_at FROM users WHERE clerk_id = :uid"),
                {"uid": clerk_user_id},
            )
            row = result.first()

            if row is None:
                logger.info(
                    "User %s not found — may already be deleted", clerk_user_id
                )
                return {"status": "skipped", "reason": "user_not_found"}

            if row[0] is None:
                logger.info(
                    "User %s cancelled deletion (deleted_at cleared)", clerk_user_id
                )
                return {"status": "skipped", "reason": "deletion_cancelled"}

            # Clean up storage files
            try:
                from app.services.storage_service import delete_file

                # Delete known file patterns for this user
                await delete_file(f"{clerk_user_id}/", bucket="resumes")
            except Exception as exc:
                logger.warning(
                    "Storage cleanup failed for user %s: %s", clerk_user_id, exc
                )

            # Hard delete — CASCADE removes all related rows
            await session.execute(
                text("DELETE FROM users WHERE clerk_id = :uid"),
                {"uid": clerk_user_id},
            )
            await session.commit()
            logger.info("User %s permanently deleted", clerk_user_id)

            return {"status": "deleted", "user_id": clerk_user_id}

    return _run_async(_execute())


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
