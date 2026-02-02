"""Tests for privacy/stealth mode API endpoints (Story 6-10).

Covers: get stealth status, toggle on (eligible), toggle on (ineligible).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1 import privacy as privacy_module
from app.api.v1.privacy import router
from app.auth.clerk import get_current_user_id

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
    privacy_module._tables_ensured = False
    yield
    privacy_module._tables_ensured = False


# ---------------------------------------------------------------------------
# Test: GET /privacy/stealth
# ---------------------------------------------------------------------------


class TestGetStealthStatus:
    @pytest.mark.asyncio
    async def test_returns_status_eligible(self):
        """GET /stealth returns stealth status for eligible user."""
        mock_cm, mock_sess = _mock_session_cm()

        tier_row = MagicMock()
        tier_row.__getitem__ = lambda self, key: {"tier": "career_insurance"}[key]
        tier_result = MagicMock()
        tier_result.mappings.return_value.first.return_value = tier_row

        stealth_row = MagicMock()
        stealth_row.__getitem__ = lambda self, key: {"stealth_enabled": True}[key]
        stealth_result = MagicMock()
        stealth_result.mappings.return_value.first.return_value = stealth_row

        mock_sess.execute.side_effect = [
            MagicMock(),  # CREATE TABLE stealth_settings
            MagicMock(),  # CREATE TABLE employer_blocklist
            MagicMock(),  # CREATE TABLE privacy_audit_log
            MagicMock(),  # CREATE TABLE passive_mode_settings
            tier_result,
            stealth_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/privacy/stealth")

        assert resp.status_code == 200
        data = resp.json()
        assert data["stealth_enabled"] is True
        assert data["eligible"] is True
        assert data["tier"] == "career_insurance"

    @pytest.mark.asyncio
    async def test_returns_ineligible_for_free_tier(self):
        """GET /stealth returns eligible=false for free tier user."""
        mock_cm, mock_sess = _mock_session_cm()

        tier_row = MagicMock()
        tier_row.__getitem__ = lambda self, key: {"tier": "free"}[key]
        tier_result = MagicMock()
        tier_result.mappings.return_value.first.return_value = tier_row

        stealth_result = MagicMock()
        stealth_result.mappings.return_value.first.return_value = None

        mock_sess.execute.side_effect = [
            MagicMock(),  # CREATE TABLE stealth_settings
            MagicMock(),  # CREATE TABLE employer_blocklist
            MagicMock(),  # CREATE TABLE privacy_audit_log
            MagicMock(),  # CREATE TABLE passive_mode_settings
            tier_result,
            stealth_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/privacy/stealth")

        assert resp.status_code == 200
        data = resp.json()
        assert data["stealth_enabled"] is False
        assert data["eligible"] is False
        assert data["tier"] == "free"


# ---------------------------------------------------------------------------
# Test: POST /privacy/stealth
# ---------------------------------------------------------------------------


class TestToggleStealth:
    @pytest.mark.asyncio
    async def test_toggle_on_eligible(self):
        """POST /stealth enables stealth for eligible user."""
        mock_cm, mock_sess = _mock_session_cm()

        tier_row = MagicMock()
        tier_row.__getitem__ = lambda self, key: {"tier": "career_insurance"}[key]
        tier_result = MagicMock()
        tier_result.mappings.return_value.first.return_value = tier_row

        mock_sess.execute.side_effect = [
            MagicMock(),  # CREATE TABLE stealth_settings
            MagicMock(),  # CREATE TABLE employer_blocklist
            MagicMock(),  # CREATE TABLE privacy_audit_log
            MagicMock(),  # CREATE TABLE passive_mode_settings
            tier_result,  # SELECT tier
            MagicMock(),  # INSERT/UPSERT
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/privacy/stealth",
                    json={"enabled": True},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["stealth_enabled"] is True
        assert data["eligible"] is True

    @pytest.mark.asyncio
    async def test_toggle_on_ineligible_returns_403(self):
        """POST /stealth returns 403 for free tier user."""
        mock_cm, mock_sess = _mock_session_cm()

        tier_row = MagicMock()
        tier_row.__getitem__ = lambda self, key: {"tier": "free"}[key]
        tier_result = MagicMock()
        tier_result.mappings.return_value.first.return_value = tier_row

        mock_sess.execute.side_effect = [
            MagicMock(),  # CREATE TABLE stealth_settings
            MagicMock(),  # CREATE TABLE employer_blocklist
            MagicMock(),  # CREATE TABLE privacy_audit_log
            MagicMock(),  # CREATE TABLE passive_mode_settings
            tier_result,  # SELECT tier
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/privacy/stealth",
                    json={"enabled": True},
                )

        assert resp.status_code == 403
        assert "Career Insurance" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_toggle_on_enterprise_eligible(self):
        """POST /stealth enables stealth for enterprise user."""
        mock_cm, mock_sess = _mock_session_cm()

        tier_row = MagicMock()
        tier_row.__getitem__ = lambda self, key: {"tier": "enterprise"}[key]
        tier_result = MagicMock()
        tier_result.mappings.return_value.first.return_value = tier_row

        mock_sess.execute.side_effect = [
            MagicMock(),  # CREATE TABLE stealth_settings
            MagicMock(),  # CREATE TABLE employer_blocklist
            MagicMock(),  # CREATE TABLE privacy_audit_log
            MagicMock(),  # CREATE TABLE passive_mode_settings
            tier_result,  # SELECT tier
            MagicMock(),  # INSERT/UPSERT
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/privacy/stealth",
                    json={"enabled": True},
                )

        assert resp.status_code == 200
        assert resp.json()["stealth_enabled"] is True
