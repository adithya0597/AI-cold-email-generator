---
phase: 01-foundation-modernization
plan: 07
subsystem: infra
tags: [opentelemetry, sentry, tracing, observability, llm-cost, redis]

# Dependency graph
requires:
  - phase: 01-foundation-modernization
    provides: FastAPI app factory (Plan 04), Celery worker (Plan 05), Redis config (Plan 05)
provides:
  - OpenTelemetry distributed tracing with ConsoleSpanExporter (dev)
  - Sentry error tracking integration for FastAPI/Starlette
  - Celery auto-instrumentation with OTel
  - LLM cost tracking with Redis-backed monthly aggregation
  - Admin endpoint for LLM cost monitoring
affects: [phase-02, phase-03, phase-04]

# Tech tracking
tech-stack:
  added: [opentelemetry-sdk, opentelemetry-instrumentation-fastapi, opentelemetry-instrumentation-celery, sentry-sdk]
  patterns: [observability-as-middleware, redis-hash-aggregation, budget-alert-pubsub]

key-files:
  created:
    - backend/app/observability/__init__.py
    - backend/app/observability/tracing.py
    - backend/app/observability/cost_tracker.py
    - backend/app/api/v1/admin.py
  modified:
    - backend/app/main.py
    - backend/app/api/v1/router.py

key-decisions:
  - "ConsoleSpanExporter for dev, OTLP placeholder for production -- swap when collector provisioned"
  - "Cost tracking is fire-and-forget (never breaks hot path) -- exceptions logged but swallowed"
  - "Budget alert threshold at 80% of $6/month via Redis pub/sub channel"

patterns-established:
  - "Observability setup via setup_observability(app) in create_app() factory"
  - "Redis hash counters with TTL for time-bucketed aggregation"
  - "Admin endpoints under /api/v1/admin/ prefix"

# Metrics
duration: 5min
completed: 2026-01-31
---

# Phase 1 Plan 07: Observability Stack Summary

**OTel distributed tracing with Sentry error capture, plus Redis-backed LLM cost tracking with budget alerts and admin dashboard endpoint**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-31T07:34:00Z
- **Completed:** 2026-01-31T07:38:54Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- OpenTelemetry TracerProvider with ConsoleSpanExporter wired into FastAPI and Celery
- Sentry SDK initialized with FastAPI/Starlette integrations (activates when SENTRY_DSN is set)
- LLM cost tracker with model pricing table, Redis monthly aggregation, and 35-day TTL
- Budget alert system publishing to Redis pub/sub when user exceeds 80% of $6/month
- Admin endpoint at GET /api/v1/admin/llm-costs with per-user breakdown and month-end projection

## Task Commits

Each task was committed atomically:

1. **Task 1: OpenTelemetry + Sentry initialization** - `475f1af` (feat)
2. **Task 2: LLM Cost Tracking middleware** - `a539af7` (feat)

## Files Created/Modified
- `backend/app/observability/__init__.py` - Package init exporting setup_observability
- `backend/app/observability/tracing.py` - OTel TracerProvider + Sentry init + FastAPI/Celery auto-instrumentation
- `backend/app/observability/cost_tracker.py` - LLM cost tracking with Redis hash aggregation, budget alerts, admin summary
- `backend/app/api/v1/admin.py` - Admin router with GET /llm-costs endpoint
- `backend/app/main.py` - Added setup_observability(app) call in create_app()
- `backend/app/api/v1/router.py` - Wired admin router into v1 API

## Decisions Made
- ConsoleSpanExporter used in development mode; production has a placeholder for OTLP exporter (Grafana Cloud / Honeycomb) that can be swapped in when a collector is provisioned
- Cost tracking uses fire-and-forget pattern -- exceptions are logged but never propagate to the caller, so cost tracking failures cannot break the LLM hot path
- Model pricing table covers GPT-4/4o/4o-mini/3.5-turbo and Claude 3 Opus/Sonnet/Haiku families with a fallback default for unknown models
- Budget alerts published to Redis pub/sub channel `alerts:cost:{user_id}` at 80% of $6/month threshold

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Git staging area contained leftover files from a prior incomplete Plan 08 execution (ci.yml, test files) -- these were unstaged before committing Task 1 to keep commits atomic

## User Setup Required

**Sentry** requires manual configuration:
- Create a Sentry project at sentry.io
- Set `SENTRY_DSN` environment variable
- Without DSN, Sentry is gracefully disabled (observability still works via OTel)

## Next Phase Readiness
- Observability stack is ready -- all API requests generate trace spans in dev console
- LLM cost tracking is callable from any LLM client code via `track_llm_cost()`
- Admin dashboard endpoint available at `/api/v1/admin/llm-costs`
- Production OTel export requires provisioning a collector (Grafana Cloud, Honeycomb, etc.)

---
*Phase: 01-foundation-modernization*
*Completed: 2026-01-31*
