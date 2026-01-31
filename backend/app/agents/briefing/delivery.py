"""
Briefing delivery module for JobPilot.

Handles dual delivery of briefings: in-app (DB + WebSocket notification)
and email (via Resend transactional email service).
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Email HTML template for briefings
# ---------------------------------------------------------------------------

_BRIEFING_EMAIL_TEMPLATE = """
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            max-width: 600px; margin: 0 auto; padding: 20px;
            background-color: #ffffff;">

    <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid #4F46E5;">
        <h1 style="color: #4F46E5; margin: 0; font-size: 24px;">JobPilot</h1>
        <p style="color: #6B7280; margin: 5px 0 0 0; font-size: 14px;">Your Daily Briefing</p>
    </div>

    <div style="padding: 24px 0;">
        <h2 style="color: #1F2937; font-size: 20px; margin: 0 0 8px 0;">
            Good {time_of_day}, {user_name}!
        </h2>
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
            {summary}
        </p>
    </div>

    <!-- Key Metrics -->
    <div style="display: flex; justify-content: space-around; padding: 16px;
                background-color: #F3F4F6; border-radius: 8px; margin-bottom: 24px;">
        <div style="text-align: center; padding: 0 12px;">
            <div style="font-size: 28px; font-weight: bold; color: #4F46E5;">{total_matches}</div>
            <div style="font-size: 12px; color: #6B7280; text-transform: uppercase;">New Matches</div>
        </div>
        <div style="text-align: center; padding: 0 12px;">
            <div style="font-size: 28px; font-weight: bold; color: #F59E0B;">{pending_approvals}</div>
            <div style="font-size: 12px; color: #6B7280; text-transform: uppercase;">Pending</div>
        </div>
        <div style="text-align: center; padding: 0 12px;">
            <div style="font-size: 28px; font-weight: bold; color: #10B981;">{applications_sent}</div>
            <div style="font-size: 12px; color: #6B7280; text-transform: uppercase;">Applied</div>
        </div>
    </div>

    <!-- Actions Needed -->
    {actions_html}

    <!-- New Matches -->
    {matches_html}

    <!-- Action Buttons -->
    <div style="text-align: center; padding: 24px 0;">
        <a href="{app_url}/dashboard"
           style="display: inline-block; padding: 12px 32px;
                  background-color: #4F46E5; color: #ffffff;
                  text-decoration: none; border-radius: 6px;
                  font-weight: 600; font-size: 14px; margin: 0 8px;">
            View in App
        </a>
        {approve_all_button}
    </div>

    <!-- Footer -->
    <div style="border-top: 1px solid #E5E7EB; padding: 16px 0; margin-top: 16px;">
        <p style="color: #9CA3AF; font-size: 12px; text-align: center; margin: 0;">
            You are receiving this because you have email briefings enabled in JobPilot.
            <a href="{unsubscribe_url}" style="color: #6B7280;">Unsubscribe</a>
        </p>
    </div>
