"""
Learned Preferences API endpoints.

Provides endpoints for viewing and managing learned preferences:
  - GET /preferences/learned — list user's pending/acknowledged learned preferences
  - PATCH /preferences/learned/{id} — update status (acknowledge or reject)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk import get_current_user_id
from app.db.models import LearnedPreference, LearnedPreferenceStatus, User
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/preferences/learned", tags=["learned-preferences"])


# ============================================================
# ensure_user_exists dependency
# ============================================================


async def ensure_user_exists(
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get User record for the authenticated Clerk user."""
    result = await db.execute(select(User).where(User.clerk_id == clerk_user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ============================================================
# Pydantic schemas
# ============================================================


class LearnedPreferenceResponse(BaseModel):
    id: str
    pattern_type: str
    pattern_value: str
    confidence: float
    occurrences: int
    status: str
    created_at: str


class LearnedPreferenceStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("acknowledged", "rejected"):
            raise ValueError("Status must be 'acknowledged' or 'rejected'")
        return v


class LearnedPreferenceListResponse(BaseModel):
    data: List[LearnedPreferenceResponse]


# ============================================================
# Helpers
# ============================================================


def _pref_to_response(pref: LearnedPreference) -> LearnedPreferenceResponse:
    """Convert an ORM LearnedPreference to a response dict."""
    status_val = pref.status.value if hasattr(pref.status, "value") else str(pref.status)
    return LearnedPreferenceResponse(
        id=str(pref.id),
        pattern_type=pref.pattern_type,
        pattern_value=pref.pattern_value,
        confidence=float(pref.confidence),
        occurrences=pref.occurrences,
        status=status_val,
        created_at=pref.created_at.isoformat() if isinstance(pref.created_at, datetime) else str(pref.created_at),
    )


# ============================================================
# Endpoints
# ============================================================


@router.get("", response_model=LearnedPreferenceListResponse)
async def get_learned_preferences(
    user: User = Depends(ensure_user_exists),
    db: AsyncSession = Depends(get_db),
):
    """Return all non-deleted learned preferences for the current user."""
    result = await db.execute(
        select(LearnedPreference)
        .where(
            LearnedPreference.user_id == user.id,
            LearnedPreference.deleted_at.is_(None),
        )
        .order_by(LearnedPreference.created_at.desc())
    )
    prefs = result.scalars().all()

    return LearnedPreferenceListResponse(
        data=[_pref_to_response(p) for p in prefs]
    )


@router.patch("/{pref_id}", response_model=LearnedPreferenceResponse)
async def update_learned_preference_status(
    pref_id: str,
    body: LearnedPreferenceStatusUpdate,
    user: User = Depends(ensure_user_exists),
    db: AsyncSession = Depends(get_db),
):
    """Update a learned preference status to acknowledged or rejected.

    Rejecting a preference soft-deletes it to exclude from future detection.
    """
    result = await db.execute(
        select(LearnedPreference).where(
            LearnedPreference.id == pref_id,
            LearnedPreference.user_id == user.id,
            LearnedPreference.deleted_at.is_(None),
        )
    )
    pref = result.scalar_one_or_none()

    if not pref:
        raise HTTPException(status_code=404, detail="Learned preference not found")

    pref.status = LearnedPreferenceStatus(body.status)

    # Soft-delete rejected preferences
    if body.status == "rejected":
        pref.deleted_at = datetime.utcnow()
        pref.deleted_by = user.id
        pref.deletion_reason = "User rejected learned preference"

    await db.flush()
    await db.refresh(pref)

    return _pref_to_response(pref)
