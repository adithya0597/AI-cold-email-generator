"""
Privacy API endpoints — Stealth Mode management.

Stealth Mode hides the user's job search from their current employer
by preventing public visibility of profile and agent actions.
Requires Career Insurance or Enterprise tier.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.clerk import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/privacy", tags=["privacy"])

ELIGIBLE_TIERS = {"career_insurance", "enterprise"}

# ---------------------------------------------------------------------------
# Table DDL — executed once per process via _ensure_tables()
# ---------------------------------------------------------------------------

_tables_ensured = False

ENSURE_STEALTH_TABLE = (
    "CREATE TABLE IF NOT EXISTS stealth_settings ("
    "  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
    "  user_id TEXT NOT NULL UNIQUE,"
    "  stealth_enabled BOOLEAN NOT NULL DEFAULT FALSE,"
    "  enabled_at TIMESTAMPTZ,"
    "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
    ")"
)

ENSURE_BLOCKLIST_TABLE = (
    "CREATE TABLE IF NOT EXISTS employer_blocklist ("
    "  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
    "  user_id TEXT NOT NULL,"
    "  company_name TEXT NOT NULL,"
    "  note TEXT,"
    "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
    "  UNIQUE(user_id, company_name)"
    ")"
)

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

ENSURE_PASSIVE_TABLE = (
    "CREATE TABLE IF NOT EXISTS passive_mode_settings ("
    "  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
    "  user_id TEXT NOT NULL UNIQUE,"
    "  search_frequency TEXT NOT NULL DEFAULT 'weekly',"
    "  min_match_score INTEGER NOT NULL DEFAULT 70,"
    "  notification_pref TEXT NOT NULL DEFAULT 'weekly_digest',"
    "  auto_save_threshold INTEGER NOT NULL DEFAULT 85,"
    "  mode TEXT NOT NULL DEFAULT 'passive',"
    "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
    "  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
    ")"
)


async def _ensure_tables(session) -> None:
    """Create all privacy-related tables if they don't exist. Runs once per process."""
    global _tables_ensured
    if _tables_ensured:
        return
    from sqlalchemy import text

    await session.execute(text(ENSURE_STEALTH_TABLE))
    await session.execute(text(ENSURE_BLOCKLIST_TABLE))
    await session.execute(text(ENSURE_AUDIT_LOG_TABLE))
    await session.execute(text(ENSURE_PASSIVE_TABLE))
    await session.commit()
    _tables_ensured = True


