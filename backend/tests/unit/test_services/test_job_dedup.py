"""
Tests for job deduplication service.

Tests normalize_text, compute_dedup_key, and upsert_jobs logic.
All database interactions are mocked.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.job_dedup import compute_dedup_key, normalize_text
from app.services.job_sources.base import RawJob


# ---------------------------------------------------------------------------
# normalize_text tests
# ---------------------------------------------------------------------------


class TestNormalizeText:
    def test_lowercase_and_strip(self):
        assert normalize_text("  Hello World  ") == "hello world"

    def test_collapse_spaces(self):
        assert normalize_text("a   b    c") == "a b c"

    def test_none_returns_empty(self):
        assert normalize_text(None) == ""

    def test_empty_string(self):
        assert normalize_text("") == ""


# ---------------------------------------------------------------------------
# compute_dedup_key tests
# ---------------------------------------------------------------------------


class TestComputeDedupKey:
    def test_url_based_dedup(self):
        """Same URL produces same dedup key."""
        job1 = RawJob(title="A", company="B", url="https://example.com/job/1")
        job2 = RawJob(title="C", company="D", url="https://example.com/job/1")
        assert compute_dedup_key(job1) == compute_dedup_key(job2)

    def test_content_based_dedup(self):
        """Same title + company + location produces same dedup key."""
        job1 = RawJob(title="Engineer", company="Acme", location="NYC", url=None)
        job2 = RawJob(title="Engineer", company="Acme", location="NYC", url=None)
        assert compute_dedup_key(job1) == compute_dedup_key(job2)

    def test_content_dedup_case_insensitive(self):
        """Dedup key is case insensitive."""
        job1 = RawJob(title="Engineer", company="Acme", location="NYC", url=None)
        job2 = RawJob(title="ENGINEER", company="acme", location="nyc", url=None)
        assert compute_dedup_key(job1) == compute_dedup_key(job2)

    def test_different_jobs_not_deduped(self):
        """Different jobs produce different dedup keys."""
        job1 = RawJob(title="Engineer", company="Acme", url=None)
        job2 = RawJob(title="Designer", company="Acme", url=None)
        assert compute_dedup_key(job1) != compute_dedup_key(job2)

    def test_different_urls_not_deduped(self):
        """Different URLs produce different dedup keys."""
        job1 = RawJob(title="A", company="B", url="https://example.com/1")
        job2 = RawJob(title="A", company="B", url="https://example.com/2")
        assert compute_dedup_key(job1) != compute_dedup_key(job2)

    def test_url_takes_precedence_over_content(self):
        """URL-based key is different from content-based key for same data."""
        job_with_url = RawJob(
            title="Eng", company="Acme", location="NYC",
            url="https://example.com/job"
        )
        job_without_url = RawJob(
            title="Eng", company="Acme", location="NYC", url=None
        )
        # Different because one uses URL hash and other uses content hash
        assert compute_dedup_key(job_with_url) != compute_dedup_key(job_without_url)


# ---------------------------------------------------------------------------
# upsert_jobs tests
# ---------------------------------------------------------------------------


def _make_fake_job(**kwargs):
    """Create a fake Job ORM-like object for mock query results."""
    defaults = {
        "id": uuid4(),
        "title": "Engineer",
        "company": "Acme",
        "url": None,
        "location": None,
        "description": None,
        "salary_min": None,
        "salary_max": None,
        "employment_type": None,
        "remote": False,
        "source_id": None,
        "raw_data": None,
        "posted_at": None,
        "source": "test",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class _FakeScalarsResult:
    """Mimic result.scalars().all() chain."""

    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class _FakeResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return _FakeScalarsResult(self._items)


def _setup_upsert_mocks():
    """Set up all mocks needed for upsert_jobs tests.

    Mocks sys.modules for app.db.* (avoids asyncpg),
    and patches select/and_ in the dedup module.

    Returns (context_manager, MockJob).
    Use as: with _setup_upsert_mocks() as (ctx, MockJob): ...
    """
    # Create a mock Job class with SQLAlchemy column descriptors
    MockJob = MagicMock()
    MockJob.url = MagicMock()
    MockJob.url.in_ = MagicMock()
    MockJob.title = MagicMock()
    MockJob.title.in_ = MagicMock()
    MockJob.company = MagicMock()
    MockJob.company.in_ = MagicMock()

    # Create mock modules for the app.db package
    mock_models = MagicMock()
    mock_models.Job = MockJob

    mock_engine = MagicMock()
    mock_session_mod = MagicMock()
    mock_db_init = MagicMock()

    modules_patch = {
        "app.db": mock_db_init,
        "app.db.engine": mock_engine,
        "app.db.session": mock_session_mod,
        "app.db.models": mock_models,
    }

    return modules_patch, MockJob


class TestUpsertJobs:
    @pytest.mark.asyncio
    async def test_empty_input_returns_empty(self):
        """Empty input returns empty list without DB queries."""
        modules_patch, _ = _setup_upsert_mocks()
        with patch.dict(sys.modules, modules_patch):
            from app.services.job_dedup import upsert_jobs
            session = AsyncMock()
            result = await upsert_jobs([], session)
            assert result == []
            session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_new_job_inserted(self):
        """A job with no existing match is inserted as new."""
        raw = RawJob(
            title="Engineer",
            company="Acme",
            url="https://example.com/job/1",
            source="jsearch",
            source_id="abc",
        )

        session = AsyncMock()
        session.execute.return_value = _FakeResult([])
        session.add = MagicMock()
        session.flush = AsyncMock()

        mock_instance = _make_fake_job(url="https://example.com/job/1")
        modules_patch, MockJob = _setup_upsert_mocks()
        MockJob.return_value = mock_instance

        # Mock select() and and_() to avoid SQLAlchemy validation
        mock_select = MagicMock()
        mock_select.return_value.where.return_value = MagicMock()

        mock_and = MagicMock(return_value=MagicMock())

        with patch.dict(sys.modules, modules_patch), \
             patch("app.services.job_dedup.select", mock_select), \
             patch("sqlalchemy.and_", mock_and):
            from app.services.job_dedup import upsert_jobs
            result = await upsert_jobs([raw], session)

        assert len(result) == 1
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_duplicate_url_updates_existing(self):
        """A job matching an existing URL updates rather than inserts."""
        existing = _make_fake_job(
            url="https://example.com/job/1",
            title="Old Title",
            company="Acme",
            salary_min=None,
        )

        raw = RawJob(
            title="Engineer",
            company="Acme",
            url="https://example.com/job/1",
            source="jsearch",
            salary_min=80000,
        )

        session = AsyncMock()
        session.execute.return_value = _FakeResult([existing])
        session.add = MagicMock()
        session.flush = AsyncMock()

        modules_patch, _ = _setup_upsert_mocks()
        mock_select = MagicMock()
        mock_select.return_value.where.return_value = MagicMock()

        with patch.dict(sys.modules, modules_patch), \
             patch("app.services.job_dedup.select", mock_select):
            from app.services.job_dedup import upsert_jobs
            result = await upsert_jobs([raw], session)

        assert len(result) == 1
        assert result[0] is existing
        # salary_min should have been updated
        assert existing.salary_min == 80000
        # Should not have called session.add for existing job
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_dedup_within_same_batch(self):
        """Duplicate jobs within the same batch are deduplicated."""
        raw1 = RawJob(
            title="Engineer",
            company="Acme",
            url="https://example.com/job/1",
            source="jsearch",
        )
        raw2 = RawJob(
            title="Engineer",
            company="Acme",
            url="https://example.com/job/1",
            source="adzuna",
        )

        session = AsyncMock()
        session.execute.return_value = _FakeResult([])
        session.add = MagicMock()
        session.flush = AsyncMock()

        mock_instance = _make_fake_job(url="https://example.com/job/1")
        modules_patch, MockJob = _setup_upsert_mocks()
        MockJob.return_value = mock_instance
        mock_select = MagicMock()
        mock_select.return_value.where.return_value = MagicMock()

        mock_and = MagicMock(return_value=MagicMock())

        with patch.dict(sys.modules, modules_patch), \
             patch("app.services.job_dedup.select", mock_select), \
             patch("sqlalchemy.and_", mock_and):
            from app.services.job_dedup import upsert_jobs
            result = await upsert_jobs([raw1, raw2], session)

        # Only one job should be stored (second is a duplicate)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_salary_zero_preserved_on_update(self):
        """salary_min=0 should still update the existing job (not be skipped)."""
        existing = _make_fake_job(
            url="https://example.com/job/1",
            salary_min=50000,
            salary_max=80000,
        )

        raw = RawJob(
            title="Engineer",
            company="Acme",
            url="https://example.com/job/1",
            source="jsearch",
            salary_min=0,
            salary_max=0,
        )

        session = AsyncMock()
        session.execute.return_value = _FakeResult([existing])
        session.add = MagicMock()
        session.flush = AsyncMock()

        modules_patch, _ = _setup_upsert_mocks()
        mock_select = MagicMock()
        mock_select.return_value.where.return_value = MagicMock()

        with patch.dict(sys.modules, modules_patch), \
             patch("app.services.job_dedup.select", mock_select):
            from app.services.job_dedup import upsert_jobs
            await upsert_jobs([raw], session)

        # salary=0 should still be written (H3 fix: not skipped by truthy check)
        assert existing.salary_min == 0
        assert existing.salary_max == 0
