# Story 0.6: Celery Worker Infrastructure

Status: ready-for-dev

## Story

As a **system**,
I want **Celery workers configured for background task processing with reliability guarantees**,
so that **agent tasks run asynchronously without blocking user requests**.

## Acceptance Criteria

1. **AC1 - Task Execution:** Given Celery workers are deployed, when a task is enqueued, then a worker picks up and executes the task.

2. **AC2 - Task Timeouts:** Given a task is running, when it exceeds time limits, then soft timeout fires at 4 minutes (240s) and hard timeout kills at 5 minutes (300s).

3. **AC3 - Heartbeat Monitoring:** Given workers are running, when heartbeat is configured, then worker events are sent enabling monitoring.

4. **AC4 - Retry with Exponential Backoff:** Given a task fails, when retry logic is triggered, then the task is retried up to 3 times with exponential backoff.

5. **AC5 - Dead Letter Queue:** Given a task fails after max retries, when all retries are exhausted, then the task is sent to a dead letter queue for inspection.

6. **AC6 - Zombie Task Cleanup:** Given a periodic schedule, when zombie task cleanup runs, then stale/stuck tasks are detected and handled.

7. **AC7 - Dead Letter Monitoring:** Given tasks are in the dead letter queue, when an admin endpoint is called, then DLQ contents are returned for monitoring.

## Tasks / Subtasks

