"""
Privacy API endpoints — Stealth Mode management.

Stealth Mode hides the user's job search from their current employer
by preventing public visibility of profile and agent actions.
Requires Career Insurance or Enterprise tier.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.clerk import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/privacy", tags=["privacy"])

ELIGIBLE_TIERS = {"career_insurance", "enterprise"}


class StealthStatusResponse(BaseModel):
    stealth_enabled: bool
    tier: Optional[str] = None
    eligible: bool


class ToggleStealthRequest(BaseModel):
    enabled: bool


@router.get("/stealth", response_model=StealthStatusResponse)
async def get_stealth_status(
    user_id: str = Depends(get_current_user_id),
):
    """Return current stealth mode status and tier eligibility."""
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        # Ensure stealth_settings table exists
        await session.execute(text(
            "CREATE TABLE IF NOT EXISTS stealth_settings ("
            "  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
            "  user_id TEXT NOT NULL UNIQUE,"
            "  stealth_enabled BOOLEAN NOT NULL DEFAULT FALSE,"
            "  enabled_at TIMESTAMPTZ,"
            "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            ")"
        ))
        await session.commit()

        # Get user tier
        result = await session.execute(
            text("SELECT tier FROM users WHERE clerk_id = :uid"),
            {"uid": user_id},
        )
        row = result.mappings().first()
        tier = str(row["tier"]) if row else None
        eligible = tier in ELIGIBLE_TIERS

        # Get stealth status
        result = await session.execute(
            text(
                "SELECT stealth_enabled FROM stealth_settings "
                "WHERE user_id = :uid"
            ),
            {"uid": user_id},
        )
        stealth_row = result.mappings().first()
        stealth_enabled = bool(stealth_row["stealth_enabled"]) if stealth_row else False

        return StealthStatusResponse(
            stealth_enabled=stealth_enabled,
            tier=tier,
            eligible=eligible,
        )


@router.post("/stealth", response_model=StealthStatusResponse)
async def toggle_stealth(
    body: ToggleStealthRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Toggle stealth mode on or off. Requires Career Insurance or Enterprise tier."""
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        # Ensure stealth_settings table exists
        await session.execute(text(
            "CREATE TABLE IF NOT EXISTS stealth_settings ("
            "  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
            "  user_id TEXT NOT NULL UNIQUE,"
            "  stealth_enabled BOOLEAN NOT NULL DEFAULT FALSE,"
            "  enabled_at TIMESTAMPTZ,"
            "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            ")"
        ))
        await session.commit()

        # Check tier eligibility
        result = await session.execute(
            text("SELECT tier FROM users WHERE clerk_id = :uid"),
            {"uid": user_id},
        )
        row = result.mappings().first()
        tier = str(row["tier"]) if row else None
        eligible = tier in ELIGIBLE_TIERS

        if not eligible:
            raise HTTPException(
                status_code=403,
                detail="Stealth Mode requires Career Insurance or Enterprise tier.",
            )

        # Upsert stealth setting
        enabled_at_clause = "NOW()" if body.enabled else "NULL"
        await session.execute(
            text(
                "INSERT INTO stealth_settings (user_id, stealth_enabled, enabled_at) "
                "VALUES (:uid, :enabled, " + ("NOW()" if body.enabled else "NULL") + ") "
                "ON CONFLICT (user_id) DO UPDATE SET "
                "stealth_enabled = :enabled, "
                "enabled_at = " + ("NOW()" if body.enabled else "NULL")
            ),
            {"uid": user_id, "enabled": body.enabled},
        )
        await session.commit()

        return StealthStatusResponse(
            stealth_enabled=body.enabled,
            tier=tier,
            eligible=True,
        )
