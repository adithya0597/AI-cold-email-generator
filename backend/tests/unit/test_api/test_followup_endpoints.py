"""Tests for follow-up suggestion API endpoints (Story 6-7).

Covers: list followups, dismiss followup, empty list, not found dismiss.
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
# Test: GET /followups
# ---------------------------------------------------------------------------


class TestListFollowups:
    @pytest.mark.asyncio
    async def test_list_returns_suggestions(self):
        """GET /followups returns pending suggestions."""
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
            "followup_count": 0,
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
        assert data["total"] == 1
        assert data["suggestions"][0]["company"] == "Acme"

    @pytest.mark.asyncio
    async def test_list_empty_returns_zero(self):
        """GET /followups returns empty list when no suggestions."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_sess.execute.return_value = mock_result

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/applications/followups")

        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["suggestions"] == []


# ---------------------------------------------------------------------------
# Test: PATCH /followups/{id}/dismiss
# ---------------------------------------------------------------------------


class TestDismissFollowup:
    @pytest.mark.asyncio
    async def test_dismiss_success(self):
        """PATCH /followups/{id}/dismiss marks suggestion as dismissed."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_sess.execute.return_value = mock_result

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch("/api/v1/applications/followups/sugg-uuid-1/dismiss")

        assert resp.status_code == 200
        assert resp.json()["status"] == "dismissed"

    @pytest.mark.asyncio
    async def test_dismiss_not_found_returns_404(self):
        """PATCH /followups/{id}/dismiss returns 404 when not found."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_sess.execute.return_value = mock_result

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch("/api/v1/applications/followups/nonexistent/dismiss")

        assert resp.status_code == 404
