"""
Briefing generator for JobPilot daily briefings.

Gathers data from agent outputs, application statuses, pending approvals,
and agent activity warnings, then summarises via an LLM call into a
structured briefing. Stores the result in the ``briefings`` table and
caches it in Redis (48h TTL) for fallback use.

Works even without real job data (Phase 4) -- placeholder sections are
returned for sections with no data.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data gathering (parallel, with per-query timeout)
# ---------------------------------------------------------------------------

_QUERY_TIMEOUT_SECONDS = 15


async def _get_recent_matches(user_id: str) -> List[Dict[str, Any]]:
    """Fetch recent job matches from agent_outputs (last 24h)."""
    try:
        from sqlalchemy import select

        from app.db.engine import AsyncSessionLocal
        from app.db.models import AgentOutput as AgentOutputModel

        since = datetime.now(timezone.utc) - timedelta(hours=24)
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AgentOutputModel)
                .where(
                    AgentOutputModel.user_id == user_id,
                    AgentOutputModel.agent_type == "job_scout",
                    AgentOutputModel.created_at >= since,
                )
                .order_by(AgentOutputModel.created_at.desc())
                .limit(20)
            )
            rows = result.scalars().all()
            return [
                {
                    "id": str(row.id),
                    "output": row.output,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in rows
            ]
    except Exception as exc:
        logger.warning("Failed to fetch recent matches for user=%s: %s", user_id, exc)
        return []


async def _get_application_updates(user_id: str) -> List[Dict[str, Any]]:
    """Fetch application/pipeline status changes (last 24h)."""
    try:
        from sqlalchemy import select

        from app.db.engine import AsyncSessionLocal
        from app.db.models import AgentOutput as AgentOutputModel

        since = datetime.now(timezone.utc) - timedelta(hours=24)
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AgentOutputModel)
                .where(
                    AgentOutputModel.user_id == user_id,
                    AgentOutputModel.agent_type.in_(["apply", "pipeline"]),
                    AgentOutputModel.created_at >= since,
                )
                .order_by(AgentOutputModel.created_at.desc())
                .limit(20)
            )
            rows = result.scalars().all()
            return [
                {
                    "id": str(row.id),
                    "agent_type": row.agent_type if hasattr(row.agent_type, 'value') else str(row.agent_type),
                    "output": row.output,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in rows
            ]
    except Exception as exc:
        logger.warning("Failed to fetch app updates for user=%s: %s", user_id, exc)
        return []


async def _get_pending_approval_count(user_id: str) -> int:
    """Count pending approval queue items."""
    try:
        from sqlalchemy import func, select

        from app.db.engine import AsyncSessionLocal
        from app.db.models import ApprovalQueueItem

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(func.count(ApprovalQueueItem.id)).where(
                    ApprovalQueueItem.user_id == user_id,
                    ApprovalQueueItem.status == "pending",
                )
            )
            return result.scalar_one_or_none() or 0
    except Exception as exc:
        logger.warning("Failed to count approvals for user=%s: %s", user_id, exc)
        return 0


async def _get_pending_approval_cards(user_id: str) -> List[Dict[str, Any]]:
    """Fetch pending approval items with job details for briefing cards."""
    try:
        from sqlalchemy import select

        from app.db.engine import AsyncSessionLocal
        from app.db.models import ApprovalQueueItem

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ApprovalQueueItem)
                .where(
                    ApprovalQueueItem.user_id == user_id,
                    ApprovalQueueItem.status == "pending",
                )
                .order_by(ApprovalQueueItem.created_at.desc())
                .limit(10)
            )
            rows = result.scalars().all()
            cards = []
            for row in rows:
                payload = row.payload or {}
                cards.append({
                    "item_id": str(row.id),
                    "job_title": payload.get("job_title", "Unknown"),
                    "company": payload.get("company", "Unknown"),
                    "submission_method": payload.get("submission_method", "unknown"),
                    "rationale": row.rationale or "",
                })
            return cards
    except Exception as exc:
        logger.warning("Failed to fetch approval cards for user=%s: %s", user_id, exc)
        return []


async def _get_agent_warnings(user_id: str) -> List[Dict[str, Any]]:
    """Fetch recent agent warnings/issues (last 24h)."""
    try:
        from sqlalchemy import select

        from app.db.engine import AsyncSessionLocal
        from app.db.models import AgentActivity

        since = datetime.now(timezone.utc) - timedelta(hours=24)
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AgentActivity)
                .where(
                    AgentActivity.user_id == user_id,
                    AgentActivity.severity == "warning",
                    AgentActivity.created_at >= since,
                )
                .order_by(AgentActivity.created_at.desc())
                .limit(10)
            )
            rows = result.scalars().all()
            return [
                {
                    "title": row.title,
                    "event_type": row.event_type,
                    "data": row.data,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in rows
            ]
    except Exception as exc:
        logger.warning("Failed to fetch warnings for user=%s: %s", user_id, exc)
        return []


# ---------------------------------------------------------------------------
# LLM summarisation
# ---------------------------------------------------------------------------

_LLM_TIMEOUT_SECONDS = 30

_BRIEFING_SYSTEM_PROMPT = """You are the JobPilot briefing agent. Summarise the
following job search activity into a daily briefing with these JSON sections:
- "summary": A 2-3 sentence paragraph summarising the day
- "actions_needed": A list of strings describing actions the user should take
- "new_matches": A list of objects with "title", "company", and "reason" keys
- "activity_log": A list of objects with "event" and "detail" keys
- "metrics": An object with "total_matches" (int), "pending_approvals" (int), "applications_sent" (int)

