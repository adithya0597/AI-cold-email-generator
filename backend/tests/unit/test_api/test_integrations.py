"""Tests for Integration API endpoints (Story 6-2, Task 2).

Covers: auth URL endpoint, callback endpoint, status endpoint,
disconnect endpoint, and error handling.
"""

from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# Test: Auth URL endpoint (AC1)
# ---------------------------------------------------------------------------


class TestGmailAuthUrl:
    """Tests for GET /integrations/gmail/auth-url."""

    @pytest.mark.asyncio
    async def test_returns_auth_url(self):
        """Endpoint returns a Google OAuth URL."""
        with patch(
            "app.services.gmail_service.build_auth_url",
            return_value="https://accounts.google.com/o/oauth2/v2/auth?test=1",
        ):
            from app.api.v1.integrations import get_gmail_auth_url

            result = await get_gmail_auth_url(user_id="user123")

        assert "accounts.google.com" in result.auth_url


# ---------------------------------------------------------------------------
# Test: Callback endpoint (AC2)
# ---------------------------------------------------------------------------


class TestGmailCallback:
    """Tests for POST /integrations/gmail/callback."""

    @pytest.mark.asyncio
    async def test_callback_stores_connection(self):
        """Callback exchanges code and stores connection."""
        mock_tokens = {
            "access_token": "ya29.test",
            "refresh_token": "1//test",
            "expires_in": 3600,
        }

        with (
            patch("app.services.gmail_service.exchange_code_for_tokens", new_callable=AsyncMock, return_value=mock_tokens),
            patch("app.services.gmail_service.get_user_email", new_callable=AsyncMock, return_value="test@gmail.com"),
            patch("app.services.gmail_service.store_connection", new_callable=AsyncMock, return_value="conn-uuid-123"),
        ):
            from app.api.v1.integrations import CallbackRequest, gmail_oauth_callback

            result = await gmail_oauth_callback(
                body=CallbackRequest(code="auth-code-123"),
                user_id="user123",
            )

        assert result.connection_id == "conn-uuid-123"
        assert result.email_address == "test@gmail.com"
        assert result.status == "active"

    @pytest.mark.asyncio
    async def test_callback_bad_code_returns_400(self):
        """Callback with bad code returns 400."""
        with patch(
            "app.services.gmail_service.exchange_code_for_tokens",
            new_callable=AsyncMock,
            side_effect=ValueError("Token exchange failed: 400"),
        ):
            from app.api.v1.integrations import CallbackRequest, gmail_oauth_callback

            with pytest.raises(Exception) as exc_info:
                await gmail_oauth_callback(
                    body=CallbackRequest(code="bad-code"),
                    user_id="user123",
                )

            assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Test: Status endpoint (AC3)
# ---------------------------------------------------------------------------


class TestGmailStatus:
    """Tests for GET /integrations/gmail/status."""

    @pytest.mark.asyncio
    async def test_returns_connected_status(self):
        """Returns connected=True with details when connected."""
        mock_conn = {
            "id": "conn-uuid",
            "email_address": "test@gmail.com",
            "status": "active",
            "connected_at": "2026-02-01T00:00:00+00:00",
            "last_sync_at": None,
        }

        with patch("app.services.gmail_service.get_connection_status", new_callable=AsyncMock, return_value=mock_conn):
            from app.api.v1.integrations import get_gmail_status

            result = await get_gmail_status(user_id="user123")

        assert result.connected is True
        assert result.email_address == "test@gmail.com"

    @pytest.mark.asyncio
    async def test_returns_not_connected(self):
        """Returns connected=False when no connection."""
        with patch("app.services.gmail_service.get_connection_status", new_callable=AsyncMock, return_value=None):
            from app.api.v1.integrations import get_gmail_status

            result = await get_gmail_status(user_id="user123")

        assert result.connected is False
        assert result.email_address is None


# ---------------------------------------------------------------------------
# Test: Disconnect endpoint (AC4)
# ---------------------------------------------------------------------------


class TestGmailDisconnect:
    """Tests for POST /integrations/gmail/disconnect."""

    @pytest.mark.asyncio
    async def test_disconnect_success(self):
        """Disconnect returns disconnected=True."""
        with patch("app.services.gmail_service.disconnect", new_callable=AsyncMock, return_value=True):
            from app.api.v1.integrations import disconnect_gmail

            result = await disconnect_gmail(user_id="user123")

        assert result.disconnected is True

    @pytest.mark.asyncio
    async def test_disconnect_no_connection_returns_404(self):
        """Disconnect returns 404 when no connection found."""
        with patch("app.services.gmail_service.disconnect", new_callable=AsyncMock, return_value=False):
            from app.api.v1.integrations import disconnect_gmail

            with pytest.raises(Exception) as exc_info:
                await disconnect_gmail(user_id="user123")

            assert exc_info.value.status_code == 404
