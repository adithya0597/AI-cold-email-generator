"""H1B sponsor data aggregation service.

Provides company name normalization, multi-source data fetching (stubs for
now — real integrations in Stories 7-2, 7-3, 7-4), aggregation/dedup, and
database upsert for the canonical h1b_sponsors table.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Table DDL — created once per process via _ensure_tables()
# ---------------------------------------------------------------------------

_tables_ensured = False

_DDL_H1B_SPONSORS = text("""
    CREATE TABLE IF NOT EXISTS h1b_sponsors (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        company_name TEXT NOT NULL,
        company_name_normalized TEXT NOT NULL,
        domain TEXT,
        total_petitions INTEGER DEFAULT 0,
        approval_rate REAL,
        avg_wage REAL,
        wage_source TEXT,
        last_updated_h1bgrader TIMESTAMPTZ,
        last_updated_myvisajobs TIMESTAMPTZ,
        last_updated_uscis TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(company_name_normalized)
    )
""")

_DDL_H1B_SOURCE_RECORDS = text("""
    CREATE TABLE IF NOT EXISTS h1b_source_records (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        sponsor_id UUID REFERENCES h1b_sponsors(id) ON DELETE CASCADE,
        source TEXT NOT NULL CHECK (source IN ('h1bgrader', 'myvisajobs', 'uscis')),
        raw_data JSONB NOT NULL DEFAULT '{}',
        fetched_at TIMESTAMPTZ DEFAULT NOW(),
        schema_version INTEGER DEFAULT 1
    )
""")

_DDL_INDEXES = [
    text("CREATE INDEX IF NOT EXISTS idx_h1b_sponsors_name_normalized ON h1b_sponsors(company_name_normalized)"),
    text("CREATE INDEX IF NOT EXISTS idx_h1b_sponsors_domain ON h1b_sponsors(domain)"),
    text("CREATE INDEX IF NOT EXISTS idx_h1b_source_records_sponsor_id ON h1b_source_records(sponsor_id)"),
]


async def _ensure_tables(session) -> None:
    """Create H1B tables if they don't exist (once per process)."""
    global _tables_ensured
    if _tables_ensured:
        return
    await session.execute(_DDL_H1B_SPONSORS)
    await session.execute(_DDL_H1B_SOURCE_RECORDS)
    for idx in _DDL_INDEXES:
        await session.execute(idx)
    await session.commit()
    _tables_ensured = True


# ---------------------------------------------------------------------------
# Company name normalization
# ---------------------------------------------------------------------------

_SUFFIX_PATTERN = re.compile(
    r",?\s*\b(inc\.?|llc\.?|corp\.?|corporation|ltd\.?|l\.?p\.?|llp\.?|co\.?|company)\b\.?",
    re.IGNORECASE,
)


def normalize_company_name(name: str) -> str:
    """Normalize a company name for deduplication.

    Strips common legal suffixes, collapses whitespace, lowercases.
    """
    result = _SUFFIX_PATTERN.sub("", name)
    result = re.sub(r"\s+", " ", result).strip().lower()
    return result


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class SourceData:
    """Data from a single H1B source."""
    source: str  # h1bgrader | myvisajobs | uscis
    company_name: str
    total_petitions: Optional[int] = None
    approval_rate: Optional[float] = None
    avg_wage: Optional[float] = None
    wage_source: Optional[str] = None
    domain: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: Optional[datetime] = None


@dataclass
class SponsorRecord:
    """Aggregated sponsor record from multiple sources."""
    company_name: str
    company_name_normalized: str
    domain: Optional[str] = None
    total_petitions: int = 0
    approval_rate: Optional[float] = None
    avg_wage: Optional[float] = None
    wage_source: Optional[str] = None
    last_updated_h1bgrader: Optional[datetime] = None
    last_updated_myvisajobs: Optional[datetime] = None
    last_updated_uscis: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Source fetchers (stubs — real integrations in Stories 7-2, 7-3, 7-4)
# ---------------------------------------------------------------------------


