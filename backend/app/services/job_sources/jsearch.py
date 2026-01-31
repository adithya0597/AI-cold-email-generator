"""
JSearch (RapidAPI) job source client.

API docs: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
Primary source for job listings.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from app.config import settings
from app.services.job_sources.base import BaseJobSource, RawJob

logger = logging.getLogger(__name__)

# JSearch API base URL
JSEARCH_BASE_URL = "https://jsearch.p.rapidapi.com/search"


class JSearchSource(BaseJobSource):
    """JSearch (RapidAPI) job board aggregator client."""

    source_name = "jsearch"

    def __init__(self, api_key: str | None = None, timeout: float = 30.0):
        self._api_key = api_key or settings.RAPIDAPI_KEY
        self._timeout = timeout

    async def search(
        self,
        query: str,
        location: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[RawJob]:
        """Search JSearch API for matching jobs.

        Returns empty list on any failure (network, auth, parse).
        """
        if not self._api_key:
            logger.warning("JSearch API key not configured, skipping")
            return []

        filters = filters or {}

        params: dict[str, Any] = {
            "query": query,
            "date_posted": "week",
            "num_pages": "1",
        }

        if location:
            params["query"] = f"{query} in {location}"

        # Map employment type filter
        emp_type = filters.get("employment_type")
        if emp_type:
            params["employment_types"] = emp_type

        headers = {
            "X-RapidAPI-Key": self._api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    JSEARCH_BASE_URL, params=params, headers=headers
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "JSearch API HTTP error: %s %s", exc.response.status_code, exc
            )
            return []
        except Exception as exc:
            logger.error("JSearch API request failed: %s", exc)
            return []

        return self._parse_response(data)

    def _parse_response(self, data: dict[str, Any]) -> list[RawJob]:
        """Parse JSearch API response into RawJob instances."""
        jobs: list[RawJob] = []
        results = data.get("data", [])

        for item in results:
            try:
                # Parse salary
                salary_min = None
                salary_max = None
                if item.get("job_min_salary"):
                    salary_min = int(item["job_min_salary"])
                if item.get("job_max_salary"):
                    salary_max = int(item["job_max_salary"])

                # Parse remote status
                remote = item.get("job_is_remote", False)

                # Parse posted date
                posted_at = None
                posted_str = item.get("job_posted_at_datetime_utc")
                if posted_str:
                    try:
                        posted_at = datetime.fromisoformat(
                            posted_str.replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError):
                        pass

                # Build location string
                city = item.get("job_city", "")
                state = item.get("job_state", "")
                country = item.get("job_country", "")
                location_parts = [p for p in [city, state, country] if p]
                location = ", ".join(location_parts) if location_parts else None

                job = RawJob(
                    title=item.get("job_title", "Unknown"),
                    company=item.get("employer_name", "Unknown"),
                    url=item.get("job_apply_link") or item.get("job_google_link"),
                    location=location,
                    description=item.get("job_description"),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    employment_type=item.get("job_employment_type"),
                    remote=bool(remote),
                    source="jsearch",
                    source_id=item.get("job_id"),
                    posted_at=posted_at,
                    raw_data=item,
                )
                jobs.append(job)
            except Exception as exc:
                logger.warning("Failed to parse JSearch job item: %s", exc)
                continue

        logger.info("JSearch returned %d jobs", len(jobs))
        return jobs
