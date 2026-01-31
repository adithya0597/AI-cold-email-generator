---
phase: 01-foundation-modernization
plan: "08"
subsystem: infrastructure
tags: [ci-cd, github-actions, websocket, email, storage, gdpr, performance]
dependency-graph:
  requires: [01-01, 01-02, 01-03, 01-04, 01-05, 01-06]
  provides: [ci-pipeline, websocket-infra, transactional-email, storage-service, gdpr-endpoints, performance-baseline]
  affects: [02-*, 03-*]
tech-stack:
  added: [github-actions, resend-sdk, supabase-storage]
  patterns: [redis-pubsub-websocket, template-email, signed-url-storage, gdpr-soft-delete]
key-files:
  created:
    - .github/workflows/ci.yml
    - backend/app/api/v1/ws.py
    - backend/app/services/transactional_email.py
    - backend/app/services/storage_service.py
    - backend/tests/unit/test_health.py
    - frontend/src/App.test.tsx
    - backend/docs/performance-baseline.md
  modified:
    - backend/app/api/v1/router.py
    - backend/app/api/v1/users.py
    - backend/tests/conftest.py
decisions:
  - "Transactional email service created as separate module (transactional_email.py) to avoid collision with legacy email_service.py"
  - "WebSocket auth uses query parameter token with TODO for full JWT validation"
  - "GDPR endpoints use raw SQL (text()) for resilience when tables do not yet exist"
  - "Storage service returns placeholder paths when Supabase is not configured"
metrics:
  duration: ~10 min
  completed: 2026-01-31
---

# Phase 1 Plan 08: CI/CD Pipeline + Remaining Infrastructure Stories -- Summary

GitHub Actions CI with parallel backend/frontend jobs, WebSocket infrastructure with Redis pub/sub, Resend transactional email service, Supabase Storage wrapper, GDPR data export/deletion endpoints, and performance baseline documentation.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | GitHub Actions CI pipeline | 1f3d32b | .github/workflows/ci.yml, tests/conftest.py, test_health.py, App.test.tsx |
| 2 | WebSocket + Email + Storage | 6972a42 | ws.py, transactional_email.py, storage_service.py, router.py |
| 3 | GDPR endpoints + perf docs | 0068398 | users.py, performance-baseline.md |

## What Was Built

### CI Pipeline (.github/workflows/ci.yml)
- Triggered on push to main and PRs to main
- Two parallel jobs with `concurrency` group for cancellation
- **backend-test**: Python 3.11, Redis 7 + PostgreSQL 15 service containers, pip cache, ruff lint, pytest with coverage XML output
- **frontend-test**: Node 20, npm cache, vitest (run once), production build verification
- No `--cov-fail-under` threshold yet (starts at 0%, increases as tests accumulate)

### WebSocket Infrastructure (backend/app/api/v1/ws.py)
- Endpoint: `WS /api/v1/ws/agents/{user_id}`
- Subscribes to Redis pub/sub channel `agent:status:{user_id}`
- Forwards Redis messages to WebSocket client in real-time
- `publish_agent_event(user_id, event)` helper for Celery workers
- JWT auth via `token` query parameter (full validation TODO)
- Graceful disconnect with pub/sub cleanup

### Transactional Email (backend/app/services/transactional_email.py)
- Resend SDK wrapper with `send_email()`, `send_briefing()`, `send_welcome()`, `send_account_deletion_notice()`
- HTML email templates for briefings, welcome, and account deletion
- Graceful degradation when RESEND_API_KEY is not configured (logs warning, returns suppressed flag)
- Separate from legacy `email_service.py` (LLM-based cold email generation)

### Storage Service (backend/app/services/storage_service.py)
- Supabase Storage wrapper with `upload_file()`, `get_signed_url()`, `delete_file()`
- File validation: 10MB size limit, PDF and DOCX only
- Per-user file isolation: `{bucket}/{user_id}/{filename}`
- Handles duplicate uploads via upsert pattern
- Returns placeholder paths when Supabase is not configured

### GDPR Endpoints (backend/app/api/v1/users.py)
- `GET /api/v1/users/me/export` -- Full data export (profile, applications, documents, agent actions)
- `DELETE /api/v1/users/me` -- Soft deletion with 30-day grace period
- Both endpoints use lazy DB imports and handle missing tables gracefully
- Export returns partial data even if some tables are unavailable

### Performance Baseline (backend/docs/performance-baseline.md)
- Target metrics: page load <2s, API p95 <500ms, agent response <30s
- Regression policy: >20% degradation fails CI (Phase 9 implementation)
- k6 test scenarios: smoke, load, stress, soak
- Actual baseline numbers: PENDING (post-deployment)

## Decisions Made

1. **Transactional email as separate module**: The existing `email_service.py` handles LLM-generated cold email content. The new `transactional_email.py` handles system notifications (briefings, welcome, deletion). This avoids naming collision and keeps concerns separated.

2. **WebSocket auth via query parameter**: WebSocket connections receive the JWT as a `token` query parameter since WebSocket headers are limited in browser APIs. Full JWT validation is a TODO -- currently accepts any non-empty token for development testing.

3. **GDPR raw SQL queries**: The export endpoint uses `text()` raw SQL instead of ORM models because the tables may not exist yet in early development. Each query is wrapped in try/except to return partial exports.

4. **Storage graceful degradation**: When `SUPABASE_URL`/`SUPABASE_KEY` are not configured, storage operations return placeholder values instead of failing. This lets development proceed without a Supabase project.

## Deviations from Plan

None -- plan executed exactly as written.

## Phase 1 Completion Status

This is the final plan (8 of 8) in Phase 1: Foundation Modernization.

### Phase 1 Success Criteria Verification

1. `npm run dev` starts Vite+React+TypeScript frontend -- YES (Plan 02)
2. User can sign up via Clerk and see protected dashboard -- YES (Plans 04, 06)
3. Celery worker picks up tasks from Redis, writes to PostgreSQL -- YES (Plan 05)
4. Pushing to main triggers GitHub Actions CI -- YES (Plan 08, this plan)
5. OpenTelemetry + Sentry captures traced API request -- YES (Plan 07)

All 5 phase success criteria are met. Phase 1 is complete.
