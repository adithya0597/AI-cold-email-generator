"""H1B sponsor data API endpoints.

Provides sponsor lookup and search for H1B-tier users.
Tier gating: only h1b_pro, career_insurance, and enterprise users.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from app.auth.clerk import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/h1b", tags=["h1b"])

ELIGIBLE_TIERS = {"h1b_pro", "career_insurance", "enterprise"}


async def _check_h1b_tier(session, user_id: str) -> str:
    """Check user tier and raise 403 if not eligible for H1B data."""
    result = await session.execute(
        text("SELECT tier FROM users WHERE clerk_id = :user_id"),
        {"user_id": user_id},
    )
    row = result.mappings().first()
    tier = row["tier"] if row else "free"

    if tier not in ELIGIBLE_TIERS:
        raise HTTPException(
            status_code=403,
            detail="H1B sponsor data requires H1B Pro, Career Insurance, or Enterprise tier.",
        )
    return tier


async def _ensure_h1b_tables(session) -> None:
    """Ensure H1B tables exist (delegates to service)."""
    from app.services.research.h1b_service import _ensure_tables

    await _ensure_tables(session)


@router.get("/sponsors/{company}")
async def get_sponsor(
    company: str,
    user_id: str = Depends(get_current_user_id),
):
    """Look up H1B sponsor data for a specific company."""
    from app.db.engine import AsyncSessionLocal
    from app.services.research.h1b_service import normalize_company_name

    async with AsyncSessionLocal() as session:
        await _ensure_h1b_tables(session)
        await _check_h1b_tier(session, user_id)

        normalized = normalize_company_name(company)
        result = await session.execute(
            text("""
                SELECT company_name, company_name_normalized, domain,
                       total_petitions, approval_rate, avg_wage, wage_source,
                       last_updated_h1bgrader, last_updated_myvisajobs,
                       last_updated_uscis, updated_at
                FROM h1b_sponsors
                WHERE company_name_normalized = :name
            """),
            {"name": normalized},
        )
        row = result.mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail=f"No H1B data found for '{company}'")

    return {
        "company_name": row["company_name"],
        "company_name_normalized": row["company_name_normalized"],
        "domain": row["domain"],
        "total_petitions": row["total_petitions"],
        "approval_rate": row["approval_rate"],
        "avg_wage": row["avg_wage"],
        "wage_source": row["wage_source"],
        "freshness": {
            "h1bgrader": str(row["last_updated_h1bgrader"]) if row["last_updated_h1bgrader"] else None,
            "myvisajobs": str(row["last_updated_myvisajobs"]) if row["last_updated_myvisajobs"] else None,
            "uscis": str(row["last_updated_uscis"]) if row["last_updated_uscis"] else None,
        },
        "last_updated": str(row["updated_at"]) if row["updated_at"] else None,
    }


@router.get("/sponsors")
async def search_sponsors(
    q: str = Query(..., min_length=2, description="Search query for company name"),
    limit: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
):
    """Search H1B sponsors by partial company name."""
    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        await _ensure_h1b_tables(session)
        await _check_h1b_tier(session, user_id)

        result = await session.execute(
            text("""
                SELECT company_name, company_name_normalized, domain,
                       total_petitions, approval_rate, avg_wage, wage_source
                FROM h1b_sponsors
                WHERE company_name_normalized ILIKE :query
                ORDER BY total_petitions DESC NULLS LAST
                LIMIT :limit
            """),
            {"query": f"%{q.lower()}%", "limit": limit},
        )
        rows = result.mappings().all()

    return {
        "total": len(rows),
        "sponsors": [
            {
                "company_name": r["company_name"],
                "company_name_normalized": r["company_name_normalized"],
                "domain": r["domain"],
                "total_petitions": r["total_petitions"],
                "approval_rate": r["approval_rate"],
                "avg_wage": r["avg_wage"],
                "wage_source": r["wage_source"],
            }
            for r in rows
        ],
    }
