# Story 0.5: Redis Cache and Queue Setup

Status: done

## Story

As a **system**,
I want **Redis configured for caching, job queuing, and real-time agent control**,
so that **agent tasks can be scheduled and emergency brake functions instantly**.

## Acceptance Criteria

1. **AC1 - Redis Connection & Health:** Given Redis is deployed and connected, when the health endpoint is called, then Redis connectivity status is included in the response.

2. **AC2 - Cache Operations with TTL:** Given Redis is connected, when a cache operation is performed, then data is stored with configurable TTL and retrievable before expiry.

3. **AC3 - Celery Broker Connectivity:** Given Redis is running, when Celery is configured, then Celery can connect to Redis as both broker and result backend.

4. **AC4 - Connection Pooling:** Given multiple concurrent requests, when Redis operations are performed, then connection pooling is configured for performance (no new connection per request).

5. **AC5 - Pub/Sub Agent Control Channels:** Given Redis pub/sub is configured, when agent control events occur, then messages are published/received on channels:
   - `agent:pause:{user_id}` - emergency brake signal
   - `agent:resume:{user_id}` - resume signal
   - `agent:status:{user_id}` - status updates

6. **AC6 - Graceful Degradation:** Given Redis becomes unavailable, when a cache-dependent operation is attempted, then the system degrades gracefully (e.g., rate limiter falls back to in-memory).

## Tasks / Subtasks

