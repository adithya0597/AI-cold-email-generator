"""
Orchestrator module for the JobPilot agent framework.

Provides deterministic task routing (NO LLM-based routing), shared user
context loading, and Celery task dispatch.  This is a module-level
singleton -- import and call the functions directly.

Architecture: Custom orchestrator chosen via ADR-1.

Components:
    - ``TaskRouter`` -- maps task types to Celery task names, validates
      brake/tier before dispatching.
    - ``dispatch_task()`` -- routes and sends a task to Celery.
    - ``get_user_context()`` -- loads shared memory accessible to all agents
      (profile, preferences, recent history) with Redis caching.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Task type -> Celery task name mapping
# ---------------------------------------------------------------------------

TASK_ROUTING: dict[str, str] = {
    "job_scout": "app.worker.tasks.agent_job_scout",
    "resume": "app.worker.tasks.agent_resume",
    "apply": "app.worker.tasks.agent_apply",
    "pipeline": "app.worker.tasks.agent_pipeline",
    "briefing": "app.worker.tasks.briefing_generate",
}

# Task types that go to the "agents" queue (vs "briefings", "default", etc.)
# Queue routing is already configured in celery_app.py by naming convention:
#   agent_* -> agents, briefing_* -> briefings, * -> default
# So we just need to pick the right task name; Celery handles queue routing.


# ---------------------------------------------------------------------------
# TaskRouter
# ---------------------------------------------------------------------------


class TaskRouter:
    """Deterministic task router -- NO LLM involved.

    Routes task types to Celery task names.  Before routing, checks the
    emergency brake and validates the user's autonomy tier.  All routing
    decisions are logged to the ``agent_activities`` table.
    """

    def route_task(self, task_type: str, user_id: str, task_data: dict) -> str:
        """Return the Celery task name for the given task type.

        Args:
            task_type: One of ``"job_scout"``, ``"resume"``, ``"apply"``,
                ``"briefing"``.
            user_id: The user requesting the task.
            task_data: Arbitrary JSON-serializable payload.

        Returns:
            The fully-qualified Celery task name string.

        Raises:
            ValueError: If *task_type* is not recognised.
        """
        task_name = TASK_ROUTING.get(task_type)
        if task_name is None:
            raise ValueError(
                f"Unknown task type '{task_type}'. "
                f"Valid types: {list(TASK_ROUTING.keys())}"
            )
        return task_name


# Module-level singleton
_router = TaskRouter()


async def dispatch_task(
    task_type: str,
    user_id: str,
    task_data: dict | None = None,
) -> str:
    """Route a task and send it to Celery for execution.

    1. Checks emergency brake (raises ``BrakeActive`` if active).
    2. Validates autonomy tier allows this task type.
    3. Resolves the Celery task name via ``TaskRouter``.
    4. Sends the task to Celery via ``.apply_async()``.
    5. Logs the routing decision to ``agent_activities``.

    Args:
        task_type: One of the supported task types.
        user_id: The user requesting the task.
        task_data: Arbitrary JSON-serializable payload.

    Returns:
        The Celery ``task_id`` string for tracking.

    Raises:
        BrakeActive: If the emergency brake is active for the user.
        TierViolation: If the user's tier does not allow this task type.
        ValueError: If *task_type* is not recognised.
    """
    from app.agents.brake import check_brake_or_raise
    from app.agents.tier_enforcer import AutonomyGate

    task_data = task_data or {}

    # 1. Check brake (raises BrakeActive)
    await check_brake_or_raise(user_id)

    # 2. Check autonomy tier
    gate = AutonomyGate()
    # Briefings are always "read" operations; job_scout is "read";
    # resume/apply are "write" since they produce artifacts or take action.
    action_type = "write" if task_type in ("apply",) else "read"
    decision = await gate.check(user_id, action_type)

    if decision == "blocked":
        from app.agents.base import TierViolation

        raise TierViolation(
            f"User's autonomy tier does not allow task type '{task_type}'"
        )

    # 3. Route to Celery task name
    task_name = _router.route_task(task_type, user_id, task_data)

    # 4. Dispatch via Celery
    from app.worker.celery_app import celery_app

    result = celery_app.send_task(
        task_name,
        args=[user_id, task_data],
        kwargs={},
    )
    celery_task_id = result.id

    logger.info(
        "Dispatched task_type=%s for user=%s -> %s (celery_id=%s, tier_decision=%s)",
        task_type,
        user_id,
        task_name,
        celery_task_id,
        decision,
    )

    # 5. Log routing decision to agent_activities
    try:
        await _record_routing_activity(
            user_id=user_id,
            task_type=task_type,
            task_name=task_name,
            celery_task_id=celery_task_id,
            tier_decision=decision,
        )
    except Exception as exc:
        # Fire-and-forget -- never break the dispatch path
        logger.error("Failed to record routing activity: %s", exc)

    return celery_task_id


async def get_user_context(user_id: str) -> dict[str, Any]:
    """Load shared context accessible to all agents for a user.

    Returns a dictionary with the user's profile, preferences, and recent
    agent output history.  Results are cached in Redis with a 5-minute TTL
    to avoid per-agent database queries.

    This is the "shared memory" from Story 3-1 acceptance criteria.

    Args:
        user_id: The user whose context to load.

    Returns:
        Dict with keys ``profile``, ``preferences``, ``recent_outputs``.
    """
    import redis.asyncio as aioredis

    from app.config import settings

    cache_key = f"user_context:{user_id}"
    cache_ttl = 300  # 5 minutes

    # Try cache first
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        cached = await r.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as exc:
        logger.warning("Redis cache read failed for user_context: %s", exc)
    finally:
        await r.aclose()

    # Cache miss -- load from DB
    context = await _load_user_context_from_db(user_id)

    # Write to cache
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await r.set(cache_key, json.dumps(context, default=str), ex=cache_ttl)
    except Exception as exc:
        logger.warning("Redis cache write failed for user_context: %s", exc)
    finally:
        await r.aclose()

    return context


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _load_user_context_from_db(user_id: str) -> dict[str, Any]:
    """Load user profile, preferences, and recent outputs from PostgreSQL."""
    from sqlalchemy import select

    from app.db.engine import AsyncSessionLocal
    from app.db.models import AgentOutput as AgentOutputModel
    from app.db.models import Profile, UserPreference

    context: dict[str, Any] = {
        "profile": None,
        "preferences": None,
        "recent_outputs": [],
    }

    async with AsyncSessionLocal() as session:
        # Profile
        result = await session.execute(
            select(Profile).where(Profile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile:
            context["profile"] = {
                "skills": profile.skills or [],
                "headline": profile.headline,
                "experience": profile.experience or [],
                "education": profile.education or [],
            }

        # Preferences
        result = await session.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        pref = result.scalar_one_or_none()
        if pref:
            context["preferences"] = {
                "autonomy_level": pref.autonomy_level,
                "target_titles": pref.target_titles or [],
                "target_locations": pref.target_locations or [],
                "salary_minimum": pref.salary_minimum,
                "work_arrangement": pref.work_arrangement,
                "requires_h1b_sponsorship": pref.requires_h1b_sponsorship,
                "briefing_hour": pref.briefing_hour,
                "briefing_timezone": pref.briefing_timezone,
            }

        # Recent agent outputs (last 10, most recent first)
        result = await session.execute(
            select(AgentOutputModel)
            .where(AgentOutputModel.user_id == user_id)
            .order_by(AgentOutputModel.created_at.desc())
            .limit(10)
        )
        outputs = result.scalars().all()
        context["recent_outputs"] = [
            {
                "agent_type": o.agent_type,
                "output": o.output,
                "created_at": (
                    o.created_at.isoformat() if o.created_at else None
                ),
            }
            for o in outputs
        ]

    return context


async def _record_routing_activity(
    user_id: str,
    task_type: str,
    task_name: str,
    celery_task_id: str,
    tier_decision: str,
) -> None:
    """Log a routing decision to the agent_activities table."""
    from app.db.engine import AsyncSessionLocal
    from app.db.models import AgentActivity

    async with AsyncSessionLocal() as session:
        activity = AgentActivity(
            user_id=user_id,
            event_type=f"orchestrator.route.{task_type}",
            agent_type="orchestrator",
            title=f"Task routed: {task_type} -> {task_name}",
            severity="info",
            data={
                "task_type": task_type,
                "task_name": task_name,
                "celery_task_id": celery_task_id,
                "tier_decision": tier_decision,
                "routed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        session.add(activity)
        await session.commit()