- [x] Task 1: Add dead letter queue handling with on_failure callback (AC: #5, #7)
  - [x] 1.1: Create `backend/app/worker/dlq.py` with `handle_task_failure()` callback that writes failed tasks to a Redis list `dlq:{queue_name}`
  - [x] 1.2: Register the on_failure signal handler in celery_app.py
  - [x] 1.3: Add `GET /api/v1/admin/dlq` endpoint to list dead letter queue contents

- [x] Task 2: Add zombie task cleanup periodic task (AC: #6)
  - [x] 2.1: Create `cleanup_zombie_tasks` periodic task in tasks.py that inspects active tasks and revokes stale ones
  - [x] 2.2: Register in celery beat_schedule to run every 5 minutes

- [x] Task 3: Add retry with exponential backoff utility (AC: #4)
  - [x] 3.1: Create `backend/app/worker/retry.py` with `retry_with_backoff()` helper that calculates exponential delay
  - [x] 3.2: Verify existing tasks use appropriate retry configuration

- [x] Task 4: Write comprehensive Celery worker tests (AC: #1-#7)
  - [x] 4.1: Create `backend/tests/unit/test_worker/test_dlq.py` — test failure callback writes to DLQ, DLQ contents retrievable
  - [x] 4.2: Create `backend/tests/unit/test_worker/test_retry.py` — test exponential backoff calculation
  - [x] 4.3: Create `backend/tests/unit/test_worker/test_zombie_cleanup.py` — test zombie detection and revocation
  - [x] 4.4: Add tests to existing `test_celery_config.py` for timeout settings and heartbeat config

## Dev Notes

### Architecture Compliance

**CRITICAL — Celery is ALREADY SUBSTANTIALLY IMPLEMENTED:**

1. **Celery app EXISTS:** `backend/app/worker/celery_app.py` with Redis broker, queue routing, reliability settings (acks_late, prefetch=1, reject_on_worker_lost), RedBeat scheduler.
   [Source: backend/app/worker/celery_app.py]

2. **Tasks EXIST:** `backend/app/worker/tasks.py` has agent_job_scout, agent_resume, agent_apply, briefing_generate, verify_brake_completion, cleanup_expired_approvals, example_task, health_check_task. All use lazy imports + asyncio.run() pattern.
   [Source: backend/app/worker/tasks.py]

3. **Timeouts ALREADY SET:** soft_time_limit=240 (4 min), time_limit=300 (5 min) — already correct per AC#2.
   [Source: backend/app/worker/celery_app.py:49-51]

4. **Heartbeat/Events ALREADY SET:** worker_send_task_events=True, task_send_sent_event=True — already correct per AC#3.
   [Source: backend/app/worker/celery_app.py:57-58]

5. **Retry defaults EXIST:** task_default_retry_delay=30, task_max_retries=3.
   [Source: backend/app/worker/celery_app.py:72-73]

6. **Celery config tests EXIST:** `backend/tests/unit/test_worker/test_celery_config.py` from story 0-5 with 15 tests covering broker, routing, reliability, serialization, RedBeat.
   [Source: backend/tests/unit/test_worker/test_celery_config.py]

**WHAT'S MISSING:**
- No dead letter queue handling — tasks that exhaust retries just fail silently
- No zombie task cleanup — no periodic task to detect stuck tasks
- No exponential backoff utility — retry delay is flat 30s
- No admin endpoint for DLQ inspection
- No tests for timeout behavior, heartbeat, retry, DLQ, zombie cleanup

### Previous Story Intelligence (0-5)

- Created `backend/app/cache/` package with redis_client.py and pubsub.py
- Test pattern: mock redis.asyncio with unittest.mock.AsyncMock
- Tests in `backend/tests/unit/test_worker/` already exist with __init__.py
- 33 tests all passing

### Technical Requirements

**Dead Letter Queue Pattern:**
```python
# backend/app/worker/dlq.py
import json
from datetime import datetime, timezone
from app.cache.redis_client import get_redis_client

async def handle_task_failure(task_id: str, task_name: str, args: tuple, kwargs: dict, exc: Exception, queue: str = "default") -> None:
    """Write failed task to dead letter queue in Redis."""
    client = await get_redis_client()
    entry = json.dumps({
        "task_id": task_id,
        "task_name": task_name,
        "args": list(args),
        "kwargs": kwargs,
        "error": str(exc),
        "error_type": type(exc).__name__,
        "failed_at": datetime.now(timezone.utc).isoformat(),
    })
    await client.lpush(f"dlq:{queue}", entry)
```

**Exponential Backoff:**
```python
# backend/app/worker/retry.py
def calculate_backoff(attempt: int, base_delay: int = 30, max_delay: int = 600) -> int:
    """Calculate exponential backoff delay. attempt is 0-indexed."""
    delay = base_delay * (2 ** attempt)
    return min(delay, max_delay)
```

### Library/Framework Requirements

**No new dependencies needed.** All required packages already installed.

### File Structure Requirements

**Files to CREATE:**
```
backend/app/worker/dlq.py                          # Dead letter queue handler
backend/app/worker/retry.py                         # Exponential backoff utility
backend/tests/unit/test_worker/test_dlq.py          # DLQ tests
backend/tests/unit/test_worker/test_retry.py        # Retry/backoff tests
backend/tests/unit/test_worker/test_zombie_cleanup.py  # Zombie cleanup tests
```

**Files to MODIFY:**
```
backend/app/worker/celery_app.py   # Register on_failure signal, add zombie cleanup to beat_schedule
backend/app/worker/tasks.py        # Add cleanup_zombie_tasks periodic task
backend/app/api/v1/router.py       # Add admin DLQ endpoint route (if admin router not already wired)
```

**Files to NOT TOUCH:**
```
backend/app/config.py
backend/app/cache/redis_client.py
backend/app/cache/pubsub.py
backend/app/main.py
```

### Testing Requirements

- **Backend Framework:** Pytest + pytest-asyncio
- **Mocking:** unittest.mock.AsyncMock for Redis operations, mock Celery inspect API for zombie detection
- **Tests to write:**
  - DLQ: failure callback writes correct JSON to Redis list, DLQ list is retrievable, multiple failures accumulate
  - Retry: exponential backoff calculation (attempt 0→30s, 1→60s, 2→120s), max delay cap
  - Zombie: stale task detection, revocation call, cleanup runs on schedule
  - Config: timeout settings (soft=240, hard=300), heartbeat settings, beat_schedule includes zombie cleanup

### References

- [Source: backend/app/worker/celery_app.py] — Full Celery configuration
- [Source: backend/app/worker/tasks.py] — All task definitions
- [Source: backend/tests/unit/test_worker/test_celery_config.py] — Existing Celery config tests
- [Source: backend/app/cache/redis_client.py] — Shared Redis client (from story 0-5)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
