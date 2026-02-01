"""
Tests for Story 0.5: Pub/sub utility for agent control channels.

Validates:
  AC#5 - Pub/sub agent control channels (pause, resume, status)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.cache.pubsub import (
    AGENT_PAUSE_CHANNEL,
    AGENT_RESUME_CHANNEL,
    AGENT_STATUS_CHANNEL,
    format_channel,
    publish_control_event,
    subscribe_control_channel,
)


# ============================================================
# Channel Formatting
# ============================================================


class TestFormatChannel:
    """Channel templates substitute user_id correctly."""

    def test_format_pause_channel(self):
        result = format_channel(AGENT_PAUSE_CHANNEL, "user-123")
        assert result == "agent:pause:user-123"

    def test_format_resume_channel(self):
        result = format_channel(AGENT_RESUME_CHANNEL, "user-456")
        assert result == "agent:resume:user-456"

    def test_format_status_channel(self):
        result = format_channel(AGENT_STATUS_CHANNEL, "user-789")
        assert result == "agent:status:user-789"

    def test_format_with_uuid(self):
        uid = "550e8400-e29b-41d4-a716-446655440000"
        result = format_channel(AGENT_PAUSE_CHANNEL, uid)
        assert result == f"agent:pause:{uid}"


# ============================================================
# AC#5 - Publish Control Event
# ============================================================


class TestPublishControlEvent:
    """AC#5: Messages are published on correct channels."""

    @pytest.mark.asyncio
    @patch("app.cache.pubsub.get_redis_client")
    async def test_publish_control_event(self, mock_get_client):
        mock_redis = AsyncMock()
        mock_redis.publish.return_value = 1
        mock_get_client.return_value = mock_redis

        result = await publish_control_event(
            AGENT_PAUSE_CHANNEL, "user-123", '{"action": "pause"}'
        )

        mock_redis.publish.assert_awaited_once_with(
            "agent:pause:user-123", '{"action": "pause"}'
        )
        assert result == 1

    @pytest.mark.asyncio
    @patch("app.cache.pubsub.get_redis_client")
    async def test_publish_returns_subscriber_count(self, mock_get_client):
        mock_redis = AsyncMock()
        mock_redis.publish.return_value = 3
        mock_get_client.return_value = mock_redis

        result = await publish_control_event(
            AGENT_STATUS_CHANNEL, "user-abc", "status-update"
        )

        assert result == 3


# ============================================================
# AC#5 - Subscribe Control Channel
# ============================================================


class TestSubscribeControlChannel:
    """AC#5: Subscribes to correct formatted channel."""

    @pytest.mark.asyncio
    @patch("app.cache.pubsub.get_redis_client")
    async def test_subscribe_control_channel(self, mock_get_client):
        mock_redis = MagicMock()
        mock_pubsub = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_get_client.return_value = mock_redis

        result = await subscribe_control_channel(
            AGENT_RESUME_CHANNEL, "user-456"
        )

        mock_pubsub.subscribe.assert_awaited_once_with("agent:resume:user-456")
        assert result is mock_pubsub
