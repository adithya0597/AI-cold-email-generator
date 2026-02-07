"""
Job source aggregator clients for JobPilot.

Provides abstract base, concrete API clients (JSearch, Adzuna, Indeed, LinkedIn),
and an aggregator that queries all sources in parallel.
"""

from app.services.job_sources.aggregator import JobAggregator
from app.services.job_sources.adzuna import AdzunaSource
from app.services.job_sources.base import BaseJobSource, RawJob
from app.services.job_sources.indeed import IndeedSource
from app.services.job_sources.jsearch import JSearchSource
from app.services.job_sources.linkedin import LinkedInSource

__all__ = [
    "BaseJobSource",
    "RawJob",
    "JSearchSource",
    "AdzunaSource",
    "IndeedSource",
    "LinkedInSource",
    "JobAggregator",
]
