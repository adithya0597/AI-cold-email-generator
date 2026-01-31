"""
Base classes and data structures for job source clients.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RawJob:
    """Normalized job listing from any external source."""

    title: str
    company: str
    url: str | None = None
    location: str | None = None
    description: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    employment_type: str | None = None  # "full_time", "part_time", "contract"
    remote: bool = False
    source: str = ""  # "jsearch", "adzuna"
    source_id: str | None = None  # External API job ID
    posted_at: datetime | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


class BaseJobSource(ABC):
    """Abstract base class for job board API clients."""

    source_name: str = "unknown"

    @abstractmethod
    async def search(
        self,
        query: str,
        location: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[RawJob]:
        """Search for jobs matching the given query and filters.

        Args:
            query: Search query string (e.g. job titles).
            location: Optional location filter.
            filters: Optional additional filters (salary_min, employment_type, etc.)

        Returns:
            List of RawJob instances. Returns empty list on failure (never raises).
        """
        ...
