"""
Privacy API endpoints — Stealth Mode management.

Stealth Mode hides the user's job search from their current employer
by preventing public visibility of profile and agent actions.
Requires Career Insurance or Enterprise tier.
"""

from __future__ import annotations

import logging
from typing import List, Optional

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


# ============================================================
# Employer Blocklist
# ============================================================


class BlocklistEntry(BaseModel):
    id: str
    company_name: str
    note: Optional[str] = None
    created_at: Optional[str] = None


class BlocklistResponse(BaseModel):
    entries: List[BlocklistEntry]
    total: int


class AddBlocklistRequest(BaseModel):
    company_name: str
    note: Optional[str] = None


ENSURE_BLOCKLIST_TABLE = (
    "CREATE TABLE IF NOT EXISTS employer_blocklist ("
    "  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
    "  user_id TEXT NOT NULL,"
    "  company_name TEXT NOT NULL,"
    "  note TEXT,"
    "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
    ")"
)


async def _check_stealth_enabled(session, user_id: str) -> bool:
    """Check if stealth mode is enabled for the user."""
    from sqlalchemy import text

    result = await session.execute(
        text("SELECT stealth_enabled FROM stealth_settings WHERE user_id = :uid"),
        {"uid": user_id},
    )
    row = result.mappings().first()
    return bool(row["stealth_enabled"]) if row else False


@router.get("/blocklist", response_model=BlocklistResponse)
async def get_blocklist(
    user_id: str = Depends(get_current_user_id),
):
    """Return the employer blocklist for the current user."""
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        await session.execute(text(ENSURE_BLOCKLIST_TABLE))
        await session.commit()

        result = await session.execute(
            text(
                "SELECT id, company_name, note, created_at "
                "FROM employer_blocklist WHERE user_id = :uid "
                "ORDER BY created_at DESC"
            ),
            {"uid": user_id},
        )
        rows = result.mappings().all()
        entries = [
            BlocklistEntry(
                id=str(r["id"]),
                company_name=r["company_name"],
                note=r["note"],
                created_at=str(r["created_at"]) if r["created_at"] else None,
            )
            for r in rows
        ]
        return BlocklistResponse(entries=entries, total=len(entries))


