"""Tests for H1B data freshness utilities (Story 7-9).

Covers: is_stale, get_stale_warning, metrics endpoint.
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.research.h1b_service import (
    get_stale_warning,
    is_stale,
)


# ---------------------------------------------------------------------------
# is_stale tests
# ---------------------------------------------------------------------------


class TestIsStale:
    def test_fresh_data(self):
        """Data updated 1 day ago is not stale for 7-day threshold."""
        updated = datetime.now(timezone.utc) - timedelta(days=1)
        assert is_stale(updated, threshold_days=7) is False

    def test_stale_data(self):
        """Data updated 10 days ago is stale for 7-day threshold."""
        updated = datetime.now(timezone.utc) - timedelta(days=10)
        assert is_stale(updated, threshold_days=7) is True

    def test_exactly_threshold(self):
        """Data exactly at threshold is stale."""
        updated = datetime.now(timezone.utc) - timedelta(days=7)
        assert is_stale(updated, threshold_days=7) is True

    def test_none_is_stale(self):
        """None timestamp is considered stale."""
        assert is_stale(None, threshold_days=7) is True


# ---------------------------------------------------------------------------
# get_stale_warning tests
# ---------------------------------------------------------------------------


class TestGetStaleWarning:
    def test_no_warning_for_fresh_data(self):
        """Data < 14 days old returns None."""
        updated = datetime.now(timezone.utc) - timedelta(days=5)
        assert get_stale_warning(updated) is None

    def test_warning_for_stale_data(self):
        """Data > 14 days old returns warning dict."""
        updated = datetime.now(timezone.utc) - timedelta(days=20)
        result = get_stale_warning(updated)

        assert result is not None
        assert result["stale_warning"] is True
        assert "may be outdated" in result["message"].lower()

    def test_warning_for_none(self):
        """None timestamp returns warning."""
        result = get_stale_warning(None)

        assert result is not None
        assert result["stale_warning"] is True


# ---------------------------------------------------------------------------
# API stale_warning tests (via endpoint)
# ---------------------------------------------------------------------------


from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
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
    h1b_service._tables_ensured = False
    yield
    h1b_service._tables_ensured = False


class TestSponsorEndpointStaleWarning:
    @pytest.mark.asyncio
    async def test_includes_stale_warning_when_old(self):
        """GET /sponsors/{company} includes stale_warning for old data."""
        mock_cm, mock_sess = _mock_session_cm()

        tier_row = MagicMock()
        tier_row.__getitem__ = lambda self, key: {"tier": "h1b_pro"}[key]
        tier_result = MagicMock()
        tier_result.mappings.return_value.first.return_value = tier_row

        old_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        sponsor_row = MagicMock()
        sponsor_row.__getitem__ = lambda self, key: {
            "company_name": "OldCorp",
            "company_name_normalized": "oldcorp",
            "domain": None,
            "total_petitions": 10,
            "approval_rate": 0.80,
            "avg_wage": None,
            "wage_source": None,
            "last_updated_h1bgrader": None,
            "last_updated_myvisajobs": None,
            "last_updated_uscis": None,
            "updated_at": old_date,
        }[key]
        sponsor_result = MagicMock()
        sponsor_result.mappings.return_value.first.return_value = sponsor_row

        mock_sess.execute.side_effect = [
            MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(),
            tier_result,
            sponsor_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/h1b/sponsors/OldCorp")

        assert resp.status_code == 200
        data = resp.json()
        assert data.get("stale_warning") is True


class TestMetricsEndpoint:
    @pytest.mark.asyncio
    async def test_returns_metrics(self):
        """GET /h1b/metrics returns freshness metrics."""
        mock_cm, mock_sess = _mock_session_cm()

        tier_row = MagicMock()
        tier_row.__getitem__ = lambda self, key: {"tier": "enterprise"}[key]
        tier_result = MagicMock()
        tier_result.mappings.return_value.first.return_value = tier_row

        metrics_row = MagicMock()
        metrics_row.__getitem__ = lambda self, key: {
            "total_sponsors": 100,
            "stale_count": 15,
            "avg_age_days": 5.5,
        }[key]
        metrics_result = MagicMock()
        metrics_result.mappings.return_value.first.return_value = metrics_row

        mock_sess.execute.side_effect = [
            MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(),
            tier_result,
            metrics_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/h1b/metrics")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_sponsors"] == 100
        assert data["stale_count"] == 15
