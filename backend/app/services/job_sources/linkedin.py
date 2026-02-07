"""
LinkedIn job source client via RapidAPI scraper endpoint.

LinkedIn does NOT have a free public job search API. This client uses a
RapidAPI-hosted LinkedIn job scraper service configured via LINKEDIN_RAPIDAPI_HOST.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from app.config import settings
from app.services.job_sources.base import BaseJobSource, RawJob

logger = logging.getLogger(__name__)


class LinkedInSource(BaseJobSource):
    """LinkedIn job board client via RapidAPI scraper."""

    source_name = "linkedin"

    def __init__(
        self,
        api_key: str | None = None,
        host: str | None = None,
        timeout: float = 30.0,
        request_delay: float = 2.0,
        client: httpx.AsyncClient | None = None,
    ):
        self._api_key = api_key or settings.RAPIDAPI_KEY
        self._host = host or settings.LINKEDIN_RAPIDAPI_HOST
        self._timeout = timeout
        self._request_delay = request_delay  # Reserved for future pagination support
        self._client = client

    async def search(
        self,
        query: str,
        location: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[RawJob]:
        """Search LinkedIn via RapidAPI scraper for matching jobs.

        Returns empty list on any failure (network, auth, parse).
        """
        if not self._api_key or not self._host:
            logger.warning("LinkedIn API credentials not configured, skipping")
            return []

        filters = filters or {}

        params: dict[str, Any] = {
            "keywords": query,
            "page": "1",
            "sort": "mostRelevant",
        }

        if location:
            params["location"] = location

        salary_min = filters.get("salary_min")
        if salary_min is not None:
            params["salary_min"] = salary_min

        headers = {
            "X-RapidAPI-Key": self._api_key,
            "X-RapidAPI-Host": self._host,
        }

        url = f"https://{self._host}/search"

        try:
            client = self._client or httpx.AsyncClient(timeout=self._timeout)
            try:
                resp = await client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            finally:
                if not self._client:
                    await client.aclose()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "LinkedIn API HTTP error: %s %s", exc.response.status_code, exc
            )
            return []
        except Exception as exc:
            logger.error("LinkedIn API request failed: %s", exc)
            return []

        return self._parse_response(data)

    def _parse_response(self, data: dict[str, Any]) -> list[RawJob]:
        """Parse LinkedIn API response into RawJob instances.

        Handles multiple response formats defensively — different RapidAPI
        LinkedIn providers may use different field names.
        """
        jobs: list[RawJob] = []
        results = data.get("data") or data.get("results") or data.get("jobs") or []

        for item in results:
            try:
                # Parse salary — use `is not None` to handle salary=0 correctly
                salary_min = None
                salary_max = None
                salary = item.get("salary")
                if isinstance(salary, dict):
                    if salary.get("min") is not None:
                        salary_min = int(salary["min"])
                    if salary.get("max") is not None:
                        salary_max = int(salary["max"])
                else:
                    if item.get("salary_min") is not None:
                        salary_min = int(item["salary_min"])
                    if item.get("salary_max") is not None:
                        salary_max = int(item["salary_max"])

                # Parse remote status
                workplace_type = (
                    item.get("workplaceType")
                    or item.get("workplace_type")
                    or ""
                )
                remote = workplace_type.lower() == "remote" if workplace_type else False
                if not remote:
                    remote = item.get("is_remote", False)

                # Parse location
                location = item.get("location") or item.get("job_location")

                # Parse posted date
                posted_at = None
                posted_str = (
                    item.get("postedAt")
                    or item.get("posted_at")
                    or item.get("date_posted")
                    or item.get("created")
                )
                if posted_str:
                    try:
                        posted_at = datetime.fromisoformat(
                            posted_str.replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError):
                        pass

                job = RawJob(
                    title=item.get("title") or item.get("job_title", "Unknown"),
                    company=item.get("companyName") or item.get("company_name") or item.get("company", "Unknown"),
                    url=item.get("url") or item.get("job_url"),
                    location=location,
                    description=item.get("description") or item.get("job_description"),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    employment_type=item.get("employmentType") or item.get("employment_type"),
                    remote=bool(remote),
                    source="linkedin",
                    source_id=str(item.get("id", "")),
                    posted_at=posted_at,
                    raw_data=item,
                )
                jobs.append(job)
            except Exception as exc:
                logger.warning("Failed to parse LinkedIn job item: %s", exc)
                continue

        logger.info("LinkedIn returned %d jobs", len(jobs))
        return jobs
