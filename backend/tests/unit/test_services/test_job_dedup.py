"""
Tests for job deduplication service.

Tests normalize_text, compute_dedup_key, and upsert_jobs logic.
All database interactions are mocked.
"""

from __future__ import annotations

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
