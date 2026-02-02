"""Tests for privacy proof API endpoints (Story 6-12).

Covers: proof with entries, proof empty, report download.
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
# Test: GET /privacy/proof
# ---------------------------------------------------------------------------


class TestGetPrivacyProof:
    @pytest.mark.asyncio
    async def test_proof_with_entries(self):
        """GET /proof returns proof data for blocklisted companies."""
        mock_cm, mock_sess = _mock_session_cm()

        blocklist_row = MagicMock()
        blocklist_row.__getitem__ = lambda self, key: {
            "company_name": "Acme Corp",
            "note": "Current employer",
        }[key]
        blocklist_result = MagicMock()
        blocklist_result.mappings.return_value.all.return_value = [blocklist_row]

        audit_row = MagicMock()
        audit_row.__getitem__ = lambda self, key: {
            "id": "audit-1",
            "company_name": "Acme Corp",
            "action_type": "blocked_match",
            "details": "Blocked job match from Acme Corp",
            "created_at": "2025-01-15T00:00:00+00:00",
        }[key]
        audit_result = MagicMock()
        audit_result.mappings.return_value.all.return_value = [audit_row]

        mock_sess.execute.side_effect = [
            MagicMock(),  # CREATE TABLE stealth_settings
            MagicMock(),  # CREATE TABLE employer_blocklist
            MagicMock(),  # CREATE TABLE privacy_audit_log
            MagicMock(),  # CREATE TABLE passive_mode_settings
            blocklist_result,
            audit_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/privacy/proof")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        entry = data["entries"][0]
        assert entry["company_name"] == "Acme Corp"
        assert entry["exposure_count"] == 0
        assert "last_checked" in entry
        assert len(entry["blocked_actions"]) == 1
        assert entry["blocked_actions"][0]["action_type"] == "blocked_match"

    @pytest.mark.asyncio
    async def test_proof_empty(self):
        """GET /proof returns empty when no blocklist entries."""
        mock_cm, mock_sess = _mock_session_cm()

        empty_result = MagicMock()
        empty_result.mappings.return_value.all.return_value = []

        mock_sess.execute.side_effect = [
            MagicMock(),  # CREATE TABLE stealth_settings
            MagicMock(),  # CREATE TABLE employer_blocklist
            MagicMock(),  # CREATE TABLE privacy_audit_log
            MagicMock(),  # CREATE TABLE passive_mode_settings
            empty_result,  # blocklist
            empty_result,  # audit
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/privacy/proof")

        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["entries"] == []


# ---------------------------------------------------------------------------
# Test: GET /privacy/proof/report
# ---------------------------------------------------------------------------


class TestDownloadReport:
    @pytest.mark.asyncio
    async def test_download_report(self):
        """GET /proof/report returns JSON privacy report without user_id."""
        mock_cm, mock_sess = _mock_session_cm()

        blocklist_row = MagicMock()
        blocklist_row.__getitem__ = lambda self, key: {
            "company_name": "Acme Corp",
            "note": "Current employer",
            "created_at": "2025-01-10T00:00:00+00:00",
        }[key]
        blocklist_result = MagicMock()
        blocklist_result.mappings.return_value.all.return_value = [blocklist_row]

        audit_result = MagicMock()
        audit_result.mappings.return_value.all.return_value = []

        mock_sess.execute.side_effect = [
            MagicMock(),  # CREATE TABLE stealth_settings
            MagicMock(),  # CREATE TABLE employer_blocklist
            MagicMock(),  # CREATE TABLE privacy_audit_log
            MagicMock(),  # CREATE TABLE passive_mode_settings
            blocklist_result,
            audit_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/privacy/proof/report")

        assert resp.status_code == 200
        data = resp.json()
        assert data["report_type"] == "privacy_proof"
        assert data["total_exposures"] == 0
        assert len(data["blocklisted_companies"]) == 1
        assert data["blocklisted_companies"][0]["company_name"] == "Acme Corp"
        assert "generated_at" in data
        assert "user_id" not in data