</div>
"""


def _get_time_of_day() -> str:
    """Return a time-of-day greeting word based on current UTC hour."""
    hour = datetime.now(timezone.utc).hour
    if hour < 12:
        return "morning"
    elif hour < 17:
        return "afternoon"
    return "evening"


def _build_actions_html(actions: List[str]) -> str:
    """Build HTML for the actions-needed section."""
    if not actions:
        return ""
    items = "".join(
        f'<li style="padding: 4px 0; color: #374151;">{a}</li>' for a in actions
    )
    return f"""
    <div style="margin-bottom: 24px;">
        <h3 style="color: #1F2937; font-size: 16px; margin: 0 0 8px 0;">
            Actions Needed
        </h3>
        <ul style="margin: 0; padding-left: 20px;">{items}</ul>
    </div>
    """


def _build_matches_html(matches: List[Dict[str, Any]]) -> str:
    """Build HTML for the new-matches section."""
    if not matches:
        return ""
    items = "".join(
        f"""
        <div style="padding: 12px; border: 1px solid #E5E7EB;
                    border-radius: 6px; margin-bottom: 8px;">
            <div style="font-weight: 600; color: #1F2937;">{m.get('title', 'Unknown')}</div>
            <div style="color: #6B7280; font-size: 14px;">{m.get('company', '')}</div>
            <div style="color: #4F46E5; font-size: 13px; margin-top: 4px;">
                {m.get('reason', '')}
            </div>
        </div>
        """
        for m in matches[:5]
    )
    return f"""
    <div style="margin-bottom: 24px;">
        <h3 style="color: #1F2937; font-size: 16px; margin: 0 0 8px 0;">
            New Matches
        </h3>
        {items}
    </div>
    """


def _build_briefing_email_html(
    user_name: str,
    briefing_content: Dict[str, Any],
    app_url: str = "https://app.jobpilot.ai",
    unsubscribe_url: str = "#",
) -> str:
    """Build the full briefing email HTML from content dict."""
    metrics = briefing_content.get("metrics", {})
    pending = metrics.get("pending_approvals", 0)

    approve_all_button = ""
    if pending > 0:
        approve_all_button = f"""
        <a href="{app_url}/approvals?action=approve-all"
           style="display: inline-block; padding: 12px 32px;
                  background-color: #10B981; color: #ffffff;
                  text-decoration: none; border-radius: 6px;
                  font-weight: 600; font-size: 14px; margin: 0 8px;">
            Approve All ({pending})
        </a>
        """

    return _BRIEFING_EMAIL_TEMPLATE.format(
        time_of_day=_get_time_of_day(),
        user_name=user_name or "there",
        summary=briefing_content.get("summary", "Here is your daily update."),
        total_matches=metrics.get("total_matches", 0),
        pending_approvals=pending,
        applications_sent=metrics.get("applications_sent", 0),
        actions_html=_build_actions_html(
            briefing_content.get("actions_needed", [])
        ),
        matches_html=_build_matches_html(
            briefing_content.get("new_matches", [])
        ),
        app_url=app_url,
        approve_all_button=approve_all_button,
        unsubscribe_url=unsubscribe_url,
    )


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------


async def deliver_briefing(
    user_id: str,
    briefing_content: Dict[str, Any],
    channels: Optional[List[str]] = None,
) -> None:
    """Deliver a briefing via the specified channels.

    Args:
        user_id: The user's ID.
        briefing_content: The briefing content dict (from generator or fallback).
        channels: Delivery channels. Defaults to ["in_app", "email"].
    """
    channels = channels or ["in_app", "email"]
    briefing_id = briefing_content.get("briefing_id")
    now = datetime.now(timezone.utc)
    delivered_channels: List[str] = []

    # --- In-app delivery ---
    if "in_app" in channels:
        try:
            await _deliver_in_app(user_id, briefing_content)
            delivered_channels.append("in_app")
        except Exception as exc:
            logger.error(
                "In-app delivery failed for user=%s: %s", user_id, exc
            )

    # --- Email delivery ---
    if "email" in channels:
        try:
            await _deliver_email(user_id, briefing_content)
            delivered_channels.append("email")
        except Exception as exc:
            logger.error(
                "Email delivery failed for user=%s: %s", user_id, exc
            )

    # Update briefing record with delivery info
    if briefing_id and delivered_channels:
        try:
            await _update_delivery_status(briefing_id, now, delivered_channels)
        except Exception as exc:
            logger.error(
                "Failed to update delivery status for briefing=%s: %s",
                briefing_id,
                exc,
            )

    logger.info(
        "Briefing delivered for user=%s channels=%s",
        user_id,
        delivered_channels,
    )


async def _deliver_in_app(
    user_id: str, briefing_content: Dict[str, Any]
) -> None:
    """Publish a WebSocket event so the frontend knows a briefing is ready."""
    import redis.asyncio as aioredis

    from app.config import settings

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await r.publish(
            f"agent:status:{user_id}",
            json.dumps(
                {
                    "type": "system.briefing.ready",
                    "event_id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": user_id,
                    "title": "Your daily briefing is ready",
                    "severity": "action_required",
                    "data": {
                        "briefing_id": briefing_content.get("briefing_id"),
                        "briefing_type": briefing_content.get("briefing_type", "full"),
                    },
                }
            ),
        )
    finally:
        await r.aclose()


async def _deliver_email(
    user_id: str, briefing_content: Dict[str, Any]
) -> None:
    """Send the briefing via email using the transactional email service."""
    from sqlalchemy import select

    from app.db.engine import AsyncSessionLocal
    from app.db.models import User
    from app.services.transactional_email import send_email

    # Look up user email and name
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User.email, User.display_name).where(User.id == user_id)
        )
        row = result.one_or_none()
        if not row:
            logger.warning("User not found for email delivery: %s", user_id)
            return

    email, display_name = row
    user_name = display_name or "there"
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")

    html = _build_briefing_email_html(user_name, briefing_content)

    await send_email(
        to=email,
        subject=f"Your Daily JobPilot Briefing - {today}",
        html=html,
    )


async def _update_delivery_status(
    briefing_id: str,
    delivered_at: datetime,
    channels: List[str],
) -> None:
    """Update the briefing record with delivery timestamp and channels."""
    from sqlalchemy import update

    from app.db.engine import AsyncSessionLocal
    from app.db.models import Briefing

    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Briefing)
            .where(Briefing.id == briefing_id)
            .values(
                delivered_at=delivered_at,
                delivery_channels=channels,
            )
        )
        await session.commit()


# ---------------------------------------------------------------------------
# Mark as read
# ---------------------------------------------------------------------------


async def mark_briefing_read(user_id: str, briefing_id: str) -> bool:
    """Mark a briefing as read by setting ``read_at`` timestamp.

    Args:
        user_id: The user's ID (for ownership verification).
        briefing_id: The briefing record ID.

    Returns:
        True if the briefing was found and updated, False otherwise.
    """
    from sqlalchemy import update

    from app.db.engine import AsyncSessionLocal
    from app.db.models import Briefing

    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            update(Briefing)
            .where(
                Briefing.id == briefing_id,
                Briefing.user_id == user_id,
            )
            .values(read_at=now)
        )
        await session.commit()
        return result.rowcount > 0
