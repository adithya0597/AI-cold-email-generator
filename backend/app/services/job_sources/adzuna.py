"""
Adzuna job source client.

API docs: https://developer.adzuna.com/overview
Secondary source for job listings.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from app.config import settings
from app.services.job_sources.base import BaseJobSource, RawJob

logger = logging.getLogger(__name__)

# Adzuna API base URL (US jobs)
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs/us/search/1"


class AdzunaSource(BaseJobSource):
    """Adzuna job board API client."""

    source_name = "adzuna"

    def __init__(
        self,
        app_id: str | None = None,
        app_key: str | None = None,
        timeout: float = 30.0,
    ):
        self._app_id = app_id or settings.ADZUNA_APP_ID
        self._app_key = app_key or settings.ADZUNA_APP_KEY
        self._timeout = timeout

    async def search(
        self,
        query: str,
        location: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[RawJob]:
        """Search Adzuna API for matching jobs.

        Returns empty list on any failure (network, auth, parse).
        """
        if not self._app_id or not self._app_key:
            logger.warning("Adzuna API credentials not configured, skipping")
            return []

        filters = filters or {}

        params: dict[str, Any] = {
            "app_id": self._app_id,
            "app_key": self._app_key,
            "what": query,
            "results_per_page": 50,
            "content-type": "application/json",
        }

        if location:
            params["where"] = location

        salary_min = filters.get("salary_min")
        if salary_min:
            params["salary_min"] = salary_min

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(ADZUNA_BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Adzuna API HTTP error: %s %s", exc.response.status_code, exc
            )
            return []
        except Exception as exc:
            logger.error("Adzuna API request failed: %s", exc)
            return []

        return self._parse_response(data)

    def _parse_response(self, data: dict[str, Any]) -> list[RawJob]:
        """Parse Adzuna API response into RawJob instances."""
        jobs: list[RawJob] = []
        results = data.get("results", [])

        for item in results:
            try:
                # Parse salary
                salary_min = None
                salary_max = None
                if item.get("salary_min"):
                    salary_min = int(item["salary_min"])
                if item.get("salary_max"):
                    salary_max = int(item["salary_max"])

                # Parse location
                location_data = item.get("location", {})
                display_name = location_data.get("display_name")

                # Parse posted date
                posted_at = None
                created_str = item.get("created")
                if created_str:
                    try:
                        posted_at = datetime.fromisoformat(
                            created_str.replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError):
                        pass

                job = RawJob(
                    title=item.get("title", "Unknown"),
                    company=item.get("company", {}).get("display_name", "Unknown"),
                    url=item.get("redirect_url"),
                    location=display_name,
                    description=item.get("description"),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    employment_type=item.get("contract_type"),
                    remote=False,  # Adzuna doesn't have explicit remote flag
                    source="adzuna",
                    source_id=str(item.get("id", "")),
                    posted_at=posted_at,
                    raw_data=item,
                )
                jobs.append(job)
            except Exception as exc:
                logger.warning("Failed to parse Adzuna job item: %s", exc)
                continue

        logger.info("Adzuna returned %d jobs", len(jobs))
        return jobs
