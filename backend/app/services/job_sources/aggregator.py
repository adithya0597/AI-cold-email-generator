"""
Job source aggregator -- queries all configured sources in parallel.

Merges results, logs individual source failures, and continues with
whatever sources succeed. Returns empty list only if ALL sources fail.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.services.job_sources.base import BaseJobSource, RawJob

logger = logging.getLogger(__name__)


class JobAggregator:
    """Aggregates job listings from multiple sources in parallel."""

    def __init__(
        self,
        sources: list[BaseJobSource] | None = None,
        per_source_timeout: float = 30.0,
    ):
        self._sources = sources or []
        self._per_source_timeout = per_source_timeout

    async def search_all(
        self,
        query: str,
        location: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[RawJob]:
        """Query all sources in parallel and merge results.

        Each source has an individual timeout. Sources that fail or timeout
        are logged and skipped -- successful results are merged.

        Args:
            query: Search query string.
            location: Optional location filter.
            filters: Optional additional filters.

        Returns:
            Merged list of RawJob from all successful sources.
        """
        if not self._sources:
            logger.warning("No job sources configured")
            return []

        tasks = [
            self._search_with_timeout(source, query, location, filters)
            for source in self._sources
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        merged: list[RawJob] = []
        for i, result in enumerate(results):
            source_name = self._sources[i].source_name
            if isinstance(result, Exception):
                logger.error(
                    "Job source '%s' failed: %s", source_name, result
                )
            elif isinstance(result, list):
                logger.info(
                    "Job source '%s' returned %d jobs", source_name, len(result)
                )
                merged.extend(result)
            else:
                logger.warning(
                    "Job source '%s' returned unexpected type: %s",
                    source_name,
                    type(result),
                )

        logger.info("Aggregator total: %d jobs from %d sources", len(merged), len(self._sources))
        return merged

    async def _search_with_timeout(
        self,
        source: BaseJobSource,
        query: str,
        location: str | None,
        filters: dict[str, Any] | None,
    ) -> list[RawJob]:
        """Run a single source search with timeout."""
        return await asyncio.wait_for(
            source.search(query, location, filters),
            timeout=self._per_source_timeout,
        )
