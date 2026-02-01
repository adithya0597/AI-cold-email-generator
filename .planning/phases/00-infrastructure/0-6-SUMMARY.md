---
phase: "0"
plan: "6"
subsystem: worker-infrastructure
tags: [celery, dlq, zombie-cleanup, retry, exponential-backoff, redis]
dependency-graph:
  requires: ["0-5"]
  provides: ["dead-letter-queue", "zombie-cleanup", "exponential-backoff-retry"]
  affects: ["03-04", "04-01"]
tech-stack:
  added: []
  patterns: ["dead-letter-queue-redis-list", "celery-signal-task-failure", "exponential-backoff"]
key-files:
  created:
    - backend/app/worker/dlq.py
    - backend/app/worker/retry.py
    - backend/tests/unit/test_worker/test_dlq.py
    - backend/tests/unit/test_worker/test_retry.py
    - backend/tests/unit/test_worker/test_zombie_cleanup.py
  modified:
    - backend/app/worker/celery_app.py
    - backend/app/worker/tasks.py
    - backend/app/api/v1/admin.py
    - backend/tests/unit/test_worker/test_celery_config.py
decisions:
  - id: "0-6-dlq-redis-list"
    description: "DLQ uses Redis LIST with 7-day TTL per queue, keyed dlq:{queue}"
  - id: "0-6-signal-handler"
    description: "task_failure signal with asyncio.run() bridge to write DLQ entries from sync signal context"
  - id: "0-6-zombie-inspect"
    description: "Zombie cleanup uses celery inspect().active() to find tasks exceeding hard timeout"
metrics:
  duration: "~5 min"
  completed: "2026-02-01"
---

# Phase 0 Plan 6: Celery Worker Infrastructure Summary

DLQ handler writes failed tasks to Redis lists with 7-day TTL; zombie cleanup revokes stale tasks every 5 minutes via beat schedule; exponential backoff utility with base*2^attempt capped at 600s.

## What Was Done

### Task 1: Dead Letter Queue Handler (AC#5, AC#7)
- Created `backend/app/worker/dlq.py` with `handle_task_failure`, `get_dlq_contents`, `dlq_length`, `clear_dlq`
- Each failed task is JSON-serialized to a Redis list `dlq:{queue}` with 7-day TTL
- Registered `task_failure` signal in `celery_app.py` using `asyncio.run()` to bridge sync signal to async Redis writer
- Added `GET /admin/dlq` endpoint in `admin.py` returning queue contents with total count
- Commit: `96fd70f`

### Task 2: Zombie Task Cleanup (AC#6)
- Added `cleanup_zombie_tasks` task in `tasks.py` using `celery_app.control.inspect().active()`
- Compares each task's `time_start` against hard timeout (300s), revokes stale tasks with `terminate=True`
- Graceful handling when no workers are online (inspect returns None)
- Registered in `beat_schedule` at 300-second (5-minute) interval
- Commit: `58cfd51`

### Task 3: Exponential Backoff Utility (AC#4)
- Created `backend/app/worker/retry.py` with `calculate_backoff` and `retry_with_backoff`
- Formula: `min(base_delay * 2^attempt, max_delay)` -- defaults 30s base, 600s cap
- Progression: 30s, 60s, 120s, 240s, 480s, 600s (capped)
- Commit: `59c5f59`

### Task 4: Comprehensive Tests (AC#1-#7)
- 8 DLQ tests: write to Redis, TTL, contents retrieval, limit, length, clear, admin endpoint structure and logic
- 8 retry tests: each attempt level, max cap, custom base, custom max
- 6 zombie tests: revoke stale, ignore healthy, handle no workers, 3 schedule config checks
- 5 new config tests: soft/hard timeouts (240/300), heartbeat events, beat schedule zombie entry
- Total: 42 tests passing (27 new + 15 existing)
- Commit: `2e45d0c`

## Decisions Made

1. **DLQ as Redis LIST** -- Simple, ordered, supports TTL for automatic cleanup. No separate database table needed.
2. **Signal-based DLQ** -- `task_failure` signal fires after all retries exhausted, uses `asyncio.run()` to bridge sync Celery signal context to async Redis client.
3. **Inspect-based zombie detection** -- Uses Celery's built-in inspect API rather than custom tracking. Gracefully handles offline workers.

## Deviations from Plan

None -- plan executed exactly as written.

## Verification

- All 42 tests pass: `pytest tests/unit/test_worker/ -v --no-cov`
- Existing 15 celery config tests unchanged and passing
- No new dependencies added
- Existing timeouts (240/300), heartbeat, retry defaults untouched

## Next Phase Readiness

No blockers. Worker infrastructure complete for agent task execution.