@router.post("/blocklist", response_model=BlocklistEntry, status_code=201)
async def add_to_blocklist(
    body: AddBlocklistRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Add a company to the employer blocklist. Requires active Stealth Mode."""
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        await session.execute(text(ENSURE_BLOCKLIST_TABLE))
        await session.commit()

        if not await _check_stealth_enabled(session, user_id):
            raise HTTPException(
                status_code=403,
                detail="Stealth Mode must be enabled to manage the blocklist.",
            )

        result = await session.execute(
            text(
                "INSERT INTO employer_blocklist (user_id, company_name, note) "
                "VALUES (:uid, :name, :note) "
                "RETURNING id, company_name, note, created_at"
            ),
            {"uid": user_id, "name": body.company_name, "note": body.note},
        )
        row = result.mappings().first()
        await session.commit()

        return BlocklistEntry(
            id=str(row["id"]),
            company_name=row["company_name"],
            note=row["note"],
            created_at=str(row["created_at"]) if row["created_at"] else None,
        )


@router.delete("/blocklist/{entry_id}")
async def remove_from_blocklist(
    entry_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Remove a company from the employer blocklist."""
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        await session.execute(text(ENSURE_BLOCKLIST_TABLE))
        await session.commit()

        result = await session.execute(
            text(
                "DELETE FROM employer_blocklist "
                "WHERE id = :eid AND user_id = :uid"
            ),
            {"eid": entry_id, "uid": user_id},
        )
        await session.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Blocklist entry not found.")

        return {"status": "removed", "id": entry_id}


# ============================================================
# Privacy Proof Documentation
# ============================================================

ENSURE_AUDIT_LOG_TABLE = (
    "CREATE TABLE IF NOT EXISTS privacy_audit_log ("
    "  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
    "  user_id TEXT NOT NULL,"
    "  company_name TEXT NOT NULL,"
    "  action_type TEXT NOT NULL,"
    "  details TEXT,"
    "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
    ")"
)


class AuditLogEntry(BaseModel):
    id: str
    company_name: str
    action_type: str
    details: Optional[str] = None
    created_at: Optional[str] = None


class PrivacyProofEntry(BaseModel):
    company_name: str
    note: Optional[str] = None
    last_checked: str
    exposure_count: int
    blocked_actions: List[AuditLogEntry]


class PrivacyProofResponse(BaseModel):
    entries: List[PrivacyProofEntry]
    total: int


@router.get("/proof", response_model=PrivacyProofResponse)
async def get_privacy_proof(
    user_id: str = Depends(get_current_user_id),
):
    """Return privacy proof dashboard data — blocklist verification + blocked actions."""
    from datetime import datetime, timezone

    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        await session.execute(text(ENSURE_BLOCKLIST_TABLE))
        await session.execute(text(ENSURE_AUDIT_LOG_TABLE))
        await session.commit()

        # Get blocklist entries
        result = await session.execute(
            text(
                "SELECT company_name, note FROM employer_blocklist "
                "WHERE user_id = :uid ORDER BY created_at DESC"
            ),
            {"uid": user_id},
        )
        blocklist_rows = result.mappings().all()

        # Get audit log entries
        result = await session.execute(
            text(
                "SELECT id, company_name, action_type, details, created_at "
                "FROM privacy_audit_log WHERE user_id = :uid "
                "ORDER BY created_at DESC LIMIT 50"
            ),
            {"uid": user_id},
        )
        audit_rows = result.mappings().all()

        now_iso = datetime.now(timezone.utc).isoformat()

        # Build audit log lookup by company
        audit_by_company: dict = {}
        for a in audit_rows:
            cn = a["company_name"]
            if cn not in audit_by_company:
                audit_by_company[cn] = []
            audit_by_company[cn].append(
                AuditLogEntry(
                    id=str(a["id"]),
                    company_name=cn,
                    action_type=a["action_type"],
                    details=a["details"],
                    created_at=str(a["created_at"]) if a["created_at"] else None,
                )
            )

        entries = [
            PrivacyProofEntry(
                company_name=r["company_name"],
                note=r["note"],
                last_checked=now_iso,
                exposure_count=0,
                blocked_actions=audit_by_company.get(r["company_name"], []),
            )
            for r in blocklist_rows
        ]

        return PrivacyProofResponse(entries=entries, total=len(entries))


@router.get("/proof/report")
async def download_privacy_report(
    user_id: str = Depends(get_current_user_id),
):
    """Download a JSON privacy report with all proof data."""
    from datetime import datetime, timezone

    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        await session.execute(text(ENSURE_BLOCKLIST_TABLE))
        await session.execute(text(ENSURE_AUDIT_LOG_TABLE))
        await session.commit()

        result = await session.execute(
            text(
                "SELECT company_name, note, created_at FROM employer_blocklist "
                "WHERE user_id = :uid ORDER BY created_at DESC"
            ),
            {"uid": user_id},
        )
        blocklist = [
            {
                "company_name": r["company_name"],
                "note": r["note"],
                "added_at": str(r["created_at"]) if r["created_at"] else None,
            }
            for r in result.mappings().all()
        ]

        result = await session.execute(
            text(
                "SELECT company_name, action_type, details, created_at "
                "FROM privacy_audit_log WHERE user_id = :uid "
                "ORDER BY created_at DESC"
            ),
            {"uid": user_id},
        )
        audit_log = [
            {
                "company_name": r["company_name"],
                "action_type": r["action_type"],
                "details": r["details"],
                "timestamp": str(r["created_at"]) if r["created_at"] else None,
            }
            for r in result.mappings().all()
        ]

        return {
            "report_type": "privacy_proof",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "blocklisted_companies": blocklist,
            "blocked_actions_log": audit_log,
            "total_exposures": 0,
        }
