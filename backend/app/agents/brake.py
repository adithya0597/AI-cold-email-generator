"""
Emergency brake module for the JobPilot agent framework.

Implements the brake state machine:

    RUNNING -> PAUSING -> PAUSED -> RESUMING -> RUNNING
                     \\-> PARTIAL (some tasks failed to stop)

State is stored in Redis:
    - ``paused:{user_id}`` -- simple flag checked by all agents before each step
    - ``brake_state:{user_id}`` -- hash with state, activated_at, paused_tasks

Functions:
    - ``check_brake(user_id)`` -- returns True if brake is active
    - ``check_brake_or_raise(user_id)`` -- raises BrakeActive if braked
    - ``activate_brake(user_id)`` -- sets brake, publishes event, schedules verification
    - ``resume_agents(user_id)`` -- clears brake, publishes event
    - ``get_brake_state(user_id)`` -- returns current state dict
    - ``verify_brake_completion(user_id)`` -- transitions PAUSING to PAUSED or PARTIAL
"""

from __future__ import annotations

import enum
import json
import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Brake state enum
# ---------------------------------------------------------------------------


class BrakeState(str, enum.Enum):
    """Emergency brake states."""

    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    PARTIAL = "partial"  # some tasks stuck / failed to pause
    RESUMING = "resuming"


# ---------------------------------------------------------------------------
# Redis helpers
# ---------------------------------------------------------------------------


async def _get_redis():
    """Create an async Redis client from application settings."""
    import redis.asyncio as aioredis

    from app.config import settings

    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def check_brake(user_id: str) -> bool:
    """Check if the emergency brake is active for a user.

    This is called by ``BaseAgent.run()`` and by the ``@requires_tier``
    decorator before every agent action.  It is intentionally cheap --
    a single Redis EXISTS command.
    """
    r = await _get_redis()
    try:
        result = await r.exists(f"paused:{user_id}")
        return bool(result)
    finally:
        await r.aclose()


async def check_brake_or_raise(user_id: str) -> None:
    """Check brake and raise ``BrakeActive`` if active.

    Convenience for calling between agent steps (before each LLM call,
    external API call, or database write).
    """
    if await check_brake(user_id):
        from app.agents.base import BrakeActive

        raise BrakeActive(f"Emergency brake active for {user_id}")


async def activate_brake(user_id: str) -> dict:
    """Activate the emergency brake for a user.

    1. Sets the Redis flag ``paused:{user_id}`` (checked by all agents).
    2. Sets the brake state hash to PAUSING with activation timestamp.
    3. Publishes a ``system.brake.activated`` event for WebSocket clients.
    4. Schedules a ``verify_brake_completion`` Celery task after 30 seconds.

    Returns:
        Dict with ``state`` and ``activated_at`` keys.
    """
    r = await _get_redis()
    now = datetime.now(timezone.utc)

    try:
        # Set the brake flag (checked by all agents)
        await r.set(f"paused:{user_id}", "1")

        # Set state machine to PAUSING
        await r.hset(
            f"brake_state:{user_id}",
            mapping={
                "state": BrakeState.PAUSING.value,
                "activated_at": now.isoformat(),
            },
        )

        # Publish brake event for WebSocket clients
        await r.publish(
            f"agent:status:{user_id}",
            json.dumps(
                {
                    "type": "system.brake.activated",
                    "event_id": str(uuid.uuid4()),
                    "timestamp": now.isoformat(),
                    "user_id": user_id,
                    "state": BrakeState.PAUSING.value,
                    "title": "Emergency brake activated",
                    "severity": "warning",
                }
            ),
        )
    finally:
        await r.aclose()

    # Schedule verification after 30 seconds to check if all tasks stopped
    try:
        from app.worker.celery_app import celery_app

        celery_app.send_task(
            "app.worker.tasks.verify_brake_completion",
            args=[user_id],
            countdown=30,
            queue="default",
        )
    except Exception as exc:
        logger.warning(
            "Failed to schedule brake verification for user=%s: %s",
            user_id,
            exc,
        )

    return {
        "state": BrakeState.PAUSING.value,
        "activated_at": now.isoformat(),
    }


