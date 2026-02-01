"""Tests for app.observability.error_tracking module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.observability.error_tracking import (
    _before_send,
    capture_error,
    configure_sentry_scope,
)


# ---------------------------------------------------------------------------
# TestBeforeSend
# ---------------------------------------------------------------------------


class TestBeforeSend:
    """Tests for the _before_send Sentry callback."""

    def test_scrubs_pii_from_user_context(self) -> None:
        event = {
            "user": {"id": "user_123", "email": "alice@example.com", "name": "Alice"},
        }
        result = _before_send(event, {})
        assert result["user"] == {"id": "user_123"}
        assert "email" not in result["user"]
        assert "name" not in result["user"]

    def test_keeps_user_id_only(self) -> None:
        event = {"user": {"id": "user_456"}}
        result = _before_send(event, {})
        assert result["user"] == {"id": "user_456"}

    def test_handles_no_user_key(self) -> None:
        event = {"message": "something happened"}
        result = _before_send(event, {})
        assert "user" not in result
        assert result["message"] == "something happened"

    def test_scrubs_ip_address(self) -> None:
        event = {"user": {"id": "u1", "ip_address": "1.2.3.4"}}
        result = _before_send(event, {})
        assert result["user"] == {"id": "u1"}

    def test_fingerprints_rate_limit_error(self) -> None:
        event = {
            "exception": {
                "values": [{"type": "RateLimitError", "value": "too many"}],
            },
        }
        result = _before_send(event, {})
        assert result["fingerprint"] == ["RateLimitError"]

    def test_fingerprints_web_scraping_error(self) -> None:
        event = {
            "exception": {
                "values": [{"type": "WebScrapingError", "value": "timeout"}],
            },
        }
        result = _before_send(event, {})
        assert result["fingerprint"] == ["WebScrapingError"]

    def test_fingerprints_llm_generation_error(self) -> None:
        event = {
            "exception": {
                "values": [{"type": "LLMGenerationError", "value": "bad response"}],
            },
        }
        result = _before_send(event, {})
        assert result["fingerprint"] == ["LLMGenerationError"]

    def test_no_fingerprint_for_unknown_error(self) -> None:
        event = {
            "exception": {
                "values": [{"type": "ValueError", "value": "oops"}],
            },
        }
        result = _before_send(event, {})
        assert "fingerprint" not in result

    def test_handles_event_without_exception(self) -> None:
        event = {"message": "log message", "level": "info"}
        result = _before_send(event, {})
        assert "fingerprint" not in result
        assert result["message"] == "log message"

    def test_handles_empty_exception_values(self) -> None:
        event = {"exception": {"values": []}}
        result = _before_send(event, {})
        assert "fingerprint" not in result

    def test_user_without_id_returns_empty_dict(self) -> None:
        event = {"user": {"email": "x@y.com"}}
        result = _before_send(event, {})
        assert result["user"] == {}


# ---------------------------------------------------------------------------
# TestConfigureSentryScope
# ---------------------------------------------------------------------------


class TestConfigureSentryScope:
    """Tests for the configure_sentry_scope ASGI middleware."""

    @pytest.mark.asyncio
    async def test_sets_user_id_from_request_state(self) -> None:
        request = MagicMock()
        request.state.user_id = "user_abc"

        call_next = AsyncMock(return_value=MagicMock())

        with patch("app.observability.error_tracking.sentry_sdk") as mock_sdk:
            response = await configure_sentry_scope(request, call_next)

        mock_sdk.set_user.assert_any_call({"id": "user_abc"})
        # Should clear user context after request
        mock_sdk.set_user.assert_called_with(None)
        call_next.assert_awaited_once_with(request)
        assert response is not None

    @pytest.mark.asyncio
    async def test_handles_missing_user_id(self) -> None:
        request = MagicMock(spec=[])
        request.state = MagicMock(spec=[])  # no user_id attribute

        call_next = AsyncMock(return_value=MagicMock())

        with patch("app.observability.error_tracking.sentry_sdk") as mock_sdk:
            response = await configure_sentry_scope(request, call_next)

        # set_user should only be called with None (cleanup), not with a user dict
        mock_sdk.set_user.assert_called_once_with(None)
        call_next.assert_awaited_once_with(request)
        assert response is not None

    @pytest.mark.asyncio
    async def test_calls_next_middleware(self) -> None:
        request = MagicMock()
        request.state.user_id = "u1"

        sentinel = MagicMock()
        call_next = AsyncMock(return_value=sentinel)

        with patch("app.observability.error_tracking.sentry_sdk"):
            result = await configure_sentry_scope(request, call_next)

        assert result is sentinel

    @pytest.mark.asyncio
    async def test_clears_user_on_exception(self) -> None:
        """User context is cleared even when call_next raises."""
        request = MagicMock()
        request.state.user_id = "u1"

        call_next = AsyncMock(side_effect=RuntimeError("boom"))

        with patch("app.observability.error_tracking.sentry_sdk") as mock_sdk:
            with pytest.raises(RuntimeError, match="boom"):
                await configure_sentry_scope(request, call_next)

        mock_sdk.set_user.assert_called_with(None)


# ---------------------------------------------------------------------------
# TestCaptureError
# ---------------------------------------------------------------------------


class TestCaptureError:
    """Tests for the capture_error helper."""

    def test_captures_exception_with_context(self) -> None:
        exc = ValueError("test error")

        with patch("app.observability.error_tracking.sentry_sdk") as mock_sdk:
            mock_scope = MagicMock()
            mock_sdk.push_scope.return_value.__enter__ = MagicMock(
                return_value=mock_scope
            )
            mock_sdk.push_scope.return_value.__exit__ = MagicMock(return_value=False)
            mock_sdk.capture_exception.return_value = "event_id_123"

            result = capture_error(exc, agent_type="scout", request_path="/api/v1/jobs")

        mock_scope.set_extra.assert_any_call("agent_type", "scout")
        mock_scope.set_extra.assert_any_call("request_path", "/api/v1/jobs")
        mock_sdk.capture_exception.assert_called_once_with(exc)
        assert result == "event_id_123"

    def test_handles_sentry_not_configured(self) -> None:
        exc = RuntimeError("no sentry")

        with patch(
            "app.observability.error_tracking.sentry_sdk"
        ) as mock_sdk:
            mock_sdk.push_scope.side_effect = Exception("SDK not init")

            result = capture_error(exc)

        assert result is None

    def test_attaches_agent_type_context(self) -> None:
        exc = ValueError("test")

        with patch("app.observability.error_tracking.sentry_sdk") as mock_sdk:
            mock_scope = MagicMock()
            mock_sdk.push_scope.return_value.__enter__ = MagicMock(
                return_value=mock_scope
            )
            mock_sdk.push_scope.return_value.__exit__ = MagicMock(return_value=False)
            mock_sdk.capture_exception.return_value = "eid"

            capture_error(exc, agent_type="apply")

        mock_scope.set_extra.assert_called_once_with("agent_type", "apply")


# ---------------------------------------------------------------------------
# TestSentryInitIntegration
# ---------------------------------------------------------------------------


class TestSentryInitIntegration:
    """Tests for before_send integration with sentry_sdk.init."""

    def test_before_send_passed_to_init(self) -> None:
        with (
            patch("app.observability.tracing.sentry_sdk") as mock_sdk,
            patch("app.observability.tracing.settings") as mock_settings,
        ):
            mock_settings.SENTRY_DSN = "https://examplePublicKey@o0.ingest.sentry.io/0"
            mock_settings.APP_ENV = "production"

            from app.observability.tracing import _init_sentry

            _init_sentry()

        mock_sdk.init.assert_called_once()
        call_kwargs = mock_sdk.init.call_args[1]
        assert call_kwargs["before_send"] is _before_send
