---
phase: "03"
plan: "05"
subsystem: briefing-pipeline
tags: [briefing, redbeat, celery, redis, llm, email, websocket, fallback]
dependency-graph:
  requires: ["03-02", "03-03"]
  provides: ["briefing-generator", "briefing-scheduler", "briefing-delivery", "briefing-api", "briefing-fallback"]
  affects: ["03-07", "03-08"]
tech-stack:
  added: []
  patterns: ["parallel-data-gathering", "llm-summarisation-with-fallback", "redis-cache-48h-ttl", "redbeat-per-user-scheduling", "dual-delivery-inapp-email"]
key-files:
  created:
    - backend/app/agents/briefing/__init__.py
    - backend/app/agents/briefing/generator.py
    - backend/app/agents/briefing/fallback.py
    - backend/app/agents/briefing/scheduler.py
    - backend/app/agents/briefing/delivery.py
    - backend/app/api/v1/briefings.py
  modified:
    - backend/app/worker/celery_app.py
    - backend/app/worker/tasks.py
    - backend/app/api/v1/router.py
decisions:
  - "Route ordering: static paths (/latest, /settings) registered before /{briefing_id} to prevent FastAPI matching conflicts"
  - "No-LLM fallback: if OPENAI_API_KEY not set, briefing built from raw data without LLM summarisation"
  - "RedBeat lock disabled (redbeat_lock_key=None) for single-beat deployments"
  - "Timezone conversion: user local time converted to UTC at schedule creation time; DST transitions handled by weekly cleanup task"
metrics:
  duration: "~7 min"
  completed: "2026-01-31"
---

# Phase 3 Plan 05: Briefing Pipeline Backend Summary

**One-liner:** Daily briefing pipeline with parallel data gathering, LLM summarisation, RedBeat per-user scheduling, dual delivery (in-app WebSocket + Resend email), Redis cache fallback with 48h TTL.

## What Was Built

### Task 1: Briefing Generator + Fallback
- `generator.py`: Full briefing pipeline -- gathers data in parallel via `asyncio.gather()` with 15s per-query timeout (recent matches, application updates, pending approvals, agent warnings), summarises via OpenAI GPT-4o-mini with JSON structured output (30s timeout), stores in briefings table, caches in Redis with 48h TTL
- `fallback.py`: Three-tier fallback hierarchy -- (1) full briefing, (2) lite briefing from Redis cache with last successful data, (3) minimal "check back soon" message. On failure: logs to Sentry, serves lite briefing, schedules retry in 1 hour via Celery
- Empty state briefing for new users with tips ("Set up your preferences to see matches here")
- No-LLM fallback builds briefing from raw data when API key is missing

### Task 2: RedBeat Scheduler + Delivery
- `scheduler.py`: Per-user daily schedule via RedBeat -- creates/updates/removes `RedBeatSchedulerEntry` with user's local time converted to UTC crontab. Weekly cleanup task removes schedules for braked users
- `delivery.py`: Dual delivery -- in-app (WebSocket `system.briefing.ready` event) + email (rich HTML template with metrics cards, action buttons, "Approve All" link, unsubscribe). Mark-as-read functionality updates `read_at` timestamp
- Celery beat configured to use `redbeat.RedBeatScheduler`
- `briefing_generate` task wired to actual generator + delivery pipeline (was a TODO placeholder)

### Task 3: Briefing API Endpoints
- `GET /api/v1/briefings/latest` -- most recent briefing (or null for new users)
- `GET /api/v1/briefings/settings` -- current briefing configuration
- `PUT /api/v1/briefings/settings` -- update time/timezone/channels + RedBeat schedule sync
- `GET /api/v1/briefings` -- paginated history (last 30 days, offset/limit)
- `POST /api/v1/briefings/{id}/read` -- mark briefing as read
- `GET /api/v1/briefings/{id}` -- specific briefing by ID
- Wired into v1 API router

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed route ordering in briefings.py**
- **Found during:** Task 3
- **Issue:** `/settings` GET route was defined after `/{briefing_id}` GET, causing FastAPI to match "settings" as a briefing_id parameter
- **Fix:** Reordered routes so static paths (`/latest`, `/settings`) come before dynamic `/{briefing_id}`
- **Files modified:** `backend/app/api/v1/briefings.py`
- **Commit:** 4625d72

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Static routes before dynamic routes | FastAPI matches routes in registration order; "settings" would match as {briefing_id} |
| No-LLM fallback mode | Graceful degradation when OPENAI_API_KEY not configured; raw data structured as briefing |
| RedBeat lock disabled | Single beat process deployment assumed; avoids Redis lock contention |
| Timezone UTC conversion at schedule time | RedBeat lacks per-entry timezone; DST correction via periodic cleanup task |
| email HTML template inline | Self-contained delivery module; no external template dependency |

## Next Phase Readiness

**For Plan 07 (Briefing Frontend):**
- All API endpoints ready at `/api/v1/briefings/*`
- Briefing content structure stable: `summary`, `actions_needed`, `new_matches`, `activity_log`, `metrics`
- Empty state and lite briefing types available for frontend rendering
- Settings endpoint supports time/timezone/channel configuration

**For Plan 08 (Integration Tests):**
- `generate_full_briefing` and `generate_briefing_with_fallback` are async functions testable with mocked DB/Redis
- Fallback hierarchy testable by raising exceptions from generator
- Redis cache TTL verifiable
- Delivery channels testable independently
