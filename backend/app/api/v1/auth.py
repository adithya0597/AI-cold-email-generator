"""
Auth sync endpoint for Clerk user record management.

POST /api/v1/auth/sync -- called by the frontend ProtectedRoute after
Clerk authentication to ensure a local ``users`` row exists for the
authenticated Clerk user.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk import get_current_user_id
from app.db.models import User
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/sync")
async def sync_user(
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Find or create a local user record for the authenticated Clerk user.

    Returns the user data and an ``is_new`` flag so the frontend can
    route new users to onboarding and returning users to the dashboard.
    """
    result = await db.execute(select(User).where(User.clerk_id == clerk_user_id))
    user = result.scalar_one_or_none()

    is_new = False
    if user is None:
        is_new = True
        user = User(clerk_id=clerk_user_id, email=f"{clerk_user_id}@pending.sync")
        db.add(user)
        await db.flush()
        await db.refresh(user)
        logger.info("Created new user record for clerk_id=%s", clerk_user_id)

    return {
        "user": {
            "id": str(user.id),
            "clerk_id": user.clerk_id,
            "email": user.email,
            "tier": user.tier.value if hasattr(user.tier, "value") else str(user.tier),
        },
        "is_new": is_new,
    }
