"""Tests for passive mode API endpoints (Story 6-13).

Covers: get settings, update settings, activate sprint, ineligible.
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


class TestGetPassiveMode:
    @pytest.mark.asyncio
    async def test_returns_defaults_for_eligible_user(self):
        """GET /passive-mode returns defaults + eligible for career_insurance."""
        mock_cm, mock_sess = _mock_session_cm()

        tier_row = MagicMock()
        tier_row.__getitem__ = lambda self, key: {"tier": "career_insurance"}[key]
        tier_result = MagicMock()
        tier_result.mappings.return_value.first.return_value = tier_row

        settings_result = MagicMock()
        settings_result.mappings.return_value.first.return_value = None

        mock_sess.execute.side_effect = [
            MagicMock(),  # CREATE TABLE stealth_settings
            MagicMock(),  # CREATE TABLE employer_blocklist
            MagicMock(),  # CREATE TABLE privacy_audit_log
            MagicMock(),  # CREATE TABLE passive_mode_settings
            tier_result,
            settings_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/privacy/passive-mode")

        assert resp.status_code == 200
        data = resp.json()
        assert data["eligible"] is True
        assert data["search_frequency"] == "weekly"
        assert data["min_match_score"] == 70

    @pytest.mark.asyncio
    async def test_returns_ineligible_for_free_tier(self):
        """GET /passive-mode returns eligible=false for free tier."""
        mock_cm, mock_sess = _mock_session_cm()

        tier_row = MagicMock()
        tier_row.__getitem__ = lambda self, key: {"tier": "free"}[key]
        tier_result = MagicMock()
        tier_result.mappings.return_value.first.return_value = tier_row

        settings_result = MagicMock()
        settings_result.mappings.return_value.first.return_value = None

        mock_sess.execute.side_effect = [
            MagicMock(),  # CREATE TABLE stealth_settings
            MagicMock(),  # CREATE TABLE employer_blocklist
            MagicMock(),  # CREATE TABLE privacy_audit_log
            MagicMock(),  # CREATE TABLE passive_mode_settings
            tier_result,
            settings_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/privacy/passive-mode")

        assert resp.status_code == 200
        assert resp.json()["eligible"] is False


class TestUpdatePassiveMode:
    @pytest.mark.asyncio
    async def test_update_success(self):
        """PUT /passive-mode updates settings for eligible user."""
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
            tier_result,
            MagicMock(),  # UPSERT
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.put(
                    "/api/v1/privacy/passive-mode",
                    json={"search_frequency": "daily", "min_match_score": 80},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["search_frequency"] == "daily"
        assert data["min_match_score"] == 80

    @pytest.mark.asyncio
    async def test_update_ineligible_returns_403(self):
        """PUT /passive-mode returns 403 for free tier."""
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
            tier_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.put(
                    "/api/v1/privacy/passive-mode",
                    json={"search_frequency": "daily"},
                )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_update_invalid_frequency_returns_422(self):
        """PUT /passive-mode returns 422 for invalid frequency value."""
        mock_cm, mock_sess = _mock_session_cm()

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.put(
                    "/api/v1/privacy/passive-mode",
                    json={"search_frequency": "every_second"},
                )

        assert resp.status_code == 422


class TestActivateSprint:
    @pytest.mark.asyncio
    async def test_sprint_activation(self):
        """POST /passive-mode/sprint switches to sprint mode."""
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
            tier_result,
            MagicMock(),  # UPSERT sprint
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/privacy/passive-mode/sprint")

        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "sprint"
        assert data["search_frequency"] == "daily"
        assert data["min_match_score"] == 50
        assert data["notification_pref"] == "immediate"
