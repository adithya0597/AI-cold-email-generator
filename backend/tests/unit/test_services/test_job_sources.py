"""
Tests for job source API clients and aggregator.

All external HTTP calls are mocked -- no real API calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.job_sources.adzuna import AdzunaSource
from app.services.job_sources.aggregator import JobAggregator
from app.services.job_sources.base import BaseJobSource, RawJob
from app.services.job_sources.jsearch import JSearchSource


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

JSEARCH_RESPONSE = {
    "data": [
        {
            "job_id": "j1",
            "job_title": "Senior Software Engineer",
            "employer_name": "Acme Corp",
            "job_apply_link": "https://acme.com/apply/1",
            "job_city": "San Francisco",
            "job_state": "CA",
            "job_country": "US",
            "job_description": "Build great software using Python and React.",
            "job_min_salary": 150000,
            "job_max_salary": 200000,
            "job_employment_type": "FULLTIME",
            "job_is_remote": True,
            "job_posted_at_datetime_utc": "2026-01-28T10:00:00.000Z",
        },
        {
            "job_id": "j2",
            "job_title": "Backend Developer",
            "employer_name": "StartupX",
            "job_apply_link": "https://startupx.com/jobs/2",
            "job_city": "New York",
            "job_state": "NY",
            "job_country": "US",
            "job_description": "FastAPI and PostgreSQL experience required.",
            "job_min_salary": None,
            "job_max_salary": None,
            "job_employment_type": "FULLTIME",
            "job_is_remote": False,
            "job_posted_at_datetime_utc": None,
        },
    ]
}

ADZUNA_RESPONSE = {
    "results": [
        {
            "id": "a1",
            "title": "Full Stack Engineer",
            "company": {"display_name": "BigTech Inc"},
            "redirect_url": "https://adzuna.com/job/a1",
            "location": {"display_name": "Austin, TX"},
            "description": "React and Node.js full stack role.",
            "salary_min": 120000,
            "salary_max": 160000,
            "contract_type": "permanent",
            "created": "2026-01-29T12:00:00Z",
        }
    ]
}


def _mock_httpx_response(data: dict, status_code: int = 200) -> httpx.Response:
    """Create a mock httpx.Response."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = data
    response.raise_for_status.return_value = None
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=response
        )
    return response


# ---------------------------------------------------------------------------
# JSearchSource tests
# ---------------------------------------------------------------------------


class TestJSearchSource:
    """Tests for JSearch API client."""

    @pytest.mark.asyncio
    async def test_search_returns_raw_jobs(self):
        """JSearch returns list of RawJob from valid response."""
        source = JSearchSource(api_key="test-key")

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_httpx_response(JSEARCH_RESPONSE))

        with patch("app.services.job_sources.jsearch.httpx.AsyncClient", return_value=mock_client):
            jobs = await source.search("software engineer")

        assert len(jobs) == 2
        assert isinstance(jobs[0], RawJob)
        assert jobs[0].title == "Senior Software Engineer"
        assert jobs[0].company == "Acme Corp"
        assert jobs[0].source == "jsearch"
        assert jobs[0].salary_min == 150000
        assert jobs[0].salary_max == 200000
        assert jobs[0].remote is True
        assert jobs[0].location == "San Francisco, CA, US"

    @pytest.mark.asyncio
    async def test_search_empty_response(self):
        """JSearch returns empty list when API returns no data."""
        source = JSearchSource(api_key="test-key")
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_httpx_response({"data": []}))

        with patch("app.services.job_sources.jsearch.httpx.AsyncClient", return_value=mock_client):
            jobs = await source.search("nonexistent role")

        assert jobs == []

    @pytest.mark.asyncio
    async def test_search_api_error_returns_empty(self):
        """JSearch returns empty list on HTTP error."""
        source = JSearchSource(api_key="test-key")
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_httpx_response({}, status_code=500))

        with patch("app.services.job_sources.jsearch.httpx.AsyncClient", return_value=mock_client):
            jobs = await source.search("software engineer")

        assert jobs == []

    @pytest.mark.asyncio
    async def test_search_no_api_key_returns_empty(self):
        """JSearch returns empty list when API key is not set."""
        source = JSearchSource(api_key="")
        jobs = await source.search("software engineer")
        assert jobs == []

    @pytest.mark.asyncio
    async def test_search_network_error_returns_empty(self):
        """JSearch returns empty list on network error."""
        source = JSearchSource(api_key="test-key")
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("connection failed"))

        with patch("app.services.job_sources.jsearch.httpx.AsyncClient", return_value=mock_client):
            jobs = await source.search("software engineer")

        assert jobs == []


