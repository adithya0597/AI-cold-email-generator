---
phase: 01-foundation-modernization
plan: 05
subsystem: infra
tags: [celery, redis, worker, queue, async, background-tasks]
depends_on:
  requires: [01-01, 01-03]
  provides: [celery-worker, queue-routing, example-task, health-check-task]
  affects: [01-07, 01-08]
tech-stack:
  added: [celery, redis]
  patterns: [lazy-import-async-tasks, asyncio-run-in-celery, queue-routing-by-naming-convention]
key-files:
  created:
    - backend/app/worker/__init__.py
    - backend/app/worker/celery_app.py
    - backend/app/worker/tasks.py
  modified: []
decisions:
  - id: lazy-import-pattern
    summary: All DB/async imports inside task functions, never at module level, to prevent event loop conflicts
  - id: asyncio-run-pattern
    summary: Celery tasks use asyncio.run() to bridge sync tasks with async SQLAlchemy operations
  - id: queue-routing-by-name
    summary: Tasks routed to queues by naming convention (agent_* -> agents, briefing_* -> briefings, etc.)
metrics:
  duration: ~8 min
  completed: 2026-01-31
---

# Phase 1 Plan 05: Celery + Redis Worker Infrastructure Summary

**Celery worker app with Redis broker, 4-queue routing (agents/briefings/scraping/default), reliability settings, and async SQLAlchemy proof-of-concept task using lazy imports + asyncio.run().**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-01-31T07:26:29Z
- **Completed:** 2026-01-31T07:34:00Z
- **Tasks:** 2
- **Files created:** 3

## Accomplishments

- Celery app configured with Redis broker/backend, JSON-only serialization, and production reliability settings
- Queue routing for 4 task types: agents, briefings, scraping, and default
- Example task demonstrating lazy-import + asyncio.run() pattern for async DB access from sync Celery tasks
- Health check task for verifying worker liveness

## Task Commits

Both tasks were committed together due to parallel agent execution timing:

1. **Task 1: Celery app + Redis config** -- `67f6a36` (committed alongside Plan 06 files)
2. **Task 2: Example task + health integration** -- `67f6a36` (same commit)

_Note: Worker files were staged when a parallel Plan 06 agent committed, resulting in a single combined commit. All code is correct and matches the plan specification._

## Files Created/Modified

- `backend/app/worker/__init__.py` -- Package docstring with usage instructions
- `backend/app/worker/celery_app.py` -- Celery app named "jobpilot" with Redis config, reliability settings, queue routing, timeouts, and autodiscovery
- `backend/app/worker/tasks.py` -- example_task (proof-of-concept DB write) and health_check_task (worker liveness probe)

## Decisions Made

1. **Lazy import pattern** -- All `app.db` and `sqlalchemy` imports are inside task functions, never at module level. This prevents the Celery worker process from creating an asyncio event loop at import time, which would conflict with `asyncio.run()` inside tasks.
2. **asyncio.run() bridge** -- Celery tasks are synchronous, but SQLAlchemy uses async sessions. The `_run_async()` helper creates a fresh event loop per task invocation via `asyncio.run()`.
3. **Queue routing by naming convention** -- Tasks prefixed with `agent_*`, `briefing_*`, `scrape_*` are routed to dedicated queues. Workers can be scaled independently per queue type.
4. **Health endpoint already complete** -- The Redis ping check was already added in Plan 04's health endpoint (`_check_redis()` in health.py). No modification needed.

## Deviations from Plan

### Commit Structure

The Plan 05 worker files were committed as part of the Plan 06 commit (`67f6a36`) due to parallel agent execution. Both agents were writing to the same repository simultaneously, and the Plan 06 agent's `git add` picked up the staged worker files. The code content is correct and matches the plan specification exactly.

### Health Endpoint

The plan specified "Update health endpoint to include Redis ping check." The health endpoint (`backend/app/api/v1/health.py`) already contained a complete `_check_redis()` function from Plan 04, so no modification was needed. The `health_check_task` was created in tasks.py for future worker-liveness verification.

---

**Total deviations:** 0 functional deviations. 1 commit-structure deviation due to parallel execution.
**Impact on plan:** No impact on functionality. All code matches specification.

## Issues Encountered

- Bash permission denials for `git commit` commands during execution. The parallel Plan 06 agent was running simultaneously, which caused intermittent permission conflicts. Ultimately resolved when the Plan 06 agent committed all staged files (including the worker files).

## User Setup Required

**Redis** must be running for Celery workers to operate:
- Local: `docker run -d -p 6379:6379 redis:7`
- Cloud: Set `REDIS_URL` environment variable (Railway, Upstash, etc.)

## Next Phase Readiness

Plan 05 provides the worker infrastructure for:
- **Plan 07** (Observability) -- `CeleryInstrumentor` can auto-instrument the celery_app for distributed tracing
- **Plan 08** (CI/CD + remaining infra) -- WebSocket endpoint can use `publish_agent_event()` pattern documented in tasks.py pub/sub comments
- **Future agent work** (Phases 3-5) -- Queue routing and task patterns are established; new agents follow the `agent_*` naming convention

---
*Phase: 01-foundation-modernization*
*Completed: 2026-01-31*