- [x] Task 1: Add dedicated Redis client utility with connection pooling and health check (AC: #1, #2, #4)
  - [x] 1.1: Create `backend/app/cache/redis_client.py` with async Redis client, connection pool, get/set with TTL, health check method
  - [x] 1.2: Add `get_redis()` dependency for FastAPI routes that need direct Redis access
  - [x] 1.3: Wire Redis client initialization into app lifespan (startup/shutdown pool management)

- [x] Task 2: Add pub/sub utility for agent control channels (AC: #5)
  - [x] 2.1: Create `backend/app/cache/pubsub.py` with `publish_control_event()` and `subscribe_control_channel()` helpers
  - [x] 2.2: Define channel constants: `AGENT_PAUSE`, `AGENT_RESUME`, `AGENT_STATUS` with `{user_id}` templating
  - [x] 2.3: Ensure existing `ws.py` pub/sub usage aligns with new channel constants

- [x] Task 3: Write comprehensive Redis tests (AC: #1-#6)
  - [x] 3.1: Create `backend/tests/unit/test_cache/__init__.py`
  - [x] 3.2: Create `backend/tests/unit/test_cache/test_redis_client.py` — test connection, get/set with TTL, health check, pool behavior
  - [x] 3.3: Create `backend/tests/unit/test_cache/test_pubsub.py` — test publish/subscribe on agent control channels
  - [x] 3.4: Create `backend/tests/unit/test_worker/test_celery_config.py` — test Celery uses Redis as broker, queue routing, reliability settings
  - [x] 3.5: Test graceful degradation when Redis is unavailable (rate limiter fallback)

## Dev Notes

### Architecture Compliance

**CRITICAL — Redis and Celery are ALREADY SUBSTANTIALLY IMPLEMENTED:**

1. **Redis config EXISTS:** `backend/app/config.py` has `REDIS_URL` setting. Default: `redis://localhost:6379/0`.
   [Source: backend/app/config.py:36]

2. **Celery + Redis broker EXISTS:** `backend/app/worker/celery_app.py` configures Celery with Redis as broker and result backend, JSON serialization, reliability settings, queue routing, RedBeat scheduler.
   [Source: backend/app/worker/celery_app.py]

3. **Celery tasks EXIST:** `backend/app/worker/tasks.py` has agent tasks (job_scout, resume, apply), briefing_generate, verify_brake_completion, cleanup_expired_approvals, health_check_task, example_task. All use lazy imports + asyncio.run() pattern.
   [Source: backend/app/worker/tasks.py]

4. **Rate limit Redis usage EXISTS:** `backend/app/middleware/rate_limit.py` uses Redis sorted sets for sliding-window rate limiting with in-memory fallback.
   [Source: backend/app/middleware/rate_limit.py]

5. **WebSocket pub/sub EXISTS:** `backend/app/api/v1/ws.py` uses Redis pub/sub on `agent:status:{user_id}` channel.
   [Source: backend/app/api/v1/ws.py]

6. **Emergency brake Redis EXISTS:** `backend/app/agents/brake.py` uses Redis for brake state per user with `paused:{user_id}` key pattern.
   [Source: backend/app/agents/brake.py]

7. **Health check includes Redis:** `backend/app/api/v1/health.py` checks Redis connectivity with 2s timeout.
   [Source: backend/app/api/v1/health.py]

**WHAT'S MISSING (the actual work for this story):**
- No centralized `cache/redis_client.py` — Redis usage is scattered (rate_limit.py creates its own client, ws.py creates its own, brake.py creates its own). Need a shared async Redis client with connection pooling.
- No formal pub/sub utility for agent control channels — ws.py has ad-hoc pub/sub, but no reusable `publish_control_event()` helper with defined channel constants.
- No tests for any Redis functionality (cache, pub/sub, Celery config).

### Previous Story Intelligence (0-4)

- Story was primarily a test/verification story since most code already existed
- Pattern: create test files in `backend/tests/unit/test_<module>/` with `__init__.py`
- Used pytest + pytest-asyncio for async test functions
- httpx.AsyncClient for endpoint testing
- All tests passed in CI with Redis service container

### Git Intelligence

Recent commits show the pattern:
- `feat(0-4): API foundation — add tier limits, comprehensive tests, mark done`
- `feat(0-3): clerk authentication integration — move to review`
- Stories are committed with `feat(0-X):` prefix convention

### Technical Requirements

**Centralized Redis Client Pattern:**
```python
# backend/app/cache/redis_client.py
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
```

**Pub/Sub Channel Constants:**
```python
# backend/app/cache/pubsub.py
AGENT_PAUSE_CHANNEL = "agent:pause:{user_id}"
AGENT_RESUME_CHANNEL = "agent:resume:{user_id}"
AGENT_STATUS_CHANNEL = "agent:status:{user_id}"
```

### Library/Framework Requirements

**No new dependencies needed.** All required packages already installed:
- `redis>=5.2.0` (async Redis client)
- `celery[redis]>=5.4.0` (Celery with Redis transport)
- `celery-redbeat>=2.3.3` (dynamic scheduling)
- `broadcaster[redis]>=1.0.0` (WebSocket pub/sub)

### File Structure Requirements

**Files to CREATE:**
```
backend/app/cache/__init__.py
backend/app/cache/redis_client.py        # Centralized async Redis client with pooling
backend/app/cache/pubsub.py              # Agent control pub/sub utilities
backend/tests/unit/test_cache/__init__.py
backend/tests/unit/test_cache/test_redis_client.py
backend/tests/unit/test_cache/test_pubsub.py
backend/tests/unit/test_worker/__init__.py
backend/tests/unit/test_worker/test_celery_config.py
```

**Files to MODIFY:**
```
backend/app/middleware/rate_limit.py      # Refactor to use shared redis_client (optional, only if clean)
```

**Files to NOT TOUCH:**
```
backend/app/worker/celery_app.py         # Already correctly configured
backend/app/worker/tasks.py              # Already correctly configured
backend/app/config.py                    # Already has REDIS_URL
backend/app/api/v1/health.py             # Already has Redis health check
backend/app/api/v1/ws.py                 # Working pub/sub — don't break it
backend/app/agents/brake.py              # Working brake — don't break it
```

### Testing Requirements

- **Backend Framework:** Pytest + pytest-asyncio
- **Redis mocking:** Use `fakeredis[aioredis]` or mock `redis.asyncio` — do NOT require real Redis for unit tests
- **Tests to write:**
  - Redis client: connection pool creation, get/set with TTL, cache miss returns None, health check returns True/False
  - Pub/sub: publish event on correct channel, subscribe receives published message, channel name formatting with user_id
  - Celery config: broker_url is REDIS_URL, result_backend is REDIS_URL, task_routes map agent_* to "agents" queue, reliability settings (acks_late, prefetch=1, reject_on_worker_lost)
  - Graceful degradation: rate limiter works with in-memory fallback when Redis unavailable

### Project Structure Notes

- New `backend/app/cache/` package follows existing module patterns (`backend/app/auth/`, `backend/app/middleware/`)
- Test directory `backend/tests/unit/test_cache/` follows existing `test_api/`, `test_middleware/`, `test_db/` pattern
- All async functions use `async def` with `pytest.mark.asyncio` decorator in tests

### References

- [Source: backend/app/config.py:36] — REDIS_URL setting
- [Source: backend/app/worker/celery_app.py] — Full Celery configuration
- [Source: backend/app/worker/tasks.py] — All task definitions
- [Source: backend/app/middleware/rate_limit.py] — Redis rate limiting with fallback
- [Source: backend/app/api/v1/ws.py] — WebSocket Redis pub/sub
- [Source: backend/app/agents/brake.py] — Emergency brake Redis usage
- [Source: backend/app/api/v1/health.py] — Redis health check
- [Source: backend/requirements.txt] — redis>=5.2.0, celery[redis]>=5.4.0
- [Source: .github/workflows/ci.yml] — CI Redis service container config

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
