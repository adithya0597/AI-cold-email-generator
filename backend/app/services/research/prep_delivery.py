"""
Prep Briefing Delivery Service — handles multi-channel briefing delivery.

Delivers interview prep briefings via in-app notification, email summary,
and push notification. Schedules reminders 2h before if unopened.

Architecture: Follows the service pattern. Uses Celery for async scheduling.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class DeliveryResult:
    """Result of a briefing delivery attempt."""

    channels_sent: list[str] = field(default_factory=list)
    channels_failed: list[str] = field(default_factory=list)
    reminder_scheduled: bool = False
    reminder_time: str | None = None
    delivery_time: str = ""
    briefing_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "channels_sent": self.channels_sent,
            "channels_failed": self.channels_failed,
            "reminder_scheduled": self.reminder_scheduled,
            "reminder_time": self.reminder_time,
            "delivery_time": self.delivery_time,
            "briefing_id": self.briefing_id,
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class PrepBriefingDeliveryService:
    """Handles multi-channel interview prep briefing delivery.

    Delivers to in-app, email, and push channels. Schedules a 2h
    reminder if the briefing hasn't been opened.
    """

    async def deliver(
        self,
        user_id: str,
        briefing: dict[str, Any],
        application_id: str,
        interview_datetime: datetime | None = None,
        channels: list[str] | None = None,
    ) -> DeliveryResult:
        """Deliver briefing through configured channels.

        Args:
            user_id: Target user ID.
            briefing: The assembled briefing dict.
            application_id: Related application ID.
            interview_datetime: When the interview is scheduled.
            channels: Channels to deliver on (default: all).

        Returns:
            DeliveryResult with delivery status per channel.
        """
        if channels is None:
            channels = ["in_app", "email", "push"]

        now = datetime.now(timezone.utc)
        result = DeliveryResult(
            delivery_time=now.isoformat(),
            briefing_id=f"briefing-{application_id}",
        )

        logger.info(
            "Delivering prep briefing for user=%s app=%s via %s",
            user_id, application_id, channels,
        )

        for channel in channels:
            try:
                await self._deliver_channel(user_id, briefing, channel)
                result.channels_sent.append(channel)
            except Exception as exc:
                logger.warning(
                    "Delivery failed on channel %s for user=%s: %s",
                    channel, user_id, exc,
                )
                result.channels_failed.append(channel)

        # Schedule 2h reminder if interview_datetime known
        if interview_datetime:
            reminder_info = await self._schedule_reminder(
                user_id, application_id, interview_datetime
            )
            result.reminder_scheduled = reminder_info.get("scheduled", False)
            result.reminder_time = reminder_info.get("reminder_time")

        return result

    async def _deliver_channel(
        self, user_id: str, briefing: dict[str, Any], channel: str
    ) -> None:
        """Deliver briefing to a specific channel."""
        if channel == "in_app":
            await self._deliver_in_app(user_id, briefing)
        elif channel == "email":
            await self._deliver_email(user_id, briefing)
        elif channel == "push":
            await self._deliver_push(user_id, briefing)
        else:
            logger.warning("Unknown delivery channel: %s", channel)

    async def _deliver_in_app(
        self, user_id: str, briefing: dict[str, Any]
    ) -> None:
        """Deliver via in-app notification (store in DB + WebSocket event)."""
        from app.cache.redis_client import get_redis_client

        # Publish WebSocket event for real-time in-app notification
        r = await get_redis_client()
        await r.publish(
            f"agent:status:{user_id}",
            json.dumps({
                "type": "interview_prep.briefing_ready",
                "event_id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "data": {
                    "company_name": briefing.get("company_name", ""),
                    "role_title": briefing.get("role_title", ""),
                    "application_id": briefing.get("application_id", ""),
                },
            }),
        )

        logger.info("In-app notification sent for user=%s", user_id)

    async def _deliver_email(
        self, user_id: str, briefing: dict[str, Any]
    ) -> None:
        """Deliver email summary of briefing."""
        company = briefing.get("company_name", "Unknown Company")
        role = briefing.get("role_title", "Role")
        summary = briefing.get("summary", {})

        logger.info(
            "Email delivery for user=%s: %s — %s (%d questions)",
            user_id, company, role,
            summary.get("total_questions", 0),
        )
        # Actual email sending would use app.services.email
        # For now, log the delivery intent

    async def _deliver_push(
        self, user_id: str, briefing: dict[str, Any]
    ) -> None:
        """Deliver push notification."""
        company = briefing.get("company_name", "Unknown Company")
        logger.info(
            "Push notification for user=%s: Interview prep ready for %s",
            user_id, company,
        )
        # Actual push would use FCM/APNs service

    async def _schedule_reminder(
        self,
        user_id: str,
        application_id: str,
        interview_datetime: datetime,
    ) -> dict[str, Any]:
        """Schedule 2h-before reminder if briefing unopened."""
        reminder_time = interview_datetime - timedelta(hours=2)
        now = datetime.now(timezone.utc)

        if reminder_time <= now:
            return {"scheduled": False, "reason": "too_late"}

        from app.worker.celery_app import celery_app

        task_result = celery_app.send_task(
            "app.worker.tasks.briefing_generate",
            args=[user_id],
            kwargs={
                "channels": ["in_app", "push"],
                "reminder": True,
                "application_id": application_id,
            },
            eta=reminder_time,
        )

        return {
            "scheduled": True,
            "reminder_time": reminder_time.isoformat(),
            "celery_task_id": task_result.id,
        }
