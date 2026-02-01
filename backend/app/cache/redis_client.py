"""
Centralized async Redis client with connection pooling.

Provides a shared connection pool, cache get/set with TTL,
health check, and graceful shutdown. All Redis-dependent modules
should use this instead of creating their own connections.
"""

import redis.asyncio as redis

from app.config import settings

_pool: redis.ConnectionPool | None = None


async def get_redis_pool() -> redis.ConnectionPool:
    """Get or create the shared connection pool."""
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=20,
            decode_responses=True,
        )
    return _pool


async def get_redis_client() -> redis.Redis:
    """Get an async Redis client from the shared pool."""
    pool = await get_redis_pool()
    return redis.Redis(connection_pool=pool)


async def cache_get(key: str) -> str | None:
    """Get a value from cache."""
    client = await get_redis_client()
    return await client.get(key)


async def cache_set(key: str, value: str, ttl: int = 300) -> None:
    """Set a value in cache with TTL (seconds)."""
    client = await get_redis_client()
    await client.set(key, value, ex=ttl)


async def cache_delete(key: str) -> None:
    """Delete a key from cache."""
    client = await get_redis_client()
    await client.delete(key)


async def redis_health_check() -> bool:
    """Check Redis connectivity. Returns True if healthy."""
    try:
        client = await get_redis_client()
        return await client.ping()
    except Exception:
        return False


async def close_redis_pool() -> None:
    """Close the connection pool on app shutdown."""
    global _pool
    if _pool is not None:
        await _pool.disconnect()
        _pool = None