async def fetch_h1bgrader(company_name: str) -> Optional[SourceData]:
    """Fetch H1B data from DOL public disclosure files.

    Uses the same underlying public data that H1BGrader uses (DOL/USCIS
    disclosure files). Returns None on failure so the pipeline continues.
    """
    from app.services.research.dol_client import DOLDisclosureClient

    try:
        client = DOLDisclosureClient()
        stats = await client.fetch_company_stats(company_name)
        if stats is None:
            logger.info("No DOL data found for %s", company_name)
            return None

        return SourceData(
            source="h1bgrader",
            company_name=company_name,
            total_petitions=stats.total_petitions,
            approval_rate=stats.approval_rate,
            avg_wage=stats.avg_wage,
            raw_data={
                "attribution": "Source: DOL H1B Disclosure Data (H1BGrader equivalent)",
                "source_url": "https://www.dol.gov/agencies/eta/foreign-labor/performance",
                "trend": stats.trend,
                "approved_count": stats.approved_count,
                "denied_count": stats.denied_count,
                "withdrawn_count": stats.withdrawn_count,
            },
            fetched_at=datetime.now(timezone.utc),
        )
    except Exception as exc:
        logger.error(
            "fetch_h1bgrader (DOL) failed for %s: %s",
            company_name,
            exc,
            exc_info=True,
            extra={"source": "h1bgrader", "company": company_name},
        )
        return None


async def fetch_myvisajobs(company_name: str) -> Optional[SourceData]:
    """Fetch LCA wage/job title data from DOL disclosure files.

    Uses the same underlying public data that MyVisaJobs uses. Extracts
    average wages, top job titles, and worksite locations.
    Returns None on failure so the pipeline continues.
    """
    from app.services.research.myvisajobs_client import MyVisaJobsClient

    try:
        client = MyVisaJobsClient()
        details = await client.fetch_company_details(company_name)
        if details is None:
            logger.info("No MyVisaJobs-equivalent data found for %s", company_name)
            return None

        normalized = normalize_company_name(company_name)
        return SourceData(
            source="myvisajobs",
            company_name=company_name,
            avg_wage=details.avg_wage,
            wage_source="dol_lca",
            domain=f"{normalized.replace(' ', '')}.com",
            raw_data={
                "attribution": "Source: DOL LCA Data (MyVisaJobs equivalent)",
                "source_url": "https://www.dol.gov/agencies/eta/foreign-labor/performance",
                "top_job_titles": details.top_job_titles,
                "worksite_locations": details.worksite_locations,
                "total_lca_records": details.total_records,
            },
            fetched_at=datetime.now(timezone.utc),
        )
    except Exception as exc:
        logger.error(
            "fetch_myvisajobs (DOL LCA) failed for %s: %s",
            company_name,
            exc,
            exc_info=True,
            extra={"source": "myvisajobs", "company": company_name},
        )
        return None