# ---------------------------------------------------------------------------
# AdzunaSource tests
# ---------------------------------------------------------------------------


class TestAdzunaSource:
    """Tests for Adzuna API client."""

    @pytest.mark.asyncio
    async def test_search_returns_raw_jobs(self):
        """Adzuna returns list of RawJob from valid response."""
        source = AdzunaSource(app_id="test-id", app_key="test-key")

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_httpx_response(ADZUNA_RESPONSE))

        with patch("app.services.job_sources.adzuna.httpx.AsyncClient", return_value=mock_client):
            jobs = await source.search("full stack engineer")

        assert len(jobs) == 1
        assert isinstance(jobs[0], RawJob)
        assert jobs[0].title == "Full Stack Engineer"
        assert jobs[0].company == "BigTech Inc"
        assert jobs[0].source == "adzuna"
        assert jobs[0].salary_min == 120000
        assert jobs[0].location == "Austin, TX"

    @pytest.mark.asyncio
    async def test_search_empty_response(self):
        """Adzuna returns empty list when API returns no results."""
        source = AdzunaSource(app_id="test-id", app_key="test-key")
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_httpx_response({"results": []}))

        with patch("app.services.job_sources.adzuna.httpx.AsyncClient", return_value=mock_client):
            jobs = await source.search("nonexistent")

        assert jobs == []

    @pytest.mark.asyncio
    async def test_search_no_credentials_returns_empty(self):
        """Adzuna returns empty list when credentials are not set."""
        source = AdzunaSource(app_id="", app_key="")
        jobs = await source.search("engineer")
        assert jobs == []

    @pytest.mark.asyncio
    async def test_search_api_error_returns_empty(self):
        """Adzuna returns empty list on HTTP error."""
        source = AdzunaSource(app_id="test-id", app_key="test-key")
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_httpx_response({}, status_code=401))

        with patch("app.services.job_sources.adzuna.httpx.AsyncClient", return_value=mock_client):
            jobs = await source.search("engineer")

        assert jobs == []


# ---------------------------------------------------------------------------
# JobAggregator tests
# ---------------------------------------------------------------------------


class _MockSource(BaseJobSource):
    """Test source that returns pre-configured jobs."""

    def __init__(self, name: str, jobs: list[RawJob] | None = None, error: Exception | None = None):
        self.source_name = name
        self._jobs = jobs or []
        self._error = error

    async def search(self, query, location=None, filters=None):
        if self._error:
            raise self._error
        return self._jobs


class TestJobAggregator:
    """Tests for the multi-source aggregator."""

    @pytest.mark.asyncio
    async def test_merges_results_from_multiple_sources(self):
        """Aggregator merges jobs from all sources."""
        job1 = RawJob(title="Job A", company="Co A", source="src1")
        job2 = RawJob(title="Job B", company="Co B", source="src2")

        agg = JobAggregator(
            sources=[_MockSource("src1", [job1]), _MockSource("src2", [job2])]
        )
        results = await agg.search_all("query")

        assert len(results) == 2
        titles = {j.title for j in results}
        assert titles == {"Job A", "Job B"}

    @pytest.mark.asyncio
    async def test_graceful_degradation_one_source_fails(self):
        """Aggregator returns results from successful source when one fails."""
        job1 = RawJob(title="Job A", company="Co A", source="src1")

        agg = JobAggregator(
            sources=[
                _MockSource("src1", [job1]),
                _MockSource("src2", error=Exception("API down")),
            ]
        )
        results = await agg.search_all("query")

        assert len(results) == 1
        assert results[0].title == "Job A"

    @pytest.mark.asyncio
    async def test_all_sources_fail_returns_empty(self):
        """Aggregator returns empty list when all sources fail."""
        agg = JobAggregator(
            sources=[
                _MockSource("src1", error=Exception("fail1")),
                _MockSource("src2", error=Exception("fail2")),
            ]
        )
        results = await agg.search_all("query")
        assert results == []

    @pytest.mark.asyncio
    async def test_no_sources_returns_empty(self):
        """Aggregator returns empty list when no sources configured."""
        agg = JobAggregator(sources=[])
        results = await agg.search_all("query")
        assert results == []