async def resume_agents(user_id: str) -> dict:
    """Resume agent execution after an emergency brake.

    1. Sets brake state to RESUMING briefly.
    2. Deletes the Redis brake flag.
    3. Sets state to RUNNING.
    4. Publishes a ``system.brake.resumed`` event for WebSocket clients.

    Returns:
        Dict with ``state`` key set to ``"running"``.
    """
    r = await _get_redis()
    now = datetime.now(timezone.utc)

    try:
        # Transition through RESUMING
        await r.hset(f"brake_state:{user_id}", "state", BrakeState.RESUMING.value)

        # Clear the brake flag
        await r.delete(f"paused:{user_id}")

        # Set state to RUNNING
        await r.hset(f"brake_state:{user_id}", "state", BrakeState.RUNNING.value)

        # Publish resume event for WebSocket clients
        await r.publish(
            f"agent:status:{user_id}",
            json.dumps(
                {
                    "type": "system.brake.resumed",
                    "event_id": str(uuid.uuid4()),
                    "timestamp": now.isoformat(),
                    "user_id": user_id,
                    "state": BrakeState.RUNNING.value,
                    "title": "Agents resumed",
                    "severity": "info",
                }
            ),
        )
    finally:
        await r.aclose()

    return {"state": BrakeState.RUNNING.value}


async def get_brake_state(user_id: str) -> dict:
    """Return the current brake state for a user.

    Returns:
        Dict with keys ``state``, ``activated_at``, and ``paused_tasks_count``.
        Defaults to RUNNING if no brake state has ever been set.
    """
    r = await _get_redis()
    try:
        state_data = await r.hgetall(f"brake_state:{user_id}")
        if not state_data:
            return {
                "state": BrakeState.RUNNING.value,
                "activated_at": None,
                "paused_tasks_count": 0,
            }

        return {
            "state": state_data.get("state", BrakeState.RUNNING.value),
            "activated_at": state_data.get("activated_at"),
            "paused_tasks_count": int(state_data.get("paused_tasks_count", 0)),
        }
    finally:
        await r.aclose()


async def verify_brake_completion(user_id: str) -> dict:
    """Verify that all agent tasks have stopped after brake activation.

    Called by a Celery task 30 seconds after ``activate_brake()``.

    - If all tasks stopped: transitions state to PAUSED.
    - If some tasks are still running: transitions to PARTIAL with
      a list of stuck task IDs.
    - Marks all pending ``ApprovalQueueItem`` records for this user
      as ``status="paused"``.

    Returns:
        Dict with the resulting brake state.
    """
    from sqlalchemy import update

    from app.db.engine import AsyncSessionLocal
    from app.db.models import ApprovalQueueItem

    r = await _get_redis()
    now = datetime.now(timezone.utc)

    try:
        # Check if brake is still active (user might have resumed already)
        is_braked = await r.exists(f"paused:{user_id}")
        if not is_braked:
            logger.info(
                "Brake already cleared for user=%s, skipping verification",
                user_id,
            )
            return {"state": BrakeState.RUNNING.value}

        # Check for running Celery tasks for this user.
        # We inspect active tasks via Celery's inspect API.  This is best-effort
        # -- if the broker is unreachable we assume tasks have stopped.
        stuck_task_ids: list[str] = []
        try:
            from app.worker.celery_app import celery_app

            inspector = celery_app.control.inspect()
            active_tasks = inspector.active() or {}
            for _worker, tasks in active_tasks.items():
                for task in tasks:
                    task_args = task.get("args", [])
                    # Agent tasks have user_id as the first argument
                    if task_args and len(task_args) > 0 and task_args[0] == user_id:
                        stuck_task_ids.append(task.get("id", "unknown"))
        except Exception as exc:
            logger.warning(
                "Could not inspect Celery tasks for user=%s: %s", user_id, exc
            )

        if stuck_task_ids:
            new_state = BrakeState.PARTIAL.value
            await r.hset(
                f"brake_state:{user_id}",
                mapping={
                    "state": new_state,
                    "stuck_tasks": json.dumps(stuck_task_ids),
                    "paused_tasks_count": str(len(stuck_task_ids)),
                },
            )
            logger.warning(
                "Brake PARTIAL for user=%s: %d stuck tasks: %s",
                user_id,
                len(stuck_task_ids),
                stuck_task_ids,
            )
        else:
            new_state = BrakeState.PAUSED.value
            await r.hset(
                f"brake_state:{user_id}",
                mapping={
                    "state": new_state,
                    "paused_tasks_count": "0",
                },
            )
            logger.info("Brake fully PAUSED for user=%s", user_id)

        # Publish state transition event
        await r.publish(
            f"agent:status:{user_id}",
            json.dumps(
                {
                    "type": f"system.brake.{new_state}",
                    "event_id": str(uuid.uuid4()),
                    "timestamp": now.isoformat(),
                    "user_id": user_id,
                    "state": new_state,
                    "stuck_tasks": stuck_task_ids,
                }
            ),
        )
    finally:
        await r.aclose()

    # Mark all pending approval items as paused
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(ApprovalQueueItem)
                .where(
                    ApprovalQueueItem.user_id == user_id,
                    ApprovalQueueItem.status == "pending",
                )
                .values(status="paused")
            )
            await session.commit()
    except Exception as exc:
        logger.error(
            "Failed to pause approval items for user=%s: %s", user_id, exc
        )

    return {"state": new_state}
