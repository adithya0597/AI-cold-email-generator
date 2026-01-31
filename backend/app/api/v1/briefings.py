"""
Briefing API endpoints for JobPilot.

Provides endpoints for:
    - Retrieving the latest briefing
    - Viewing briefing history (paginated, last 30 days)
    - Marking a briefing as read
    - Reading and updating briefing settings (time, timezone, channels)

All endpoints require an authenticated user (user_id from query param for now;
will use Clerk JWT extraction once auth middleware is wired).

Route ordering: Static paths (/latest, /settings) are registered BEFORE
the dynamic path (/{briefing_id}) to prevent FastAPI from matching
"latest" or "settings" as a briefing_id.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/briefings", tags=["briefings"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class BriefingResponse(BaseModel):
    """A single briefing record."""

    id: str
    user_id: str
    content: Dict[str, Any]
    briefing_type: str
    generated_at: str
    delivered_at: Optional[str] = None
    delivery_channels: List[str] = []
    read_at: Optional[str] = None
    schema_version: int = 1


class BriefingSettingsResponse(BaseModel):
    """Current briefing configuration."""

    briefing_hour: int
    briefing_minute: int
    briefing_timezone: str
    briefing_channels: List[str]


class BriefingSettingsUpdate(BaseModel):
    """Update briefing settings."""

    briefing_hour: int = Field(ge=0, le=23, description="Hour (0-23)")
    briefing_minute: int = Field(ge=0, le=59, description="Minute (0-59)")
    briefing_timezone: str = Field(
        default="UTC", description="IANA timezone name"
    )
    briefing_channels: List[str] = Field(
        default=["in_app", "email"],
        description="Delivery channels: in_app, email, or both",
    )


class BriefingHistoryResponse(BaseModel):
    """Paginated briefing history."""

    briefings: List[BriefingResponse]
    total: int
    has_more: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _briefing_to_response(briefing) -> BriefingResponse:
    """Convert a Briefing ORM model to a response schema."""
    return BriefingResponse(
        id=str(briefing.id),
        user_id=str(briefing.user_id),
        content=briefing.content or {},
        briefing_type=briefing.briefing_type or "full",
        generated_at=(
            briefing.generated_at.isoformat() if briefing.generated_at else ""
        ),
        delivered_at=(
            briefing.delivered_at.isoformat() if briefing.delivered_at else None
        ),
        delivery_channels=briefing.delivery_channels or [],
        read_at=(
            briefing.read_at.isoformat() if briefing.read_at else None
        ),
        schema_version=briefing.schema_version or 1,
    )


# ---------------------------------------------------------------------------
# Endpoints -- static paths first, then dynamic /{briefing_id}
# ---------------------------------------------------------------------------


@router.get("/latest", response_model=Optional[BriefingResponse])
async def get_latest_briefing(user_id: str = Query(..., description="User ID")):
    """Get the most recent briefing for the authenticated user.

    Returns the latest briefing or null if no briefings exist yet.
    New users will see an empty-state response from the frontend.
    """
    from sqlalchemy import select

    from app.db.engine import AsyncSessionLocal
    from app.db.models import Briefing

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Briefing)
            .where(Briefing.user_id == user_id)
            .order_by(Briefing.generated_at.desc())
            .limit(1)
        )
        briefing = result.scalars().first()

    if not briefing:
        return None

    return _briefing_to_response(briefing)


@router.get("/settings", response_model=BriefingSettingsResponse)
async def get_briefing_settings(
    user_id: str = Query(..., description="User ID"),
):
    """Get current briefing configuration for the user."""
    from sqlalchemy import select

    from app.db.engine import AsyncSessionLocal
    from app.db.models import UserPreference

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        prefs = result.scalars().first()

    if not prefs:
        # Return defaults
        return BriefingSettingsResponse(
            briefing_hour=8,
            briefing_minute=0,
            briefing_timezone="UTC",
            briefing_channels=["in_app", "email"],
        )

    return BriefingSettingsResponse(
        briefing_hour=prefs.briefing_hour or 8,
        briefing_minute=prefs.briefing_minute or 0,
        briefing_timezone=prefs.briefing_timezone or "UTC",
        briefing_channels=prefs.briefing_channels or ["in_app", "email"],
    )


@router.put("/settings", response_model=BriefingSettingsResponse)
async def update_briefing_settings(
    body: BriefingSettingsUpdate,
    user_id: str = Query(..., description="User ID"),
):
    """Update briefing time, timezone, and delivery channels.

    Also updates the RedBeat schedule so changes take effect from
    the next scheduled run.
    """
    from sqlalchemy import select, update

    from app.db.engine import AsyncSessionLocal
    from app.db.models import UserPreference

    # Validate channels
    valid_channels = {"in_app", "email"}
    if not body.briefing_channels or not set(body.briefing_channels).issubset(
        valid_channels
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid channels. Must be subset of {valid_channels}",
        )

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        prefs = result.scalars().first()

        if not prefs:
            raise HTTPException(
                status_code=404, detail="User preferences not found"
            )

        await session.execute(
            update(UserPreference)
            .where(UserPreference.user_id == user_id)
            .values(
                briefing_hour=body.briefing_hour,
                briefing_minute=body.briefing_minute,
                briefing_timezone=body.briefing_timezone,
                briefing_channels=body.briefing_channels,
            )
        )
        await session.commit()

    # Update RedBeat schedule
    try:
        from app.agents.briefing.scheduler import update_user_briefing_schedule

        update_user_briefing_schedule(
            user_id=user_id,
            hour=body.briefing_hour,
            minute=body.briefing_minute,
            tz=body.briefing_timezone,
            channels=body.briefing_channels,
        )
    except Exception as exc:
        logger.error(
            "Failed to update RedBeat schedule for user=%s: %s", user_id, exc
        )
        # Don't fail the request -- settings are saved in DB

    return BriefingSettingsResponse(
        briefing_hour=body.briefing_hour,
        briefing_minute=body.briefing_minute,
        briefing_timezone=body.briefing_timezone,
        briefing_channels=body.briefing_channels,
    )


@router.get("", response_model=BriefingHistoryResponse)
async def get_briefing_history(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Get paginated briefing history (last 30 days).

    Returns briefings ordered by generation time (newest first).
    """
    from sqlalchemy import func, select

    from app.db.engine import AsyncSessionLocal
    from app.db.models import Briefing

    since = datetime.now(timezone.utc) - timedelta(days=30)

    async with AsyncSessionLocal() as session:
        # Get total count
        count_result = await session.execute(
            select(func.count(Briefing.id)).where(
                Briefing.user_id == user_id,
                Briefing.generated_at >= since,
            )
        )
        total = count_result.scalar_one_or_none() or 0

        # Get paginated results
        result = await session.execute(
            select(Briefing)
            .where(
                Briefing.user_id == user_id,
                Briefing.generated_at >= since,
            )
            .order_by(Briefing.generated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        briefings = result.scalars().all()

    return BriefingHistoryResponse(
        briefings=[_briefing_to_response(b) for b in briefings],
        total=total,
        has_more=(offset + limit) < total,
    )


@router.post("/{briefing_id}/read")
async def mark_briefing_read(
    briefing_id: str,
    user_id: str = Query(..., description="User ID"),
):
    """Mark a briefing as read.

    Sets the ``read_at`` timestamp on the briefing record.
    """
    from app.agents.briefing.delivery import mark_briefing_read as _mark_read

    updated = await _mark_read(user_id, briefing_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Briefing not found")

    return {"status": "ok", "briefing_id": briefing_id, "read": True}


@router.get("/{briefing_id}", response_model=BriefingResponse)
async def get_briefing(
    briefing_id: str,
    user_id: str = Query(..., description="User ID"),
):
    """Get a specific briefing by ID."""
    from sqlalchemy import select

    from app.db.engine import AsyncSessionLocal
    from app.db.models import Briefing

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Briefing).where(
                Briefing.id == briefing_id,
                Briefing.user_id == user_id,
            )
        )
        briefing = result.scalars().first()

    if not briefing:
        raise HTTPException(status_code=404, detail="Briefing not found")

    return _briefing_to_response(briefing)
