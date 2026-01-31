"""
Job deduplication and storage service.

Deduplicates raw jobs by URL first, then by (title + company + location) hash.
Upserts into the jobs table and returns ORM Job instances.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from app.services.job_sources.base import RawJob

logger = logging.getLogger(__name__)


def normalize_text(s: str | None) -> str:
    """Lowercase, strip whitespace, collapse multiple spaces."""
    if not s:
        return ""
    return re.sub(r"\s+", " ", s.strip().lower())


def compute_dedup_key(job: RawJob) -> str:
    """Compute a deduplication key for a raw job.

    Uses URL if present, otherwise hashes (normalized_title + company + location).
    """
    if job.url:
        return hashlib.sha256(normalize_text(job.url).encode()).hexdigest()

    composite = "|".join([
        normalize_text(job.title),
        normalize_text(job.company),
        normalize_text(job.location),
    ])
    return hashlib.sha256(composite.encode()).hexdigest()


async def upsert_jobs(raw_jobs: list[RawJob], session: Any) -> list[Any]:
    """Deduplicate and upsert raw jobs into the jobs table.

    Checks existing jobs by URL first, then by dedup key (title+company+location).
    Inserts new jobs, updates existing ones with fresh data.

    Args:
        raw_jobs: List of RawJob instances from aggregator.
        session: AsyncSession for database operations.

    Returns:
        List of Job ORM instances (both new and existing).
    """
    from app.db.models import Job

    if not raw_jobs:
        return []

    # Collect all URLs and dedup keys
    url_to_raw: dict[str, RawJob] = {}
    key_to_raw: dict[str, RawJob] = {}

    for rj in raw_jobs:
        dedup_key = compute_dedup_key(rj)
        if rj.url:
            url_to_raw[normalize_text(rj.url)] = rj
        key_to_raw[dedup_key] = rj

    # Check existing jobs by URL
    existing_by_url: dict[str, Any] = {}
    urls = [rj.url for rj in raw_jobs if rj.url]
    if urls:
        result = await session.execute(
            select(Job).where(Job.url.in_(urls))
        )
        for job in result.scalars().all():
            if job.url:
                existing_by_url[normalize_text(job.url)] = job

    # Check existing jobs by content-based dedup (title+company+location)
    # For jobs without URL matches, query DB by title+company combinations
    existing_by_content: dict[str, Any] = {}
    content_candidates = [
        rj for rj in raw_jobs
        if not (rj.url and normalize_text(rj.url) in existing_by_url)
    ]
    if content_candidates:
        # Query jobs matching any of the candidate titles+companies
        titles = list({rj.title for rj in content_candidates if rj.title})
        companies = list({rj.company for rj in content_candidates if rj.company})
        if titles and companies:
            from sqlalchemy import and_

            result = await session.execute(
                select(Job).where(
                    and_(Job.title.in_(titles), Job.company.in_(companies))
                )
            )
            for job in result.scalars().all():
                # Build content key for the existing DB job
                content_key = hashlib.sha256(
                    "|".join([
                        normalize_text(job.title),
                        normalize_text(job.company),
                        normalize_text(getattr(job, "location", None)),
                    ]).encode()
                ).hexdigest()
                existing_by_content[content_key] = job

    # Process each raw job
    result_jobs: list[Any] = []
    seen_keys: set[str] = set()

    for rj in raw_jobs:
        dedup_key = compute_dedup_key(rj)

        # Skip duplicates within the same batch
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        # Check if exists by URL
        norm_url = normalize_text(rj.url) if rj.url else None
        existing = existing_by_url.get(norm_url) if norm_url else None

        # If not found by URL, check by content-based key
        if not existing:
            content_key = hashlib.sha256(
                "|".join([
                    normalize_text(rj.title),
                    normalize_text(rj.company),
                    normalize_text(rj.location),
                ]).encode()
            ).hexdigest()
            existing = existing_by_content.get(content_key)

        if existing:
            # Update existing job with fresh data
            _update_job(existing, rj)
            result_jobs.append(existing)
            logger.debug("Updated existing job: %s at %s", rj.title, rj.company)
        else:
            # Create new job
            new_job = Job(
                id=uuid4(),
                source=rj.source,
                url=rj.url,
                title=rj.title,
                company=rj.company,
                description=rj.description,
                location=rj.location,
                salary_min=rj.salary_min,
                salary_max=rj.salary_max,
                employment_type=rj.employment_type,
                remote=rj.remote,
                source_id=rj.source_id,
                raw_data=rj.raw_data,
                posted_at=rj.posted_at,
            )
            session.add(new_job)
            result_jobs.append(new_job)
            logger.debug("Inserted new job: %s at %s", rj.title, rj.company)

    await session.flush()
    logger.info(
        "Upserted %d jobs (%d input, %d deduplicated)",
        len(result_jobs),
        len(raw_jobs),
        len(raw_jobs) - len(result_jobs),
    )
    return result_jobs


def _update_job(job: Any, raw: RawJob) -> None:
    """Update an existing Job ORM instance with fresh data from a RawJob."""
    if raw.description and not job.description:
        job.description = raw.description
    if raw.salary_min is not None:
        job.salary_min = raw.salary_min
    if raw.salary_max is not None:
        job.salary_max = raw.salary_max
    if raw.employment_type:
        job.employment_type = raw.employment_type
    if raw.remote is not None:
        job.remote = raw.remote
    if raw.raw_data:
        job.raw_data = raw.raw_data
    if raw.posted_at:
        job.posted_at = raw.posted_at
