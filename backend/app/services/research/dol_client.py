"""DOL H1B public disclosure data client.

Downloads and parses DOL H1B disclosure CSV files — the same underlying
public data that H1BGrader uses. Provides per-company aggregation of
petition counts, approval rates, wage data, and historical trends.
"""

from __future__ import annotations

import asyncio
import csv
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import httpx

from app.services.research.h1b_service import normalize_company_name

logger = logging.getLogger(__name__)

# DOL disclosure CSV base URL pattern (fiscal year files)
_DOL_BASE_URL = "https://www.dol.gov/sites/dolgov/files/ETA/oflc/pdfs/LCA_Disclosure_Data_FY{year}.csv"

# Required columns in the DOL CSV
_REQUIRED_COLUMNS = {"EMPLOYER_NAME", "CASE_STATUS"}

# Hours per work year for hourly-to-annual conversion
_HOURS_PER_YEAR = 2080


@dataclass
class CompanyStats:
    """Aggregated stats for a single company from DOL data."""

    company_name: str
    total_petitions: int = 0
    approved_count: int = 0
    denied_count: int = 0
    withdrawn_count: int = 0
    approval_rate: float = 0.0
    avg_wage: Optional[float] = None
    trend: str = "stable"
    _wages: list = field(default_factory=list, repr=False)


def parse_disclosure_csv(path: Path) -> List[Dict[str, str]]:
    """Parse a DOL H1B disclosure CSV file.

    Skips rows missing EMPLOYER_NAME. Returns list of row dicts.
    """
    rows: List[Dict[str, str]] = []

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip rows with empty employer name
            if not row.get("EMPLOYER_NAME", "").strip():
                continue
            rows.append(row)

    return rows


def _parse_wage(wage_str: str, unit: str) -> Optional[float]:
    """Parse a wage string, handling commas and hourly/annual conversion."""
    if not wage_str:
        return None
    try:
        wage = float(wage_str.replace(",", "").strip())
        if unit and unit.strip().lower() == "hour":
            wage = wage * _HOURS_PER_YEAR
        return wage
    except (ValueError, TypeError):
        return None


def aggregate_by_company(records: List[Dict[str, str]]) -> Dict[str, CompanyStats]:
    """Group DOL records by normalized company name and compute stats."""
    companies: Dict[str, CompanyStats] = {}

    for row in records:
        employer = row.get("EMPLOYER_NAME", "").strip()
        if not employer:
            continue

        key = normalize_company_name(employer)
        if key not in companies:
            companies[key] = CompanyStats(company_name=employer)

        stats = companies[key]
        stats.total_petitions += 1

        status = (row.get("CASE_STATUS") or "").strip().lower()
        if status == "certified":
            stats.approved_count += 1
        elif status == "denied":
            stats.denied_count += 1
        elif status == "withdrawn":
            stats.withdrawn_count += 1

        wage = _parse_wage(
            row.get("WAGE_RATE_OF_PAY_FROM", ""),
            row.get("WAGE_UNIT_OF_PAY", ""),
        )
        if wage is not None:
            stats._wages.append(wage)

    # Compute derived fields
    for stats in companies.values():
        if stats.total_petitions > 0:
            stats.approval_rate = stats.approved_count / stats.total_petitions
        if stats._wages:
            stats.avg_wage = sum(stats._wages) / len(stats._wages)

    return companies


def calculate_trend(current: int, previous: int) -> str:
    """Calculate trend based on year-over-year change.

    Returns 'increasing', 'decreasing', or 'stable' (±10% threshold).
    """
    if previous == 0:
        return "increasing" if current > 0 else "stable"

    change = (current - previous) / previous
    if change > 0.10:
        return "increasing"
    elif change < -0.10:
        return "decreasing"
    return "stable"


class DOLDisclosureClient:
    """Client for downloading and parsing DOL H1B disclosure data."""

    def __init__(self, cache_dir: Optional[Path] = None):
        import tempfile

        self._cache_dir = cache_dir or Path(tempfile.gettempdir()) / "jobpilot_dol_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._max_retries = 3
        self._backoff_base = 1  # seconds

    def _cache_path(self, fiscal_year: int) -> Path:
        return self._cache_dir / f"h1b_disclosure_{fiscal_year}.csv"

    def _is_cache_fresh(self, path: Path, max_age_hours: int = 24) -> bool:
        """Check if cached file is less than max_age_hours old."""
        if not path.exists():
            return False
        age = time.time() - path.stat().st_mtime
        return age < max_age_hours * 3600

    async def download_disclosure_file(self, fiscal_year: int) -> Path:
        """Download DOL disclosure CSV for a fiscal year.

        Caches locally; skips download if cache is < 24h old.
        Retries with exponential backoff on transient failures.
        """
        cached = self._cache_path(fiscal_year)
        if self._is_cache_fresh(cached):
            logger.info("Using cached DOL disclosure file: %s", cached)
            return cached

        url = _DOL_BASE_URL.format(year=fiscal_year)
        last_error: Optional[Exception] = None

        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    async with client.stream("GET", url) as response:
                        if response.status_code != 200:
                            raise httpx.HTTPStatusError(
                                f"HTTP {response.status_code}",
                                request=response.request,
                                response=response,
                            )
                        with open(cached, "wb") as f:
                            async for chunk in response.aiter_bytes():
                                f.write(chunk)

                logger.info("Downloaded DOL disclosure file: %s", cached)
                return cached

            except Exception as exc:
                last_error = exc
                if attempt < self._max_retries - 1:
                    delay = self._backoff_base * (2 ** attempt)
                    logger.warning(
                        "DOL download attempt %d failed: %s. Retrying in %ds...",
                        attempt + 1,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)

        raise last_error or RuntimeError("DOL download failed after retries")

    async def fetch_company_stats(self, company_name: str, fiscal_year: int = 2024) -> Optional[CompanyStats]:
        """Fetch stats for a specific company from DOL data."""
        path = await self.download_disclosure_file(fiscal_year)
        records = parse_disclosure_csv(path)
        companies = aggregate_by_company(records)

        normalized = normalize_company_name(company_name)
        return companies.get(normalized)
