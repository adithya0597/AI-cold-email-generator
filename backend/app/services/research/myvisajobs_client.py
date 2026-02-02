"""MyVisaJobs-equivalent data extractor using DOL LCA disclosure files.

Extracts wage data, commonly sponsored job titles, and worksite locations
per company — the same fields that MyVisaJobs specializes in.
Reuses DOLDisclosureClient from dol_client.py for file download/caching.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.services.research.dol_client import DOLDisclosureClient, _parse_wage
from app.services.research.h1b_service import normalize_company_name

logger = logging.getLogger(__name__)


@dataclass
class CompanyDetails:
    """Detailed company data from DOL LCA filings."""

    avg_wage: Optional[float] = None
    total_records: int = 0
    top_job_titles: List[Tuple[str, int]] = field(default_factory=list)
    worksite_locations: Dict[str, int] = field(default_factory=dict)


def get_top_job_titles(records: List[Dict[str, str]], limit: int = 5) -> List[Tuple[str, int]]:
    """Return top job titles by count from LCA records."""
    counter: Counter = Counter()
    for row in records:
        title = (row.get("SOC_TITLE") or "").strip()
        if title:
            counter[title] += 1
    return counter.most_common(limit)


def get_worksite_locations(records: List[Dict[str, str]]) -> Dict[str, int]:
    """Return worksite state → petition count mapping."""
    counter: Counter = Counter()
    for row in records:
        state = (row.get("WORKSITE_STATE") or "").strip()
        if state:
            counter[state] += 1
    return dict(counter)


def extract_company_details(records: List[Dict[str, str]], company_key: str) -> CompanyDetails:
    """Extract wage, job title, and location data for a specific company.

    Filters records by normalized company name match.
    """
    company_records = [
        r for r in records
        if normalize_company_name(r.get("EMPLOYER_NAME", "")) == company_key
    ]

    if not company_records:
        return CompanyDetails()

    # Wages
    wages = []
    for row in company_records:
        wage = _parse_wage(
            row.get("WAGE_RATE_OF_PAY_FROM", ""),
            row.get("WAGE_UNIT_OF_PAY", ""),
        )
        if wage is not None:
            wages.append(wage)

    return CompanyDetails(
        avg_wage=sum(wages) / len(wages) if wages else None,
        total_records=len(company_records),
        top_job_titles=get_top_job_titles(company_records),
        worksite_locations=get_worksite_locations(company_records),
    )


class MyVisaJobsClient:
    """Client for extracting MyVisaJobs-equivalent data from DOL LCA files."""

    def __init__(self):
        self._dol_client = DOLDisclosureClient()

    async def fetch_company_details(self, company_name: str, fiscal_year: int = 2024) -> Optional[CompanyDetails]:
        """Fetch detailed company data from DOL LCA files."""
        from app.services.research.dol_client import parse_disclosure_csv

        path = await self._dol_client.download_disclosure_file(fiscal_year)
        records = parse_disclosure_csv(path)

        company_key = normalize_company_name(company_name)
        details = extract_company_details(records, company_key)

        if details.total_records == 0:
            return None
        return details
