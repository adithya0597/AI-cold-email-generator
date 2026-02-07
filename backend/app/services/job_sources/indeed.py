"""
Indeed job source client via RapidAPI scraper endpoint.

Indeed does NOT have a public API. This client uses a RapidAPI-hosted
Indeed scraper/aggregator service configured via INDEED_RAPIDAPI_HOST.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from app.config import settings
from app.services.job_sources.base import BaseJobSource, RawJob

logger = logging.getLogger(__name__)


class IndeedSource(BaseJobSource):
    """Indeed job board client via RapidAPI scraper."""

    source_name = "indeed"

    def __init__(
        self,
        api_key: str | None = None,
        host: str | None = None,
        timeout: float = 30.0,
        request_delay: float = 1.0,
        client: httpx.AsyncClient | None = None,
    ):
        self._api_key = api_key or settings.RAPIDAPI_KEY
        self._host = host or settings.INDEED_RAPIDAPI_HOST
        self._timeout = timeout
        self._request_delay = request_delay  # Reserved for future pagination support
        self._client = client

    async def search(
        self,
        query: str,
        location: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[RawJob]:
        """Search Indeed via RapidAPI scraper for matching jobs.

        Returns empty list on any failure (network, auth, parse).
        """
        if not self._api_key or not self._host:
            logger.warning("Indeed API credentials not configured, skipping")
            return []

        filters = filters or {}

        params: dict[str, Any] = {
            "query": query,
            "page": "1",
            "num_pages": "1",
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
                "Indeed API HTTP error: %s %s", exc.response.status_code, exc
            )
            return []
        except Exception as exc:
            logger.error("Indeed API request failed: %s", exc)
            return []

        return self._parse_response(data)

    def _parse_response(self, data: dict[str, Any]) -> list[RawJob]:
        """Parse Indeed API response into RawJob instances.

        Handles multiple response formats defensively — different RapidAPI
        Indeed providers may use different field names.
        """
        jobs: list[RawJob] = []
        results = data.get("data") or data.get("results") or []

        for item in results:
            try:
                # Parse salary — use `is not None` to handle salary=0 correctly
                salary_min = None
                salary_max = None
                if item.get("salary_min") is not None:
                    salary_min = int(item["salary_min"])
                if item.get("salary_max") is not None:
                    salary_max = int(item["salary_max"])

                # Parse remote status
                remote = item.get("is_remote", False)

                # Parse location
                location = item.get("job_location") or item.get("location")

                # Parse posted date
                posted_at = None
                posted_str = item.get("date_posted") or item.get("created")
                if posted_str:
                    try:
                        posted_at = datetime.fromisoformat(
                            posted_str.replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError):
                        pass

                job = RawJob(
                    title=item.get("job_title") or item.get("title", "Unknown"),
                    company=item.get("company_name") or item.get("company", "Unknown"),
                    url=item.get("job_url") or item.get("url"),
                    location=location,
                    description=item.get("job_description") or item.get("description"),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    employment_type=item.get("job_type") or item.get("employment_type"),
                    remote=bool(remote),
                    source="indeed",
                    source_id=str(item.get("id", "")),
                    posted_at=posted_at,
                    raw_data=item,
                )
                jobs.append(job)
            except Exception as exc:
                logger.warning("Failed to parse Indeed job item: %s", exc)
                continue

        logger.info("Indeed returned %d jobs", len(jobs))
        return jobs
