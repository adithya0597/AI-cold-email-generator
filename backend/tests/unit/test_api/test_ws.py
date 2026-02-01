"""Tests for WebSocket infrastructure — auth, publishing, REST events."""
from __future__ import annotations

import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# TestValidateWsToken
# ---------------------------------------------------------------------------


class TestValidateWsToken:
    """Test WebSocket JWT validation (app.auth.ws_auth)."""

    @pytest.mark.asyncio
    async def test_returns_none_for_empty_token(self):
        from app.auth.ws_auth import validate_ws_token

        result = await validate_ws_token("")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_none_like_token(self):
        from app.auth.ws_auth import validate_ws_token

        result = await validate_ws_token("")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_clerk_domain_not_set(self):
        from app.auth.ws_auth import validate_ws_token

        with patch("app.auth.ws_auth.settings") as mock_settings:
            mock_settings.CLERK_DOMAIN = ""
            result = await validate_ws_token("some-token")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_user_id_for_valid_jwt(self):
        from app.auth.ws_auth import validate_ws_token

        mock_config_instance = MagicMock()
        mock_config_instance.decode.return_value = {"sub": "user_123"}
        mock_clerk_config = MagicMock(return_value=mock_config_instance)

        with patch("app.auth.ws_auth.settings") as mock_settings:
            mock_settings.CLERK_DOMAIN = "example.clerk.accounts.dev"
            with patch.dict("sys.modules", {"fastapi_clerk_auth": MagicMock(ClerkConfig=mock_clerk_config)}):
                result = await validate_ws_token("valid-jwt")
                assert result == "user_123"

    @pytest.mark.asyncio
    async def test_returns_none_for_invalid_jwt(self):
        from app.auth.ws_auth import validate_ws_token

        mock_config_instance = MagicMock()
        mock_config_instance.decode.side_effect = Exception("Invalid token")
        mock_clerk_config = MagicMock(return_value=mock_config_instance)

        with patch("app.auth.ws_auth.settings") as mock_settings:
            mock_settings.CLERK_DOMAIN = "example.clerk.accounts.dev"
            with patch.dict("sys.modules", {"fastapi_clerk_auth": MagicMock(ClerkConfig=mock_clerk_config)}):
                result = await validate_ws_token("bad-jwt")
                assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_sub_missing(self):
        from app.auth.ws_auth import validate_ws_token

        mock_config_instance = MagicMock()
        mock_config_instance.decode.return_value = {"iss": "clerk", "aud": "app"}
        mock_clerk_config = MagicMock(return_value=mock_config_instance)

        with patch("app.auth.ws_auth.settings") as mock_settings:
            mock_settings.CLERK_DOMAIN = "example.clerk.accounts.dev"
            with patch.dict("sys.modules", {"fastapi_clerk_auth": MagicMock(ClerkConfig=mock_clerk_config)}):
                result = await validate_ws_token("jwt-no-sub")
                assert result is None


# ---------------------------------------------------------------------------
# TestPublishAgentEvent
# ---------------------------------------------------------------------------


class TestPublishAgentEvent:
    """Test event publishing to Redis."""

    @pytest.mark.asyncio
    @patch("app.api.v1.ws._get_redis")
    async def test_publishes_to_correct_channel(self, mock_get_redis):
        from app.api.v1.ws import publish_agent_event

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        event = {"type": "agent.test.completed", "data": {"foo": "bar"}}
        await publish_agent_event("user_abc", event)

        mock_redis.publish.assert_called_once()
        args = mock_redis.publish.call_args[0]
        assert args[0] == "agent:status:user_abc"

    @pytest.mark.asyncio
    @patch("app.api.v1.ws._get_redis")
    async def test_publishes_json_payload(self, mock_get_redis):
        import json

        from app.api.v1.ws import publish_agent_event

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        event = {"type": "agent.scout.completed", "score": 85}
        await publish_agent_event("user_xyz", event)

        payload = mock_redis.publish.call_args[0][1]
        parsed = json.loads(payload)
        assert parsed["type"] == "agent.scout.completed"
        assert parsed["score"] == 85

    @pytest.mark.asyncio
    @patch("app.api.v1.ws._get_redis")
    async def test_handles_redis_failure_gracefully(self, mock_get_redis):
        from app.api.v1.ws import publish_agent_event

        mock_get_redis.side_effect = Exception("Redis down")

        # Should not raise
        await publish_agent_event("user_abc", {"type": "test"})

    @pytest.mark.asyncio
    @patch("app.api.v1.ws._get_redis")
    async def test_closes_redis_after_publish(self, mock_get_redis):
        from app.api.v1.ws import publish_agent_event

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        await publish_agent_event("user_1", {"type": "test"})
        mock_redis.aclose.assert_called_once()


# ---------------------------------------------------------------------------
# TestEventsEndpoint
# ---------------------------------------------------------------------------


class TestEventsEndpoint:
    """Test REST events fallback endpoint models."""

    def test_events_response_model(self):
        from app.api.v1.agents import EventItem, EventsResponse

        response = EventsResponse(
            events=[
                EventItem(
                    id="1",
                    event_type="agent.test",
                    title="Test Event",
                    severity="info",
                    data={},
                    timestamp="2026-02-01T00:00:00",
                )
            ],
            count=1,
        )
        assert response.count == 1
        assert response.events[0].event_type == "agent.test"

    def test_empty_events_response(self):
        from app.api.v1.agents import EventsResponse

        response = EventsResponse(events=[], count=0)
        assert response.count == 0
        assert response.events == []

    def test_event_item_optional_fields(self):
        from app.api.v1.agents import EventItem

        item = EventItem(
            id="2",
            event_type="agent.scout.completed",
            title="Scout done",
            severity="info",
            timestamp="2026-02-01T12:00:00",
        )
        assert item.agent_type is None
        assert item.data == {}

    def test_event_item_with_all_fields(self):
        from app.api.v1.agents import EventItem

        item = EventItem(
            id="3",
            event_type="agent.scout.completed",
            agent_type="scout",
            title="Found 5 jobs",
            severity="info",
            data={"jobs_found": 5},
            timestamp="2026-02-01T12:00:00",
        )
        assert item.agent_type == "scout"
        assert item.data["jobs_found"] == 5
