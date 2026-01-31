"""
Job source aggregator clients for JobPilot.

Provides abstract base, concrete API clients (JSearch, Adzuna),
and an aggregator that queries all sources in parallel.
"""

from app.services.job_sources.aggregator import JobAggregator
from app.services.job_sources.adzuna import AdzunaSource
from app.services.job_sources.base import BaseJobSource, RawJob
from app.services.job_sources.jsearch import JSearchSource

__all__ = [
    "BaseJobSource",
    "RawJob",
    "JSearchSource",
    "AdzunaSource",
    "JobAggregator",
]
