"""USCIS H1B Employer Data Hub client.

Downloads and parses official USCIS H1B employer data — the most
authoritative source for approval/denial statistics. Data takes
priority over all other sources in aggregation.
"""

from __future__ import annotations

import asyncio
import csv
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import httpx

from app.services.research.h1b_service import normalize_company_name

logger = logging.getLogger(__name__)

# USCIS H1B Employer Data Hub URL pattern
_USCIS_BASE_URL = "https://www.uscis.gov/sites/default/files/document/data/h1b_datahubexport-{year}.csv"


@dataclass
class EmployerStats:
    """Aggregated USCIS employer statistics."""

    initial_approvals: int = 0
    initial_denials: int = 0
    continuing_approvals: int = 0
    continuing_denials: int = 0

    @property
    def total_petitions(self) -> int:
        return (
            self.initial_approvals
            + self.initial_denials
            + self.continuing_approvals
            + self.continuing_denials
        )

    @property
    def approval_rate(self) -> float:
        total = self.total_petitions
        if total == 0:
            return 0.0
        return (self.initial_approvals + self.continuing_approvals) / total


def parse_employer_data(path: Path) -> List[Dict[str, str]]:
    """Parse a USCIS H1B employer data CSV file.

    Skips rows missing Employer field. Returns list of row dicts.
    """
    rows: List[Dict[str, str]] = []

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("Employer", "").strip():
                continue
            rows.append(row)

    return rows


def _safe_int(value: str) -> int:
    """Parse an integer from a string, returning 0 on failure."""
    try:
        return int(value.replace(",", "").strip())
    except (ValueError, TypeError, AttributeError):
        return 0


def get_employer_stats(records: List[Dict[str, str]], company_name: str) -> Optional[EmployerStats]:
    """Extract aggregated stats for a specific employer.

    Matches by normalized company name. Sums across multiple entries
    (e.g., different fiscal years or name variations).
    """
    normalized = normalize_company_name(company_name)
    stats = EmployerStats()
    found = False

    for row in records:
        employer = row.get("Employer", "")
        if normalize_company_name(employer) == normalized:
            found = True
            stats.initial_approvals += _safe_int(row.get("Initial Approvals", "0"))
            stats.initial_denials += _safe_int(row.get("Initial Denials", "0"))
            stats.continuing_approvals += _safe_int(row.get("Continuing Approvals", "0"))
            stats.continuing_denials += _safe_int(row.get("Continuing Denials", "0"))

    return stats if found else None


class USCISClient:
    """Client for downloading and parsing USCIS H1B employer data."""

    def __init__(self, cache_dir: Optional[Path] = None):
        import tempfile

        self._cache_dir = cache_dir or Path(tempfile.gettempdir()) / "jobpilot_uscis_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._max_retries = 3
        self._backoff_base = 1

    def _cache_path(self, fiscal_year: int) -> Path:
        return self._cache_dir / f"uscis_h1b_employer_{fiscal_year}.csv"

    def _is_cache_fresh(self, path: Path, max_age_hours: int = 24) -> bool:
        if not path.exists():
            return False
        age = time.time() - path.stat().st_mtime
        return age < max_age_hours * 3600

    async def download_employer_data(self, fiscal_year: int) -> Path:
        """Download USCIS H1B employer data for a fiscal year.

        Caches locally; skips download if cache is < 24h old.
        """
        cached = self._cache_path(fiscal_year)
        if self._is_cache_fresh(cached):
            logger.info("Using cached USCIS employer data: %s", cached)
            return cached

        url = _USCIS_BASE_URL.format(year=fiscal_year)
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

                logger.info("Downloaded USCIS employer data: %s", cached)
                return cached

            except Exception as exc:
                last_error = exc
                if attempt < self._max_retries - 1:
                    delay = self._backoff_base * (2 ** attempt)
                    logger.warning(
                        "USCIS download attempt %d failed: %s. Retrying in %ds...",
                        attempt + 1,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)

        raise last_error or RuntimeError("USCIS download failed after retries")

    async def fetch_employer_stats(self, company_name: str, fiscal_year: int = 2024) -> Optional[EmployerStats]:
        """Fetch stats for a specific employer from USCIS data."""
        path = await self.download_employer_data(fiscal_year)
        records = parse_employer_data(path)
        return get_employer_stats(records, company_name)
