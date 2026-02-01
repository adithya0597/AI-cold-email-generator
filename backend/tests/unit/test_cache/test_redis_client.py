"""
Tests for Story 0.5: Centralized Redis client with connection pooling.

Validates:
  AC#1 - Redis health check
  AC#2 - Cache operations with TTL
  AC#4 - Connection pooling
  AC#6 - Graceful degradation (health check returns False on failure)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.cache import redis_client


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture(autouse=True)
def reset_pool():
    """Reset the module-level pool before each test."""
    redis_client._pool = None
    yield
    redis_client._pool = None


# ============================================================
# AC#4 - Connection Pooling
# ============================================================


class TestConnectionPooling:
    """AC#4: Connection pooling is configured for performance."""

    @pytest.mark.asyncio
    @patch("app.cache.redis_client.redis.ConnectionPool.from_url")
    async def test_get_redis_pool_creates_pool(self, mock_from_url):
        mock_pool = MagicMock()
        mock_from_url.return_value = mock_pool

        pool = await redis_client.get_redis_pool()

        mock_from_url.assert_called_once_with(
            "redis://localhost:6379/0",
            max_connections=20,
            decode_responses=True,
        )
        assert pool is mock_pool

    @pytest.mark.asyncio
    @patch("app.cache.redis_client.redis.ConnectionPool.from_url")
    async def test_get_redis_pool_reuses_pool(self, mock_from_url):
        mock_pool = MagicMock()
        mock_from_url.return_value = mock_pool

        pool1 = await redis_client.get_redis_pool()
        pool2 = await redis_client.get_redis_pool()

        assert pool1 is pool2
        # from_url should only be called once (pool is reused)
        mock_from_url.assert_called_once()


# ============================================================
# AC#2 - Cache Operations with TTL
# ============================================================


class TestCacheOperations:
    """AC#2: Cache operations with configurable TTL."""

    @pytest.mark.asyncio
    @patch("app.cache.redis_client.get_redis_client")
    async def test_cache_set_with_ttl(self, mock_get_client):
        mock_redis = AsyncMock()
        mock_get_client.return_value = mock_redis

        await redis_client.cache_set("test:key", "test-value", ttl=600)

        mock_redis.set.assert_awaited_once_with("test:key", "test-value", ex=600)

    @pytest.mark.asyncio
    @patch("app.cache.redis_client.get_redis_client")
    async def test_cache_set_default_ttl(self, mock_get_client):
        mock_redis = AsyncMock()
        mock_get_client.return_value = mock_redis

        await redis_client.cache_set("test:key", "test-value")

        mock_redis.set.assert_awaited_once_with("test:key", "test-value", ex=300)

    @pytest.mark.asyncio
    @patch("app.cache.redis_client.get_redis_client")
    async def test_cache_get_returns_value(self, mock_get_client):
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "cached-value"
        mock_get_client.return_value = mock_redis

        result = await redis_client.cache_get("test:key")

        assert result == "cached-value"
        mock_redis.get.assert_awaited_once_with("test:key")

    @pytest.mark.asyncio
    @patch("app.cache.redis_client.get_redis_client")
    async def test_cache_get_miss_returns_none(self, mock_get_client):
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_get_client.return_value = mock_redis

        result = await redis_client.cache_get("nonexistent:key")

        assert result is None

    @pytest.mark.asyncio
    @patch("app.cache.redis_client.get_redis_client")
    async def test_cache_delete(self, mock_get_client):
        mock_redis = AsyncMock()
        mock_get_client.return_value = mock_redis

        await redis_client.cache_delete("test:key")

        mock_redis.delete.assert_awaited_once_with("test:key")


# ============================================================
# AC#1 - Redis Health Check
# ============================================================


class TestHealthCheck:
    """AC#1 & AC#6: Health check and graceful degradation."""

    @pytest.mark.asyncio
    @patch("app.cache.redis_client.get_redis_client")
    async def test_redis_health_check_healthy(self, mock_get_client):
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_get_client.return_value = mock_redis

        result = await redis_client.redis_health_check()

        assert result is True
        mock_redis.ping.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.cache.redis_client.get_redis_client")
    async def test_redis_health_check_unhealthy(self, mock_get_client):
        """AC#6: Graceful degradation when Redis is unavailable."""
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = ConnectionError("Redis unavailable")
        mock_get_client.return_value = mock_redis

        result = await redis_client.redis_health_check()

        assert result is False


# ============================================================
# Pool Lifecycle
# ============================================================


class TestPoolLifecycle:
    """Connection pool shutdown and cleanup."""

    @pytest.mark.asyncio
    @patch("app.cache.redis_client.redis.ConnectionPool.from_url")
    async def test_close_redis_pool(self, mock_from_url):
        mock_pool = AsyncMock()
        mock_from_url.return_value = mock_pool

        # Create pool first
        await redis_client.get_redis_pool()
        assert redis_client._pool is not None

        # Close it
        await redis_client.close_redis_pool()

        mock_pool.disconnect.assert_awaited_once()
        assert redis_client._pool is None

    @pytest.mark.asyncio
    async def test_close_redis_pool_noop_when_none(self):
        """Closing when no pool exists should not raise."""
        assert redis_client._pool is None
        await redis_client.close_redis_pool()
        assert redis_client._pool is None
