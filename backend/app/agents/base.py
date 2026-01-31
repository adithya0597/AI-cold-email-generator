"""
BaseAgent class and AgentOutput dataclass for JobPilot agent framework.

Every agent inherits from BaseAgent and overrides ``execute()``.  The ``run()``
entry point handles the full lifecycle: brake check, execute, record output
to the database, record an activity feed entry, and publish a real-time
WebSocket event via Redis pub/sub.

Langfuse ``@observe()`` is applied to ``run()`` for automatic tracing.
Celery tasks that invoke agents must create an explicit Langfuse trace at task
start (contextvars do not propagate across Celery process boundaries).

Architecture: Custom orchestrator chosen via ADR-1.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Agent output dataclass
# ---------------------------------------------------------------------------


@dataclass
class AgentOutput:
    """Standard structured output every agent must produce."""

    action: str
    rationale: str
    confidence: float = 0.0
    alternatives_considered: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "action": self.action,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "alternatives_considered": self.alternatives_considered,
            "data": self.data,
            "requires_approval": self.requires_approval,
        }


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class BrakeActive(Exception):
    """Raised when the emergency brake is active for a user."""

    pass


class TierViolation(Exception):
    """Raised when an action requires a higher autonomy tier."""

    pass


# ---------------------------------------------------------------------------
# BaseAgent
# ---------------------------------------------------------------------------


class BaseAgent:
    """Base class for all JobPilot agents.

    Lifecycle:
        1. ``run()`` -- entry point, checks brake, calls execute, records, publishes
        2. ``execute()`` -- abstract, subclasses override with agent-specific logic
        3. ``_record_output()`` -- persists to ``agent_outputs`` table
        4. ``_record_activity()`` -- persists to ``agent_activities`` table
        5. ``_publish_event()`` -- pushes to Redis pub/sub for WebSocket clients

    Class attributes:
        agent_type: Identifier string (e.g. ``"job_scout"``, ``"resume"``).
    """

    agent_type: str = "base"

    async def run(self, user_id: str, task_data: dict) -> AgentOutput:
        """Main entry point.  Checks brake, executes, records, publishes.

        Langfuse tracing note: In Celery tasks, create an explicit trace
        *before* calling ``run()`` because ``@observe()`` contextvars do not
        propagate across process boundaries.
        """
        from app.agents.brake import check_brake

        if await check_brake(user_id):
            raise BrakeActive(f"Emergency brake active for {user_id}")

        output = await self.execute(user_id, task_data)

        # Fire-and-forget persistence and event publishing.
        # Failures here are logged but never break the hot path.
        try:
            await self._record_output(user_id, output)
        except Exception as exc:
            logger.error("Failed to record output for user=%s: %s", user_id, exc)

        try:
            await self._record_activity(
                user_id=user_id,
                event_type=f"agent.{self.agent_type}.completed",
                title=f"{self.agent_type} completed: {output.action}",
                severity="info",
                data=output.to_dict(),
            )
        except Exception as exc:
            logger.error("Failed to record activity for user=%s: %s", user_id, exc)

        try:
            await self._publish_event(user_id, output)
        except Exception as exc:
            logger.error("Failed to publish event for user=%s: %s", user_id, exc)

        return output

    async def execute(self, user_id: str, task_data: dict) -> AgentOutput:
        """Override in subclass with actual agent logic."""
        raise NotImplementedError("Subclasses must implement execute()")

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    async def _record_output(self, user_id: str, output: AgentOutput) -> None:
        """Persist agent output to the ``agent_outputs`` table."""
        from app.db.engine import AsyncSessionLocal
        from app.db.models import AgentOutput as AgentOutputModel

        async with AsyncSessionLocal() as session:
            record = AgentOutputModel(
                agent_type=self.agent_type,
                user_id=user_id,
                output=output.to_dict(),
                schema_version=1,
            )
            session.add(record)
            await session.commit()

    async def _record_activity(
        self,
        user_id: str,
        event_type: str,
        title: str,
        severity: str = "info",
        data: dict | None = None,
    ) -> None:
        """Persist an activity entry to the ``agent_activities`` table."""
        from app.db.engine import AsyncSessionLocal
        from app.db.models import AgentActivity

        async with AsyncSessionLocal() as session:
            activity = AgentActivity(
                user_id=user_id,
                event_type=event_type,
                agent_type=self.agent_type,
                title=title,
                severity=severity,
                data=data or {},
            )
            session.add(activity)
            await session.commit()

    async def _publish_event(self, user_id: str, output: AgentOutput) -> None:
        """Push a real-time update via Redis pub/sub for WebSocket clients."""
        import redis.asyncio as aioredis

        from app.config import settings

        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            await r.publish(
                f"agent:status:{user_id}",
                json.dumps(
                    {
                        "type": f"agent.{self.agent_type}.completed",
                        "event_id": str(uuid.uuid4()),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "user_id": user_id,
                        "agent_type": self.agent_type,
                        "title": f"{self.agent_type} completed: {output.action}",
                        "severity": "info",
                        "data": {
                            "action": output.action,
                            "rationale": output.rationale,
                            "confidence": output.confidence,
                        },
                    }
                ),
            )
        finally:
            await r.aclose()

    async def _queue_for_approval(
        self,
        user_id: str,
        action_name: str,
        args: tuple,
        kwargs: dict,
    ) -> AgentOutput:
        """Store a pending action in the ``approval_queue`` table (L2 flow).

        Creates an ApprovalQueueItem with 48-hour default expiry and publishes
        an ``approval.new`` WebSocket event so the frontend can notify the user.
        """
        from datetime import timedelta

        import redis.asyncio as aioredis

        from app.config import settings
        from app.db.engine import AsyncSessionLocal
        from app.db.models import ApprovalQueueItem

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=48)

        async with AsyncSessionLocal() as session:
            item = ApprovalQueueItem(
                user_id=user_id,
                agent_type=self.agent_type,
                action_name=action_name,
                payload={"args": [str(a) for a in args], "kwargs": kwargs},
                status="pending",
                rationale=f"{action_name} requires L2 approval",
                confidence=0.0,
                expires_at=expires_at,
            )
            session.add(item)
            await session.commit()

        # Publish approval event for WebSocket
        try:
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            try:
                await r.publish(
                    f"agent:status:{user_id}",
                    json.dumps(
                        {
                            "type": "approval.new",
                            "event_id": str(uuid.uuid4()),
                            "timestamp": now.isoformat(),
                            "user_id": user_id,
                            "agent_type": self.agent_type,
                            "title": "New action requires your approval",
                            "severity": "action_required",
                            "data": {"action_name": action_name},
                        }
                    ),
                )
            finally:
                await r.aclose()
        except Exception as exc:
            logger.warning("Failed to publish approval event: %s", exc)

        return AgentOutput(
            action="queued_for_approval",
            rationale=f"{action_name} requires L2 approval",
            confidence=1.0,
            requires_approval=True,
        )
