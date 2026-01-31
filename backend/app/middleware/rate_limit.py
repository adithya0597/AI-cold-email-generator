"""
Rate limiting middleware for the JobPilot API.

Strategy:
  - Uses a sliding-window counter per client IP (or per user_id when
    authenticated).
  - Stores counters in Redis when available; falls back to an in-memory
    dictionary so the app can run without Redis during development.
  - Two tiers: Free (100 req/hour) and Pro (1000 req/hour).  All
    requests currently default to Pro limits until user tier lookup is
    implemented in the database layer.

Wire into the FastAPI app via ``app.add_middleware(RateLimitMiddleware)``.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Dict, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tier configuration
# ---------------------------------------------------------------------------

TIER_LIMITS: Dict[str, int] = {
    "free": 100,   # requests per hour
    "pro": 1000,   # requests per hour
}

WINDOW_SECONDS = 3600  # 1 hour

# Paths that are never rate-limited (health checks, docs)
EXEMPT_PATHS: set = {
    "/api/v1/health",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


# ---------------------------------------------------------------------------
# In-memory fallback store
# ---------------------------------------------------------------------------

class _InMemoryStore:
    """Simple in-memory sliding-window counter.  NOT shared across workers."""

    def __init__(self) -> None:
        # key -> list of timestamps
        self._hits: Dict[str, list] = defaultdict(list)

    async def increment(self, key: str, window: int) -> int:
        now = time.time()
        cutoff = now - window
        # Prune expired entries
        self._hits[key] = [t for t in self._hits[key] if t > cutoff]
        self._hits[key].append(now)
        return len(self._hits[key])


# ---------------------------------------------------------------------------
# Redis store
# ---------------------------------------------------------------------------

class _RedisStore:
    """Sliding-window counter backed by Redis sorted sets."""

    def __init__(self) -> None:
        self._client = None  # lazy init

    async def _get_client(self):
        if self._client is None:
            import redis.asyncio as aioredis

            self._client = aioredis.from_url(
                settings.REDIS_URL, socket_connect_timeout=2
            )
        return self._client

    async def increment(self, key: str, window: int) -> int:
        try:
            client = await self._get_client()
            now = time.time()
            cutoff = now - window
            redis_key = f"ratelimit:{key}"

            pipe = client.pipeline()
            pipe.zremrangebyscore(redis_key, 0, cutoff)
            pipe.zadd(redis_key, {str(now): now})
            pipe.zcard(redis_key)
            pipe.expire(redis_key, window + 60)  # TTL slightly longer than window
            results = await pipe.execute()
            return results[2]  # zcard result
        except Exception as exc:
            logger.debug("Redis rate-limit failed, falling back to in-memory: %s", exc)
            return -1  # signal to caller to use fallback


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class RateLimitMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that enforces per-client request rate limits."""

    def __init__(self, app, **kwargs) -> None:  # type: ignore[override]
        super().__init__(app, **kwargs)
        self._redis_store = _RedisStore()
        self._memory_store = _InMemoryStore()

    def _get_client_key(self, request: Request) -> str:
        """Derive a rate-limit key from the request.

        Prefers user_id from a previously-decoded JWT (set by Clerk
        middleware on ``request.state``).  Falls back to client IP.
        """
        user_id: Optional[str] = getattr(request.state, "user_id", None) if hasattr(request, "state") else None
        if user_id:
            return f"user:{user_id}"
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        client = request.client
        return f"ip:{client.host}" if client else "ip:unknown"

    def _get_tier(self, request: Request) -> str:
        """Determine the user's tier.

        TODO: Once user management is in the DB, look up the tier from
        the user record.  For now everyone gets Pro limits.
        """
        return "pro"

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip exempt paths
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        # Skip non-API paths (docs, static, etc.)
        if not request.url.path.startswith("/api"):
            return await call_next(request)

        key = self._get_client_key(request)
        tier = self._get_tier(request)
        limit = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

        # Try Redis first, fall back to in-memory
        count = await self._redis_store.increment(key, WINDOW_SECONDS)
        if count == -1:
            count = await self._memory_store.increment(key, WINDOW_SECONDS)

        # Set rate-limit headers on all responses
        remaining = max(0, limit - count)
        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(time.time()) + WINDOW_SECONDS),
        }

        if count > limit:
            retry_after = WINDOW_SECONDS  # worst case: full window
            headers["Retry-After"] = str(retry_after)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RateLimitExceeded",
                    "message": f"Rate limit exceeded. Limit: {limit} requests per hour.",
                    "detail": {"retry_after": retry_after},
                },
                headers=headers,
            )

        response = await call_next(request)

        # Attach rate-limit headers to successful responses too
        for header_name, header_value in headers.items():
            response.headers[header_name] = header_value

        return response
