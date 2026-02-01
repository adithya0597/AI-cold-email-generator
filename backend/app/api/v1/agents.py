"""
Agent API endpoints for JobPilot.

Provides:
    - POST /agents/brake       -- activate emergency brake
    - POST /agents/resume      -- resume agents after brake
    - GET  /agents/brake/status -- current brake state
    - GET  /agents/activity     -- paginated agent activity feed
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class BrakeResponse(BaseModel):
    """Response after activating or resuming the brake."""

    state: str
    activated_at: Optional[str] = None


class BrakeStatusResponse(BaseModel):
    """Current brake state."""

    state: str
    activated_at: Optional[str] = None
    paused_tasks_count: int = 0


class EventItem(BaseModel):
    """A single event for REST recovery."""

    id: str
    event_type: str
    agent_type: Optional[str] = None
    title: str
    severity: str
    data: Dict[str, Any] = {}
    timestamp: str


class EventsResponse(BaseModel):
    """Events since a given timestamp."""

    events: List[EventItem]
    count: int


class ActivityItem(BaseModel):
    """A single agent activity record."""

    id: str
    event_type: str
    agent_type: Optional[str] = None
    title: str
    severity: str
    data: Dict[str, Any] = {}
    created_at: str


class ActivityFeedResponse(BaseModel):
    """Paginated activity feed."""

    activities: List[ActivityItem]
    total: int
    has_more: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/brake", response_model=BrakeResponse)
async def activate_brake(user_id: str = Query(..., description="User ID")):
    """Activate the emergency brake for the user.

    Immediately sets a Redis flag that all agents check before each step.
    Returns the transitional 'pausing' state; the system verifies full
    stop after 30 seconds.
    """
    from app.agents.brake import activate_brake as _activate

    result = await _activate(user_id)
    return BrakeResponse(
        state=result["state"],
        activated_at=result.get("activated_at"),
    )


@router.post("/resume", response_model=BrakeResponse)
async def resume_agents(user_id: str = Query(..., description="User ID")):
    """Resume agent execution after an emergency brake.

    Clears the Redis brake flag and transitions state back to 'running'.
    """
    from app.agents.brake import resume_agents as _resume

    result = await _resume(user_id)
    return BrakeResponse(state=result["state"])


@router.get("/brake/status", response_model=BrakeStatusResponse)
async def get_brake_status(user_id: str = Query(..., description="User ID")):
    """Return current brake state for the user.

    Useful for polling during the 'pausing' -> 'paused' transition.
    """
    from app.agents.brake import get_brake_state

    state = await get_brake_state(user_id)
    return BrakeStatusResponse(
        state=state["state"],
        activated_at=state.get("activated_at"),
        paused_tasks_count=state.get("paused_tasks_count", 0),
    )


@router.get("/activity", response_model=ActivityFeedResponse)
async def get_activity_feed(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Return paginated agent activity feed (newest first).

    Supports 'load more' pagination via offset parameter.
    """
    from sqlalchemy import func, select

    from app.db.engine import AsyncSessionLocal
    from app.db.models import AgentActivity

    async with AsyncSessionLocal() as session:
        # Total count
        count_result = await session.execute(
            select(func.count(AgentActivity.id)).where(
                AgentActivity.user_id == user_id,
            )
        )
        total = count_result.scalar_one_or_none() or 0

        # Paginated results (newest first)
        result = await session.execute(
            select(AgentActivity)
            .where(AgentActivity.user_id == user_id)
            .order_by(AgentActivity.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        activities = result.scalars().all()

    return ActivityFeedResponse(
        activities=[
            ActivityItem(
                id=str(a.id),
                event_type=a.event_type,
                agent_type=a.agent_type,
                title=a.title,
                severity=a.severity,
                data=a.data or {},
                created_at=a.created_at.isoformat() if a.created_at else "",
            )
            for a in activities
        ],
        total=total,
        has_more=(offset + limit) < total,
    )


@router.get("/events", response_model=EventsResponse)
async def get_events_since(
    user_id: str = Query(..., description="User ID"),
    since: str = Query(..., description="ISO 8601 timestamp to fetch events after"),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Return agent events since the given timestamp.

    Used as a REST fallback to recover events missed during WebSocket
    disconnection.  Returns events in chronological order (oldest first)
    so the client can replay them.
    """
    from datetime import datetime

    from sqlalchemy import select

    from app.db.engine import AsyncSessionLocal
    from app.db.models import AgentActivity

    since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentActivity)
            .where(
                AgentActivity.user_id == user_id,
                AgentActivity.created_at > since_dt,
            )
            .order_by(AgentActivity.created_at.asc())
            .limit(limit)
        )
        events = result.scalars().all()

    return EventsResponse(
        events=[
            EventItem(
                id=str(e.id),
                event_type=e.event_type,
                agent_type=e.agent_type,
                title=e.title,
                severity=e.severity,
                data=e.data or {},
                timestamp=e.created_at.isoformat() if e.created_at else "",
            )
            for e in events
        ],
        count=len(events),
    )
