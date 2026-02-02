"""Tests for follow-up draft management API endpoints (Story 6-8).

Covers: update draft, send followup, send not-found.
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
# Test: PATCH /followups/{id}/draft
# ---------------------------------------------------------------------------


class TestUpdateDraft:
    @pytest.mark.asyncio
    async def test_update_draft_success(self):
        """PATCH /followups/{id}/draft updates subject and body."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_sess.execute.return_value = mock_result

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/applications/followups/sugg-uuid-1/draft",
                    json={"draft_subject": "New Subject", "draft_body": "New Body"},
                )

        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"

    @pytest.mark.asyncio
    async def test_update_draft_not_found(self):
        """PATCH /followups/{id}/draft returns 404 when suggestion not found."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_sess.execute.return_value = mock_result

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/applications/followups/nonexistent/draft",
                    json={"draft_subject": "Updated"},
                )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_draft_empty_body_returns_400(self):
        """PATCH /followups/{id}/draft returns 400 when no fields provided."""
        mock_cm, _mock_sess = _mock_session_cm()

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/applications/followups/sugg-uuid-1/draft",
                    json={},
                )

        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Test: POST /followups/{id}/send
# ---------------------------------------------------------------------------


class TestSendFollowup:
    @pytest.mark.asyncio
    async def test_send_success(self):
        """POST /followups/{id}/send marks suggestion as sent."""
        mock_cm, mock_sess = _mock_session_cm()

        # First execute returns the row (SELECT)
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: {
            "id": "sugg-uuid-1",
            "draft_subject": "Follow-up",
            "draft_body": "Hello",
        }[key]

        mock_select_result = MagicMock()
        mock_select_result.mappings.return_value.first.return_value = mock_row

        mock_update_result = MagicMock()

        mock_sess.execute.side_effect = [mock_select_result, mock_update_result]

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/applications/followups/sugg-uuid-1/send"
                )

        assert resp.status_code == 200
        assert resp.json()["status"] == "sent"

    @pytest.mark.asyncio
    async def test_send_not_found(self):
        """POST /followups/{id}/send returns 404 when not found."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_select_result = MagicMock()
        mock_select_result.mappings.return_value.first.return_value = None
        mock_sess.execute.return_value = mock_select_result

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/applications/followups/nonexistent/send"
                )

        assert resp.status_code == 404