async def fetch_uscis(company_name: str) -> Optional[SourceData]:
    """Fetch H1B data from USCIS public LCA data. Stub returning mock data."""
    logger.info("fetch_uscis stub called for %s", company_name)
    return SourceData(
        source="uscis",
        company_name=company_name,
        total_petitions=200,
        approval_rate=0.88,
        avg_wage=130000.0,
        wage_source="uscis_lca",
        raw_data={"stub": True, "source": "uscis"},
        fetched_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def aggregate_sources(
    h1bgrader_data: Optional[SourceData],
    myvisajobs_data: Optional[SourceData],
    uscis_data: Optional[SourceData],
) -> SponsorRecord:
    """Merge data from multiple sources into a single SponsorRecord.

    Priority: USCIS for wage data (most authoritative), H1BGrader for
    petition counts and approval rates, MyVisaJobs for supplemental info.
    """
    # Use the first available company name
    company_name = "Unknown"
    for src in [h1bgrader_data, myvisajobs_data, uscis_data]:
        if src and src.company_name:
            company_name = src.company_name
            break

    record = SponsorRecord(
        company_name=company_name,
        company_name_normalized=normalize_company_name(company_name),
    )

    # Petitions: sum unique sources or take max
    petitions = []
    if h1bgrader_data and h1bgrader_data.total_petitions is not None:
        petitions.append(h1bgrader_data.total_petitions)
    if uscis_data and uscis_data.total_petitions is not None:
        petitions.append(uscis_data.total_petitions)
    record.total_petitions = max(petitions) if petitions else 0

    # Approval rate: prefer USCIS, then H1BGrader
    if uscis_data and uscis_data.approval_rate is not None:
        record.approval_rate = uscis_data.approval_rate
    elif h1bgrader_data and h1bgrader_data.approval_rate is not None:
        record.approval_rate = h1bgrader_data.approval_rate

    # Wage: prefer USCIS (most authoritative), then MyVisaJobs
    if uscis_data and uscis_data.avg_wage is not None:
        record.avg_wage = uscis_data.avg_wage
        record.wage_source = uscis_data.wage_source or "uscis"
    elif myvisajobs_data and myvisajobs_data.avg_wage is not None:
        record.avg_wage = myvisajobs_data.avg_wage
        record.wage_source = myvisajobs_data.wage_source or "myvisajobs"

    # Domain: prefer MyVisaJobs
    if myvisajobs_data and myvisajobs_data.domain:
        record.domain = myvisajobs_data.domain

    # Freshness timestamps
    if h1bgrader_data and h1bgrader_data.fetched_at:
        record.last_updated_h1bgrader = h1bgrader_data.fetched_at
    if myvisajobs_data and myvisajobs_data.fetched_at:
        record.last_updated_myvisajobs = myvisajobs_data.fetched_at
    if uscis_data and uscis_data.fetched_at:
        record.last_updated_uscis = uscis_data.fetched_at

    return record


# ---------------------------------------------------------------------------
# Database upsert
# ---------------------------------------------------------------------------


async def upsert_sponsor(session, sponsor: SponsorRecord) -> None:
    """Insert or update a canonical sponsor record."""
    await session.execute(
        text("""
            INSERT INTO h1b_sponsors (
                company_name, company_name_normalized, domain,
                total_petitions, approval_rate, avg_wage, wage_source,
                last_updated_h1bgrader, last_updated_myvisajobs, last_updated_uscis,
                updated_at
            ) VALUES (
                :company_name, :company_name_normalized, :domain,
                :total_petitions, :approval_rate, :avg_wage, :wage_source,
                :last_updated_h1bgrader, :last_updated_myvisajobs, :last_updated_uscis,
                NOW()
            )
            ON CONFLICT (company_name_normalized) DO UPDATE SET
                total_petitions = EXCLUDED.total_petitions,
                approval_rate = EXCLUDED.approval_rate,
                avg_wage = EXCLUDED.avg_wage,
                wage_source = EXCLUDED.wage_source,
                domain = COALESCE(EXCLUDED.domain, h1b_sponsors.domain),
                last_updated_h1bgrader = COALESCE(EXCLUDED.last_updated_h1bgrader, h1b_sponsors.last_updated_h1bgrader),
                last_updated_myvisajobs = COALESCE(EXCLUDED.last_updated_myvisajobs, h1b_sponsors.last_updated_myvisajobs),
                last_updated_uscis = COALESCE(EXCLUDED.last_updated_uscis, h1b_sponsors.last_updated_uscis),
                updated_at = NOW()
        """),
        {
            "company_name": sponsor.company_name,
            "company_name_normalized": sponsor.company_name_normalized,
            "domain": sponsor.domain,
            "total_petitions": sponsor.total_petitions,
            "approval_rate": sponsor.approval_rate,
            "avg_wage": sponsor.avg_wage,
            "wage_source": sponsor.wage_source,
            "last_updated_h1bgrader": sponsor.last_updated_h1bgrader,
            "last_updated_myvisajobs": sponsor.last_updated_myvisajobs,
            "last_updated_uscis": sponsor.last_updated_uscis,
        },
    )
    await session.commit()


# ---------------------------------------------------------------------------
# Pipeline orchestration
# ---------------------------------------------------------------------------


async def run_h1b_pipeline(company_names: list[str] | None = None) -> Dict[str, Any]:
    """Run the full H1B data aggregation pipeline.

    If company_names is None, this is a stub — real batch fetching comes in
    Stories 7-2 through 7-4. For now, processes the given list.
    """
    from app.db.engine import AsyncSessionLocal

    if company_names is None:
        company_names = []

    results = {"processed": 0, "errors": []}

    async with AsyncSessionLocal() as session:
        await _ensure_tables(session)

        for company in company_names:
            try:
                h1b_data = await fetch_h1bgrader(company)
                mvj_data = await fetch_myvisajobs(company)
                uscis_data = await fetch_uscis(company)

                sponsor = aggregate_sources(h1b_data, mvj_data, uscis_data)
                await upsert_sponsor(session, sponsor)
                results["processed"] += 1
            except Exception as exc:
                logger.error(
                    "H1B pipeline error for %s: %s", company, exc, exc_info=True
                )
                results["errors"].append({"company": company, "error": str(exc)})

    if results["errors"]:
        logger.warning(
            "H1B pipeline completed with %d errors: %s",
            len(results["errors"]),
            results["errors"],
        )

    return results
