"""Tests for employer blocklist API endpoints (Story 6-11).

Covers: list blocklist, add company, add without stealth, remove company.
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
# Test: GET /privacy/blocklist
# ---------------------------------------------------------------------------


class TestGetBlocklist:
    @pytest.mark.asyncio
    async def test_list_returns_entries(self):
        """GET /blocklist returns blocklisted companies."""
        mock_cm, mock_sess = _mock_session_cm()

        entry_row = MagicMock()
        entry_row.__getitem__ = lambda self, key: {
            "id": "entry-uuid-1",
            "company_name": "Acme Corp",
            "note": "Current employer",
            "created_at": "2025-01-15T00:00:00+00:00",
        }[key]

        list_result = MagicMock()
        list_result.mappings.return_value.all.return_value = [entry_row]

        mock_sess.execute.side_effect = [
            MagicMock(),  # CREATE TABLE stealth_settings
            MagicMock(),  # CREATE TABLE employer_blocklist
            MagicMock(),  # CREATE TABLE privacy_audit_log
            MagicMock(),  # CREATE TABLE passive_mode_settings
            list_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/privacy/blocklist")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["entries"][0]["company_name"] == "Acme Corp"
        assert data["entries"][0]["note"] == "Current employer"

    @pytest.mark.asyncio
    async def test_list_empty(self):
        """GET /blocklist returns empty list when no entries."""
        mock_cm, mock_sess = _mock_session_cm()

        list_result = MagicMock()
        list_result.mappings.return_value.all.return_value = []

        mock_sess.execute.side_effect = [
            MagicMock(),  # CREATE TABLE stealth_settings
            MagicMock(),  # CREATE TABLE employer_blocklist
            MagicMock(),  # CREATE TABLE privacy_audit_log
            MagicMock(),  # CREATE TABLE passive_mode_settings
            list_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/privacy/blocklist")

        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["entries"] == []


# ---------------------------------------------------------------------------
# Test: POST /privacy/blocklist
# ---------------------------------------------------------------------------


class TestAddToBlocklist:
    @pytest.mark.asyncio
    async def test_add_with_stealth_active(self):
        """POST /blocklist adds company when stealth is active."""
        mock_cm, mock_sess = _mock_session_cm()

        # Stealth check
        stealth_row = MagicMock()
        stealth_row.__getitem__ = lambda self, key: {"stealth_enabled": True}[key]
        stealth_result = MagicMock()
        stealth_result.mappings.return_value.first.return_value = stealth_row

        # INSERT RETURNING
        insert_row = MagicMock()
        insert_row.__getitem__ = lambda self, key: {
            "id": "new-entry-uuid",
            "company_name": "Evil Corp",
            "note": "Competitor",
            "created_at": "2025-01-20T00:00:00+00:00",
        }[key]
        insert_result = MagicMock()
        insert_result.mappings.return_value.first.return_value = insert_row

        mock_sess.execute.side_effect = [
            MagicMock(),  # CREATE TABLE stealth_settings
            MagicMock(),  # CREATE TABLE employer_blocklist
            MagicMock(),  # CREATE TABLE privacy_audit_log
            MagicMock(),  # CREATE TABLE passive_mode_settings
            stealth_result,
            insert_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/privacy/blocklist",
                    json={"company_name": "Evil Corp", "note": "Competitor"},
                )

        assert resp.status_code == 201
        data = resp.json()
        assert data["company_name"] == "Evil Corp"
        assert data["note"] == "Competitor"

    @pytest.mark.asyncio
    async def test_add_without_stealth_returns_403(self):
        """POST /blocklist returns 403 when stealth is not active."""
        mock_cm, mock_sess = _mock_session_cm()

        stealth_result = MagicMock()
        stealth_result.mappings.return_value.first.return_value = None

        mock_sess.execute.side_effect = [
            MagicMock(),  # CREATE TABLE stealth_settings
            MagicMock(),  # CREATE TABLE employer_blocklist
            MagicMock(),  # CREATE TABLE privacy_audit_log
            MagicMock(),  # CREATE TABLE passive_mode_settings
            stealth_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/privacy/blocklist",
                    json={"company_name": "Evil Corp"},
                )

        assert resp.status_code == 403
        assert "Stealth Mode" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Test: DELETE /privacy/blocklist/{id}
# ---------------------------------------------------------------------------


class TestRemoveFromBlocklist:
    @pytest.mark.asyncio
    async def test_remove_success(self):
        """DELETE /blocklist/{id} removes entry when stealth is active."""
        mock_cm, mock_sess = _mock_session_cm()

        stealth_row = MagicMock()
        stealth_row.__getitem__ = lambda self, key: {"stealth_enabled": True}[key]
        stealth_result = MagicMock()
        stealth_result.mappings.return_value.first.return_value = stealth_row

        delete_result = MagicMock()
        delete_result.rowcount = 1

        mock_sess.execute.side_effect = [
            MagicMock(),  # CREATE TABLE stealth_settings
            MagicMock(),  # CREATE TABLE employer_blocklist
            MagicMock(),  # CREATE TABLE privacy_audit_log
            MagicMock(),  # CREATE TABLE passive_mode_settings
            stealth_result,
            delete_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete("/api/v1/privacy/blocklist/entry-uuid-1")

        assert resp.status_code == 200
        assert resp.json()["status"] == "removed"

    @pytest.mark.asyncio
    async def test_remove_not_found(self):
        """DELETE /blocklist/{id} returns 404 when not found."""
        mock_cm, mock_sess = _mock_session_cm()

        stealth_row = MagicMock()
        stealth_row.__getitem__ = lambda self, key: {"stealth_enabled": True}[key]
        stealth_result = MagicMock()
        stealth_result.mappings.return_value.first.return_value = stealth_row

        delete_result = MagicMock()
        delete_result.rowcount = 0

        mock_sess.execute.side_effect = [
            MagicMock(),  # CREATE TABLE stealth_settings
            MagicMock(),  # CREATE TABLE employer_blocklist
            MagicMock(),  # CREATE TABLE privacy_audit_log
            MagicMock(),  # CREATE TABLE passive_mode_settings
            stealth_result,
            delete_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete("/api/v1/privacy/blocklist/nonexistent")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_without_stealth_returns_403(self):
        """DELETE /blocklist/{id} returns 403 when stealth is not active."""
        mock_cm, mock_sess = _mock_session_cm()

        stealth_result = MagicMock()
        stealth_result.mappings.return_value.first.return_value = None

        mock_sess.execute.side_effect = [
            MagicMock(),  # CREATE TABLE stealth_settings
            MagicMock(),  # CREATE TABLE employer_blocklist
            MagicMock(),  # CREATE TABLE privacy_audit_log
            MagicMock(),  # CREATE TABLE passive_mode_settings
            stealth_result,
        ]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete("/api/v1/privacy/blocklist/entry-uuid-1")

        assert resp.status_code == 403
        assert "Stealth Mode" in resp.json()["detail"]
