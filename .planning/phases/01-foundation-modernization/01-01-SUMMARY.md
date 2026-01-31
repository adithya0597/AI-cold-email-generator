---
phase: 01-foundation-modernization
plan: 01
subsystem: backend-dependencies
tags: [python, dependencies, pydantic-settings, config, llm-clients]
dependency-graph:
  requires: []
  provides: [modernized-backend-deps, config-module, env-example]
  affects: [01-03-database-layer, 01-04-api-foundation, 01-05-celery-redis, 01-07-observability]
tech-stack:
  added: [pydantic-settings, asyncpg, celery, redis, fastapi-clerk-auth, sentry-sdk, opentelemetry-api, opentelemetry-sdk, opentelemetry-instrumentation-fastapi, opentelemetry-instrumentation-celery, resend, broadcaster, ruff]
  removed: [langchain, python-jose, passlib, selenium, black, flake8, prometheus-client, aiohttp, lxml, openpyxl, pandas]
  upgraded: [fastapi, uvicorn, pydantic, openai, anthropic, sqlalchemy, alembic, httpx, python-multipart]
  patterns: [pydantic-settings-singleton, env-file-config]
key-files:
  created: [backend/app/config.py, backend/.env.example]
  modified: [backend/requirements.txt, backend/app/core/llm_clients.py]
decisions:
  - id: dep-modernization
    summary: Upgraded all backend deps, removed 11 deprecated packages, added 13 new packages
  - id: resend-email
    summary: ADR-6 resolved -- Resend chosen over SendGrid for transactional email
  - id: ruff-replaces-black-flake8
    summary: Ruff replaces both black and flake8 as single linter/formatter
  - id: raw-httpx-llm-clients
    summary: LLM clients use raw httpx, not SDK -- safe from openai v2 breaking changes
metrics:
  duration: ~5 min
  completed: 2026-01-31
---

# Phase 01 Plan 01: Backend Dependency Modernization Summary

**One-liner:** Modernized all Python deps (fastapi 0.115+, openai 2.16+, SQLAlchemy async), removed 11 deprecated packages, added 13 new packages for auth/queue/observability/email, and created pydantic-settings config module.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Update requirements.txt with modernized versions | `1d3ad66` | `backend/requirements.txt` |
| 2 | Document LLM client raw httpx usage (no SDK breaking changes) | `1e05616` | `backend/app/core/llm_clients.py` |
| 3 | Create pydantic-settings config module + .env.example | `3ca2f7e` | `backend/app/config.py`, `backend/.env.example` |

## What Changed

### Task 1: requirements.txt Modernization

**Upgraded (8 packages):**
- `fastapi` 0.104.1 -> >=0.115.0
- `uvicorn[standard]` 0.24.0 -> >=0.34.0
- `pydantic` 2.5.0 -> >=2.10.0
- `openai` 1.3.0 -> >=2.16.0 (v1 to v2 major upgrade)
- `anthropic` 0.7.0 -> >=0.77.0
- `sqlalchemy[asyncio]` 2.0.23 -> >=2.0.36 (added asyncio extra)
- `alembic` 1.12.1 -> >=1.14.0
- `python-multipart` 0.0.6 -> >=0.0.18

**Added (13 packages):**
- `pydantic-settings>=2.7.0` -- centralized config management
- `asyncpg>=0.30.0` -- async PostgreSQL driver for SQLAlchemy
- `celery[redis]>=5.4.0` -- distributed task queue
- `redis>=5.2.0` -- cache + message broker
- `fastapi-clerk-auth>=0.0.9` -- Clerk JWT validation
- `sentry-sdk[fastapi]>=2.0.0` -- error tracking
- `opentelemetry-api>=1.29.0` + `opentelemetry-sdk>=1.29.0` -- distributed tracing
- `opentelemetry-instrumentation-fastapi>=0.50b0` + `opentelemetry-instrumentation-celery>=0.50b0`
- `resend>=2.0.0` -- transactional email (ADR-6 resolved)
- `broadcaster[redis]>=1.0.0` -- WebSocket pub/sub
- `ruff>=0.9.0` -- replaces both black and flake8

**Removed (11 packages):**
- `langchain==0.0.340` -- pre-1.0 deprecated, not needed until Phase 3
- `python-jose[cryptography]==3.3.0` -- replaced by Clerk auth
- `passlib[bcrypt]==1.7.4` -- replaced by Clerk (no password auth)
- `selenium==4.15.2` -- heavy, not needed for Phase 1
- `black==23.11.0` -- replaced by ruff
- `flake8==6.1.0` -- replaced by ruff
- `prometheus-client==0.19.0` -- replaced by OpenTelemetry + Sentry
- `aiohttp==3.9.1` -- not needed, httpx is the HTTP client
- `lxml==4.9.3` -- not used
- `openpyxl==3.1.2` -- not needed (was for Excel parsing)
- `pandas==2.1.3` -- not needed (was for data manipulation)

### Task 2: LLM Client SDK Assessment

No code changes required. The existing `OpenAIClient` and `AnthropicClient` in `llm_clients.py` use raw httpx HTTP calls, NOT the openai/anthropic Python SDKs. A grep of the entire codebase confirmed no file imports `openai` or `anthropic` directly. The SDK version upgrades (openai v1->v2, anthropic 0.7->0.77) have zero impact on working code.

Added documentation comment noting the raw httpx approach and a TODO for Phase 3 SDK migration.

### Task 3: pydantic-settings Config Module

Created `backend/app/config.py` with a `Settings` class containing all environment variables:
- `DATABASE_URL` (postgresql+asyncpg connection string)
- `REDIS_URL` (Celery broker + cache)
- `CLERK_DOMAIN` (JWT authentication)
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` (LLM clients)
- `SENTRY_DSN` (error tracking)
- `RESEND_API_KEY` (email service)
- `SUPABASE_URL` / `SUPABASE_KEY` (storage only)
- `APP_ENV`, `DEBUG`, `CORS_ORIGINS`

Exports a `settings = Settings()` singleton. All future config access should use `from app.config import settings`.

Created `backend/.env.example` with documentation for every variable.

## Decisions Made

1. **ADR-6 Resolved: Resend for email** -- Resend chosen over SendGrid. Better DX, free tier (3K emails/mo) sufficient for development and beta.
2. **Ruff replaces Black + Flake8** -- Single tool for linting and formatting, 10-100x faster.
3. **Raw httpx LLM clients preserved** -- No migration to SDK v2 in this plan. Documented for Phase 3 consideration.
4. **Version pinning strategy** -- Using `>=X.Y.Z,<NEXT_MAJOR` for major packages (fastapi, openai, celery, pydantic) and `>=X.Y.Z` for stable packages.

## Deviations from Plan

None -- plan executed exactly as written.

## Next Phase Readiness

Plan 01 unblocks:
- **Plan 03 (Database Layer):** asyncpg and sqlalchemy[asyncio] are now in requirements
- **Plan 04 (API Foundation):** fastapi-clerk-auth is now in requirements; config module provides settings
- **Plan 05 (Celery + Redis):** celery[redis] and redis are now in requirements
- **Plan 07 (Observability):** sentry-sdk and opentelemetry packages are now in requirements

No blockers or concerns for downstream plans.