If there is no data for a section, return an empty list or zero value.
Return ONLY valid JSON, no markdown or explanation."""


async def _llm_summarise(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Call the LLM to produce a structured briefing summary.

    Returns a parsed dict or a fallback structure on failure.
    """
    try:
        import httpx

        from app.config import settings

        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set -- returning raw data as briefing")
            return _build_no_llm_briefing(raw_data)

        user_prompt = json.dumps(raw_data, default=str)

        async with httpx.AsyncClient(timeout=_LLM_TIMEOUT_SECONDS) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": _BRIEFING_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.3,
                    "max_tokens": 1500,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)

    except Exception as exc:
        logger.error("LLM summarisation failed: %s", exc)
        return _build_no_llm_briefing(raw_data)


def _build_no_llm_briefing(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build a briefing structure without LLM when the API is unavailable."""
    matches = raw_data.get("recent_matches", [])
    approvals = raw_data.get("pending_approvals", 0)
    updates = raw_data.get("application_updates", [])
    approval_cards = raw_data.get("pending_approval_cards", [])

    return {
        "summary": (
            f"Today you have {len(matches)} new job match(es), "
            f"{approvals} pending approval(s), and {len(updates)} pipeline update(s)."
        ),
        "actions_needed": (
            [f"Review {approvals} pending approval(s)"] if approvals > 0 else []
        ),
        "new_matches": [
            {
                "title": m.get("output", {}).get("action", "Unknown"),
                "company": "See details",
                "reason": m.get("output", {}).get("rationale", ""),
            }
            for m in matches[:10]
        ],
        "activity_log": [
            {"event": u.get("agent_type", "agent"), "detail": str(u.get("output", {}))}
            for u in updates[:10]
        ],
        "metrics": {
            "total_matches": len(matches),
            "pending_approvals": approvals,
            "applications_sent": len(
                [u for u in updates if u.get("agent_type") == "apply"]
            ),
        },
        "pending_approval_cards": approval_cards,
    }


# ---------------------------------------------------------------------------
# Empty state briefing for new users (Story 3-10)
# ---------------------------------------------------------------------------


def _build_empty_state_briefing() -> Dict[str, Any]:
    """Return an encouraging empty-state briefing for users with no data."""
    return {
        "summary": (
            "Your agent is still learning your preferences. "
            "Check back tomorrow for your first personalised briefing!"
        ),
        "actions_needed": [
            "Set up your job preferences to see matches here",
            "Upload your resume for tailored applications",
            "Configure your target job titles and locations",
        ],
        "new_matches": [],
        "activity_log": [],
        "metrics": {
            "total_matches": 0,
            "pending_approvals": 0,
            "applications_sent": 0,
        },
        "tips": [
            "Add more skills to your profile for better matches",
            "Fine-tune your deal-breakers to filter out irrelevant jobs",
            "Set your autonomy level to control how your agent acts",
        ],
    }


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------


async def generate_full_briefing(user_id: str) -> Dict[str, Any]:
    """Generate a complete daily briefing for a user.

    Gathers data in parallel (with per-query 15s timeout), summarises
    via LLM (30s timeout), stores in ``briefings`` table, and caches
    the result in Redis with 48h TTL for fallback use.

    Returns:
        The briefing content dict.
    """
    # Gather data in parallel with timeouts
    gather_results = await asyncio.gather(
        asyncio.wait_for(_get_recent_matches(user_id), timeout=_QUERY_TIMEOUT_SECONDS),
        asyncio.wait_for(_get_application_updates(user_id), timeout=_QUERY_TIMEOUT_SECONDS),
        asyncio.wait_for(_get_pending_approval_count(user_id), timeout=_QUERY_TIMEOUT_SECONDS),
        asyncio.wait_for(_get_agent_warnings(user_id), timeout=_QUERY_TIMEOUT_SECONDS),
        asyncio.wait_for(_get_pending_approval_cards(user_id), timeout=_QUERY_TIMEOUT_SECONDS),
        return_exceptions=True,
    )

    # Handle any timed-out queries gracefully
    recent_matches = gather_results[0] if not isinstance(gather_results[0], BaseException) else []
    application_updates = gather_results[1] if not isinstance(gather_results[1], BaseException) else []
    pending_approvals = gather_results[2] if not isinstance(gather_results[2], BaseException) else 0
    agent_warnings = gather_results[3] if not isinstance(gather_results[3], BaseException) else []
    approval_cards = gather_results[4] if not isinstance(gather_results[4], BaseException) else []

    # Check for empty state (new user, no data at all)
    has_any_data = (
        len(recent_matches) > 0
        or len(application_updates) > 0
        or pending_approvals > 0
        or len(agent_warnings) > 0
    )

    if not has_any_data:
        briefing_content = _build_empty_state_briefing()
    else:
        # Build raw data for LLM
        raw_data = {
            "recent_matches": recent_matches,
            "application_updates": application_updates,
            "pending_approvals": pending_approvals,
            "agent_warnings": agent_warnings,
            "pending_approval_cards": approval_cards,
        }
        briefing_content = await _llm_summarise(raw_data)

    now = datetime.now(timezone.utc)
    briefing_content["generated_at"] = now.isoformat()
    briefing_content["briefing_type"] = "full"

    # Store in briefings table
    briefing_id = await _store_briefing(user_id, briefing_content, now)
    briefing_content["briefing_id"] = briefing_id

    # Cache in Redis for fallback (48h TTL)
    await _cache_briefing(user_id, briefing_content)

    logger.info(
        "Full briefing generated for user=%s id=%s matches=%d approvals=%d",
        user_id,
        briefing_id,
        len(recent_matches),
        pending_approvals,
    )

    return briefing_content


async def _store_briefing(
    user_id: str,
    content: Dict[str, Any],
    generated_at: datetime,
) -> str:
    """Persist a briefing record to the database. Returns the briefing ID."""
    from app.db.engine import AsyncSessionLocal
    from app.db.models import Briefing

    async with AsyncSessionLocal() as session:
        briefing = Briefing(
            user_id=user_id,
            content=content,
            briefing_type=content.get("briefing_type", "full"),
            generated_at=generated_at,
            schema_version=1,
        )
        session.add(briefing)
        await session.commit()
        await session.refresh(briefing)
        return str(briefing.id)


async def _cache_briefing(user_id: str, content: Dict[str, Any]) -> None:
    """Cache a successful briefing in Redis with 48h TTL."""
    try:
        import redis.asyncio as aioredis

        from app.config import settings

        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            await r.set(
                f"briefing_cache:{user_id}",
                json.dumps(content, default=str),
                ex=86400 * 2,  # 48-hour TTL
            )
        finally:
            await r.aclose()
    except Exception as exc:
        logger.warning("Failed to cache briefing for user=%s: %s", user_id, exc)
