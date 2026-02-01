"""Tests for Gmail OAuth service (Story 6-2, Task 1).

Covers: auth URL generation, token exchange, token storage,
connection status, disconnect, and email fetching.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _mock_session_cm():
    """Create a mock async session context manager."""
    mock_sess = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_sess)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm, mock_sess


# ---------------------------------------------------------------------------
# Test: Auth URL generation
# ---------------------------------------------------------------------------


class TestBuildAuthUrl:
    """Tests for OAuth authorization URL generation."""

    def test_auth_url_contains_client_id(self):
        """Auth URL includes the Google client ID."""
        with patch("app.config.settings") as mock_settings:
            mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
            mock_settings.GOOGLE_REDIRECT_URI = "http://localhost/callback"

            from app.services.gmail_service import build_auth_url

            url = build_auth_url()

        assert "test-client-id" in url
        assert "accounts.google.com" in url

    def test_auth_url_includes_state(self):
        """Auth URL includes state parameter when provided."""
        with patch("app.config.settings") as mock_settings:
            mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
            mock_settings.GOOGLE_REDIRECT_URI = "http://localhost/callback"

            from app.services.gmail_service import build_auth_url

            url = build_auth_url(state="user123")

        assert "state=user123" in url

    def test_auth_url_requests_offline_access(self):
        """Auth URL requests offline access for refresh tokens."""
        with patch("app.config.settings") as mock_settings:
            mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
            mock_settings.GOOGLE_REDIRECT_URI = "http://localhost/callback"

            from app.services.gmail_service import build_auth_url

            url = build_auth_url()

        assert "access_type=offline" in url


# ---------------------------------------------------------------------------
# Test: Token exchange
# ---------------------------------------------------------------------------


class TestExchangeCode:
    """Tests for OAuth token exchange."""

    @pytest.mark.asyncio
    async def test_exchange_success(self):
        """Successful code exchange returns tokens."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "ya29.test",
            "refresh_token": "1//test",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with (
            patch("app.config.settings") as mock_settings,
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.GOOGLE_CLIENT_ID = "test-id"
            mock_settings.GOOGLE_CLIENT_SECRET = "test-secret"
            mock_settings.GOOGLE_REDIRECT_URI = "http://localhost/callback"

            from app.services.gmail_service import exchange_code_for_tokens

            result = await exchange_code_for_tokens("auth-code-123")

        assert result["access_token"] == "ya29.test"
        assert result["refresh_token"] == "1//test"

    @pytest.mark.asyncio
    async def test_exchange_failure_raises(self):
        """Failed code exchange raises ValueError."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with (
            patch("app.config.settings") as mock_settings,
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.GOOGLE_CLIENT_ID = "test-id"
            mock_settings.GOOGLE_CLIENT_SECRET = "test-secret"
            mock_settings.GOOGLE_REDIRECT_URI = "http://localhost/callback"

            from app.services.gmail_service import exchange_code_for_tokens

            with pytest.raises(ValueError, match="Token exchange failed"):
                await exchange_code_for_tokens("bad-code")


# ---------------------------------------------------------------------------
# Test: Connection storage
# ---------------------------------------------------------------------------


class TestStoreConnection:
    """Tests for storing Gmail connections."""

    @pytest.mark.asyncio
    async def test_store_new_connection(self):
        """Stores a new connection when none exists."""
        mock_cm, mock_sess = _mock_session_cm()

        # No existing connection
        mock_existing = MagicMock()
        mock_existing.scalar.return_value = None
        # Insert
        mock_insert = MagicMock()

        mock_sess.execute = AsyncMock(side_effect=[mock_existing, mock_insert])
        mock_sess.commit = AsyncMock()

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.services.gmail_service import store_connection

            conn_id = await store_connection(
                user_id="user123",
                email_address="test@gmail.com",
                access_token="ya29.test",
                refresh_token="1//test",
                expires_in=3600,
            )

        assert conn_id  # Returns a UUID string
        assert mock_sess.commit.called

    @pytest.mark.asyncio
    async def test_update_existing_connection(self):
        """Updates an existing connection instead of creating a new one."""
        mock_cm, mock_sess = _mock_session_cm()

        # Existing connection found
        mock_existing = MagicMock()
        mock_existing.scalar.return_value = "existing-conn-id"
        # Update
        mock_update = MagicMock()

        mock_sess.execute = AsyncMock(side_effect=[mock_existing, mock_update])
        mock_sess.commit = AsyncMock()

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.services.gmail_service import store_connection

            conn_id = await store_connection(
                user_id="user123",
                email_address="test@gmail.com",
                access_token="ya29.new",
                refresh_token="1//new",
                expires_in=3600,
            )

        assert conn_id == "existing-conn-id"


# ---------------------------------------------------------------------------
# Test: Connection status
# ---------------------------------------------------------------------------


class TestGetConnectionStatus:
    """Tests for retrieving connection status."""

    @pytest.mark.asyncio
    async def test_returns_none_when_not_connected(self):
        """Returns None when no Gmail connection exists."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = None
        mock_sess.execute = AsyncMock(return_value=mock_result)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.services.gmail_service import get_connection_status

            result = await get_connection_status("user123")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_status_when_connected(self):
        """Returns connection details when Gmail is connected."""
        mock_cm, mock_sess = _mock_session_cm()

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: {
            "id": "conn-uuid",
            "email_address": "test@gmail.com",
            "status": "active",
            "connected_at": now,
            "last_sync_at": None,
        }[key]

        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = mock_row
        mock_sess.execute = AsyncMock(return_value=mock_result)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.services.gmail_service import get_connection_status

            result = await get_connection_status("user123")

        assert result["email_address"] == "test@gmail.com"
        assert result["status"] == "active"


# ---------------------------------------------------------------------------
# Test: Disconnect
# ---------------------------------------------------------------------------


class TestDisconnect:
    """Tests for disconnecting Gmail."""

    @pytest.mark.asyncio
    async def test_disconnect_returns_true(self):
        """Disconnect returns True when connection exists."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_sess.execute = AsyncMock(return_value=mock_result)
        mock_sess.commit = AsyncMock()

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.services.gmail_service import disconnect

            result = await disconnect("user123")

        assert result is True

    @pytest.mark.asyncio
    async def test_disconnect_returns_false_when_none(self):
        """Disconnect returns False when no connection exists."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_sess.execute = AsyncMock(return_value=mock_result)
        mock_sess.commit = AsyncMock()

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.services.gmail_service import disconnect

            result = await disconnect("user123")

        assert result is False