# ---------------------------------------------------------------------------
# Stealth Mode
# ---------------------------------------------------------------------------


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
        await _ensure_tables(session)

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
        await _ensure_tables(session)

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

        # Upsert stealth setting — use CASE to avoid string concatenation
        await session.execute(
            text(
                "INSERT INTO stealth_settings (user_id, stealth_enabled, enabled_at) "
                "VALUES (:uid, :enabled, CASE WHEN :enabled THEN NOW() ELSE NULL END) "
                "ON CONFLICT (user_id) DO UPDATE SET "
                "stealth_enabled = :enabled, "
                "enabled_at = CASE WHEN :enabled THEN NOW() ELSE NULL END"
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
        await _ensure_tables(session)

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
        await _ensure_tables(session)

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
    """Remove a company from the employer blocklist. Requires active Stealth Mode."""
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        await _ensure_tables(session)

        if not await _check_stealth_enabled(session, user_id):
            raise HTTPException(
                status_code=403,
                detail="Stealth Mode must be enabled to manage the blocklist.",
            )

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
        await _ensure_tables(session)

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
        await _ensure_tables(session)

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
            "blocklisted_companies": blocklist,
            "blocked_actions_log": audit_log,
            "total_exposures": 0,
        }


# ============================================================
# Passive Mode Settings
# ============================================================

VALID_FREQUENCIES = {"daily", "weekly"}
VALID_NOTIFICATION_PREFS = {"weekly_digest", "immediate"}


class PassiveModeResponse(BaseModel):
    search_frequency: str = "weekly"
    min_match_score: int = 70
    notification_pref: str = "weekly_digest"
    auto_save_threshold: int = 85
    mode: str = "passive"
    eligible: bool = False
    tier: Optional[str] = None


class UpdatePassiveModeRequest(BaseModel):
    search_frequency: Optional[Literal["daily", "weekly"]] = None
    min_match_score: Optional[int] = Field(None, ge=10, le=100)
    notification_pref: Optional[Literal["weekly_digest", "immediate"]] = None
    auto_save_threshold: Optional[int] = Field(None, ge=30, le=99)


@router.get("/passive-mode", response_model=PassiveModeResponse)
async def get_passive_mode(
    user_id: str = Depends(get_current_user_id),
):
    """Return current passive mode settings and tier eligibility."""
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        await _ensure_tables(session)

        # Get tier
        result = await session.execute(
            text("SELECT tier FROM users WHERE clerk_id = :uid"),
            {"uid": user_id},
        )
        row = result.mappings().first()
        tier = str(row["tier"]) if row else None
        eligible = tier in ELIGIBLE_TIERS

        # Get settings
        result = await session.execute(
            text(
                "SELECT search_frequency, min_match_score, notification_pref, "
                "auto_save_threshold, mode FROM passive_mode_settings "
                "WHERE user_id = :uid"
            ),
            {"uid": user_id},
        )
        settings_row = result.mappings().first()

        if settings_row:
            return PassiveModeResponse(
                search_frequency=settings_row["search_frequency"],
                min_match_score=settings_row["min_match_score"],
                notification_pref=settings_row["notification_pref"],
                auto_save_threshold=settings_row["auto_save_threshold"],
                mode=settings_row["mode"],
                eligible=eligible,
                tier=tier,
            )

        return PassiveModeResponse(eligible=eligible, tier=tier)


@router.put("/passive-mode", response_model=PassiveModeResponse)
async def update_passive_mode(
    body: UpdatePassiveModeRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Update passive mode settings. Requires Career Insurance or Enterprise tier."""
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        await _ensure_tables(session)

        # Check tier
        result = await session.execute(
            text("SELECT tier FROM users WHERE clerk_id = :uid"),
            {"uid": user_id},
        )
        row = result.mappings().first()
        tier = str(row["tier"]) if row else None

        if tier not in ELIGIBLE_TIERS:
            raise HTTPException(
                status_code=403,
                detail="Passive Mode requires Career Insurance or Enterprise tier.",
            )

        # Build SET clause from provided fields
        updates = {}
        if body.search_frequency is not None:
            updates["search_frequency"] = body.search_frequency
        if body.min_match_score is not None:
            updates["min_match_score"] = body.min_match_score
        if body.notification_pref is not None:
            updates["notification_pref"] = body.notification_pref
        if body.auto_save_threshold is not None:
            updates["auto_save_threshold"] = body.auto_save_threshold

        freq = updates.get("search_frequency", "weekly")
        score = updates.get("min_match_score", 70)
        notif = updates.get("notification_pref", "weekly_digest")
        auto_save = updates.get("auto_save_threshold", 85)

        await session.execute(
            text(
                "INSERT INTO passive_mode_settings "
                "(user_id, search_frequency, min_match_score, notification_pref, auto_save_threshold) "
                "VALUES (:uid, :freq, :score, :notif, :auto_save) "
                "ON CONFLICT (user_id) DO UPDATE SET "
                "search_frequency = :freq, min_match_score = :score, "
                "notification_pref = :notif, auto_save_threshold = :auto_save, "
                "updated_at = NOW()"
            ),
            {"uid": user_id, "freq": freq, "score": score, "notif": notif, "auto_save": auto_save},
        )
        await session.commit()

        return PassiveModeResponse(
            search_frequency=freq,
            min_match_score=score,
            notification_pref=notif,
            auto_save_threshold=auto_save,
            mode="passive",
            eligible=True,
            tier=tier,
        )


@router.post("/passive-mode/sprint", response_model=PassiveModeResponse)
async def activate_sprint_mode(
    user_id: str = Depends(get_current_user_id),
):
    """Switch to Sprint mode — daily frequency, lower thresholds, immediate notifications."""
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        await _ensure_tables(session)

        # Check tier
        result = await session.execute(
            text("SELECT tier FROM users WHERE clerk_id = :uid"),
            {"uid": user_id},
        )
        row = result.mappings().first()
        tier = str(row["tier"]) if row else None

        if tier not in ELIGIBLE_TIERS:
            raise HTTPException(
                status_code=403,
                detail="Sprint Mode requires Career Insurance or Enterprise tier.",
            )

        await session.execute(
            text(
                "INSERT INTO passive_mode_settings "
                "(user_id, search_frequency, min_match_score, notification_pref, "
                "auto_save_threshold, mode) "
                "VALUES (:uid, 'daily', 50, 'immediate', 70, 'sprint') "
                "ON CONFLICT (user_id) DO UPDATE SET "
                "search_frequency = 'daily', min_match_score = 50, "
                "notification_pref = 'immediate', auto_save_threshold = 70, "
                "mode = 'sprint', updated_at = NOW()"
            ),
            {"uid": user_id},
        )
        await session.commit()

        return PassiveModeResponse(
            search_frequency="daily",
            min_match_score=50,
            notification_pref="immediate",
            auto_save_threshold=70,
            mode="sprint",
            eligible=True,
            tier=tier,
        )
