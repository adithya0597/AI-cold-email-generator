"""Tests for H1B API endpoints (Story 7-1).

Covers: sponsor lookup, sponsor search, tier gating.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1 import h1b as h1b_module
from app.api.v1.h1b import router
from app.auth.clerk import get_current_user_id
from app.services.research import h1b_service

app = FastAPI()
app.include_router(router, prefix="/api/v1")
app.dependency_overrides[get_current_user_id] = lambda: "test-user-123"


def _mock_session_cm():
    mock_sess = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_sess)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm, mock_sess


@pytest.fixture(autouse=True)
def _reset_tables_flag():
    """Reset the _tables_ensured flag before each test."""
    h1b_service._tables_ensured = False
    yield
    h1b_service._tables_ensured = False


# ---------------------------------------------------------------------------
# GET /h1b/sponsors/{company}
# ---------------------------------------------------------------------------


class TestGetSponsor:
    @pytest.mark.asyncio
    async def test_returns_sponsor_data(self):
        """GET /sponsors/{company} returns data for eligible user."""
        mock_cm, mock_sess = _mock_session_cm()

        # Tier check
        tier_row = MagicMock()
        tier_row.__getitem__ = lambda self, key: {"tier": "h1b_pro"}[key]
        tier_result = MagicMock()
        tier_result.mappings.return_value.first.return_value = tier_row

        # Sponsor lookup
        sponsor_row = MagicMock()
        sponsor_row.__getitem__ = lambda self, key: {
            "company_name": "Google LLC",
            "company_name_normalized": "google",
            "domain": "google.com",
            "total_petitions": 500,
            "approval_rate": 0.95,
            "avg_wage": 150000.0,
            "wage_source": "uscis_lca",
            "last_updated_h1bgrader": "2025-01-15T00:00:00+00:00",
            "last_updated_myvisajobs": "2025-01-14T00:00:00+00:00",
            "last_updated_uscis": "2025-01-13T00:00:00+00:00",
            "updated_at": "2025-01-15T00:00:00+00:00",
        }[key]
        sponsor_result = MagicMock()
        sponsor_result.mappings.return_value.first.return_value = sponsor_row

        mock_sess.execute.side_effect = [
            MagicMock(),  # CREATE TABLE h1b_sponsors
            MagicMock(),  # CREATE TABLE h1b_source_records
            MagicMock(),  # INDEX 1
            MagicMock(),  # INDEX 2
            MagicMock(),  # INDEX 3
            tier_result,
            sponsor_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/h1b/sponsors/Google")

        assert resp.status_code == 200
        data = resp.json()
        assert data["company_name"] == "Google LLC"
        assert data["total_petitions"] == 500
        assert data["approval_rate"] == 0.95
        assert data["avg_wage"] == 150000.0
        assert "freshness" in data

    @pytest.mark.asyncio
    async def test_returns_404_when_not_found(self):
        """GET /sponsors/{company} returns 404 when no data."""
        mock_cm, mock_sess = _mock_session_cm()

        tier_row = MagicMock()
        tier_row.__getitem__ = lambda self, key: {"tier": "career_insurance"}[key]
        tier_result = MagicMock()
        tier_result.mappings.return_value.first.return_value = tier_row

        not_found = MagicMock()
        not_found.mappings.return_value.first.return_value = None

        mock_sess.execute.side_effect = [
            MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(),  # DDL
            tier_result,
            not_found,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/h1b/sponsors/NonexistentCorp")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_403_for_free_tier(self):
        """GET /sponsors/{company} returns 403 for free tier user."""
        mock_cm, mock_sess = _mock_session_cm()

        tier_row = MagicMock()
        tier_row.__getitem__ = lambda self, key: {"tier": "free"}[key]
        tier_result = MagicMock()
        tier_result.mappings.return_value.first.return_value = tier_row

        mock_sess.execute.side_effect = [
            MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(),  # DDL
            tier_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/h1b/sponsors/Google")

        assert resp.status_code == 403
        assert "H1B Pro" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_returns_403_for_pro_tier(self):
        """GET /sponsors/{company} returns 403 for pro tier user."""
        mock_cm, mock_sess = _mock_session_cm()

        tier_row = MagicMock()
        tier_row.__getitem__ = lambda self, key: {"tier": "pro"}[key]
        tier_result = MagicMock()
        tier_result.mappings.return_value.first.return_value = tier_row

        mock_sess.execute.side_effect = [
            MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(),  # DDL
            tier_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/h1b/sponsors/Google")

        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /h1b/sponsors?q=
# ---------------------------------------------------------------------------


class TestSearchSponsors:
    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        """GET /sponsors?q=goo returns matching sponsors."""
        mock_cm, mock_sess = _mock_session_cm()

        tier_row = MagicMock()
        tier_row.__getitem__ = lambda self, key: {"tier": "enterprise"}[key]
        tier_result = MagicMock()
        tier_result.mappings.return_value.first.return_value = tier_row

        search_row = MagicMock()
        search_row.__getitem__ = lambda self, key: {
            "company_name": "Google LLC",
            "company_name_normalized": "google",
            "domain": "google.com",
            "total_petitions": 500,
            "approval_rate": 0.95,
            "avg_wage": 150000.0,
            "wage_source": "uscis_lca",
        }[key]
        search_result = MagicMock()
        search_result.mappings.return_value.all.return_value = [search_row]

        mock_sess.execute.side_effect = [
            MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(),  # DDL
            tier_result,
            search_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/h1b/sponsors?q=goo")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["sponsors"][0]["company_name"] == "Google LLC"

    @pytest.mark.asyncio
    async def test_search_returns_empty(self):
        """GET /sponsors?q=xyz returns empty results."""
        mock_cm, mock_sess = _mock_session_cm()

        tier_row = MagicMock()
        tier_row.__getitem__ = lambda self, key: {"tier": "h1b_pro"}[key]
        tier_result = MagicMock()
        tier_result.mappings.return_value.first.return_value = tier_row

        empty_result = MagicMock()
        empty_result.mappings.return_value.all.return_value = []

        mock_sess.execute.side_effect = [
            MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(),  # DDL
            tier_result,
            empty_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/h1b/sponsors?q=xyznonexistent")

        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["sponsors"] == []

    @pytest.mark.asyncio
    async def test_search_requires_min_length(self):
        """GET /sponsors?q=a returns 422 (min_length=2)."""
        mock_cm, mock_sess = _mock_session_cm()

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/h1b/sponsors?q=a")

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_search_tier_gated(self):
        """GET /sponsors?q=goo returns 403 for free tier."""
        mock_cm, mock_sess = _mock_session_cm()

        tier_row = MagicMock()
        tier_row.__getitem__ = lambda self, key: {"tier": "free"}[key]
        tier_result = MagicMock()
        tier_result.mappings.return_value.first.return_value = tier_row

        mock_sess.execute.side_effect = [
            MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(),  # DDL
            tier_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/h1b/sponsors?q=goo")

        assert resp.status_code == 403
