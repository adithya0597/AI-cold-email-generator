"""Tests for Outlook OAuth service (Story 6-3).

Covers: auth URL, token exchange, connection storage, status, disconnect.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_session_cm():
    mock_sess = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_sess)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm, mock_sess


class TestOutlookAuthUrl:
    def test_auth_url_contains_microsoft(self):
        with patch("app.config.settings") as s:
            s.MICROSOFT_CLIENT_ID = "ms-client-id"
            s.MICROSOFT_REDIRECT_URI = "http://localhost/callback"
            from app.services.outlook_service import build_auth_url
            url = build_auth_url()
        assert "login.microsoftonline.com" in url
        assert "ms-client-id" in url

    def test_auth_url_includes_state(self):
        with patch("app.config.settings") as s:
            s.MICROSOFT_CLIENT_ID = "ms-client-id"
            s.MICROSOFT_REDIRECT_URI = "http://localhost/callback"
            from app.services.outlook_service import build_auth_url
            url = build_auth_url(state="user123")
        assert "state=user123" in url


class TestOutlookExchangeCode:
    @pytest.mark.asyncio
    async def test_exchange_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "eyJ.test",
            "refresh_token": "0.test",
            "expires_in": 3600,
        }
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with (
            patch("app.config.settings") as s,
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            s.MICROSOFT_CLIENT_ID = "ms-id"
            s.MICROSOFT_CLIENT_SECRET = "ms-secret"
            s.MICROSOFT_REDIRECT_URI = "http://localhost/callback"
            from app.services.outlook_service import exchange_code_for_tokens
            result = await exchange_code_for_tokens("auth-code")
        assert result["access_token"] == "eyJ.test"

    @pytest.mark.asyncio
    async def test_exchange_failure_raises(self):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with (
            patch("app.config.settings") as s,
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            s.MICROSOFT_CLIENT_ID = "ms-id"
            s.MICROSOFT_CLIENT_SECRET = "ms-secret"
            s.MICROSOFT_REDIRECT_URI = "http://localhost/callback"
            from app.services.outlook_service import exchange_code_for_tokens
            with pytest.raises(ValueError):
                await exchange_code_for_tokens("bad-code")


class TestOutlookStoreConnection:
    @pytest.mark.asyncio
    async def test_store_new_connection(self):
        mock_cm, mock_sess = _mock_session_cm()
        mock_existing = MagicMock()
        mock_existing.scalar.return_value = None
        mock_sess.execute = AsyncMock(side_effect=[mock_existing, MagicMock()])
        mock_sess.commit = AsyncMock()

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.services.outlook_service import store_connection
            conn_id = await store_connection("user123", "test@outlook.com", "token", "refresh", 3600)
        assert conn_id


class TestOutlookStatus:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_connected(self):
        mock_cm, mock_sess = _mock_session_cm()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = None
        mock_sess.execute = AsyncMock(return_value=mock_result)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.services.outlook_service import get_connection_status
            result = await get_connection_status("user123")
        assert result is None


class TestOutlookDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect_returns_true(self):
        mock_cm, mock_sess = _mock_session_cm()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_sess.execute = AsyncMock(return_value=mock_result)
        mock_sess.commit = AsyncMock()

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.services.outlook_service import disconnect
            result = await disconnect("user123")
        assert result is True


class TestOutlookEndpoints:
    @pytest.mark.asyncio
    async def test_auth_url_endpoint(self):
        with patch(
            "app.services.outlook_service.build_auth_url",
            return_value="https://login.microsoftonline.com/common/oauth2/v2.0/authorize?test=1",
        ):
            from app.api.v1.integrations import get_outlook_auth_url
            result = await get_outlook_auth_url(user_id="user123")
        assert "microsoftonline.com" in result.auth_url

    @pytest.mark.asyncio
    async def test_outlook_callback(self):
        mock_tokens = {"access_token": "eyJ.test", "refresh_token": "0.test", "expires_in": 3600}
        with (
            patch("app.services.outlook_service.exchange_code_for_tokens", new_callable=AsyncMock, return_value=mock_tokens),
            patch("app.services.outlook_service.get_user_email", new_callable=AsyncMock, return_value="test@outlook.com"),
            patch("app.services.outlook_service.store_connection", new_callable=AsyncMock, return_value="conn-uuid"),
        ):
            from app.api.v1.integrations import CallbackRequest, outlook_oauth_callback
            result = await outlook_oauth_callback(body=CallbackRequest(code="code"), user_id="user123")
        assert result.connection_id == "conn-uuid"
        assert result.email_address == "test@outlook.com"

    @pytest.mark.asyncio
    async def test_outlook_status_not_connected(self):
        with patch("app.services.outlook_service.get_connection_status", new_callable=AsyncMock, return_value=None):
            from app.api.v1.integrations import get_outlook_status
            result = await get_outlook_status(user_id="user123")
        assert result.connected is False

    @pytest.mark.asyncio
    async def test_outlook_disconnect_404(self):
        with patch("app.services.outlook_service.disconnect", new_callable=AsyncMock, return_value=False):
            from app.api.v1.integrations import disconnect_outlook
            with pytest.raises(Exception) as exc_info:
                await disconnect_outlook(user_id="user123")
            assert exc_info.value.status_code == 404
