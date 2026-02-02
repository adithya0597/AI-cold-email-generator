"""Tests for follow-up tracking API endpoints (Story 6-9).

Covers: followup history, mark manual, followup count in list.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.applications import router
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


# ---------------------------------------------------------------------------
# Test: GET /{application_id}/followup-history
# ---------------------------------------------------------------------------


class TestFollowupHistory:
    @pytest.mark.asyncio
    async def test_history_returns_sent_followups(self):
        """GET /followup-history returns sent follow-ups with count."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: {
            "id": "sugg-uuid-1",
            "draft_subject": "Follow-up: Engineer at Acme",
            "sent_at": "2025-01-15T10:00:00+00:00",
        }[key]

        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [mock_row]
        mock_sess.execute.return_value = mock_result

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/applications/app-uuid-1/followup-history"
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["followup_count"] == 1
        assert data["history"][0]["draft_subject"] == "Follow-up: Engineer at Acme"
        assert data["last_followup_at"] == "2025-01-15T10:00:00+00:00"

    @pytest.mark.asyncio
    async def test_history_empty(self):
        """GET /followup-history returns empty when no sent followups."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_sess.execute.return_value = mock_result

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/applications/app-uuid-1/followup-history"
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["followup_count"] == 0
        assert data["history"] == []
        assert data["last_followup_at"] is None


# ---------------------------------------------------------------------------
# Test: POST /followups/{id}/mark-manual
# ---------------------------------------------------------------------------


class TestMarkManual:
    @pytest.mark.asyncio
    async def test_mark_manual_success(self):
        """POST /followups/{id}/mark-manual marks as sent+dismissed."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_sess.execute.return_value = mock_result

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/applications/followups/sugg-uuid-1/mark-manual"
                )

        assert resp.status_code == 200
        assert resp.json()["status"] == "marked_manual"

    @pytest.mark.asyncio
    async def test_mark_manual_not_found(self):
        """POST /followups/{id}/mark-manual returns 404 when not found."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_sess.execute.return_value = mock_result

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/applications/followups/nonexistent/mark-manual"
                )

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test: GET /followups includes followup_count
# ---------------------------------------------------------------------------


class TestFollowupCountInList:
    @pytest.mark.asyncio
    async def test_list_includes_followup_count(self):
        """GET /followups includes followup_count per suggestion."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: {
            "id": "sugg-uuid-1",
            "application_id": "app-uuid-1",
            "company": "Acme",
            "job_title": "Engineer",
            "status": "applied",
            "followup_date": "2025-01-15T00:00:00+00:00",
            "draft_subject": "Follow-up",
            "draft_body": "Hello",
            "created_at": "2025-01-10T00:00:00+00:00",
            "followup_count": 3,
        }[key]

        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [mock_row]
        mock_sess.execute.return_value = mock_result

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/applications/followups")

        assert resp.status_code == 200
        data = resp.json()
        assert data["suggestions"][0]["followup_count"] == 3
