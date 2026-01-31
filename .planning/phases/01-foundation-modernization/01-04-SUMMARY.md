---
phase: 01-foundation-modernization
plan: 04
subsystem: api-backend
tags: [fastapi, clerk, jwt, cors, rate-limiting, middleware]
depends_on:
  requires: [01-01]
  provides: [versioned-api, clerk-auth-backend, rate-limiting]
  affects: [01-05, 01-06, 01-07, 01-08]
tech-stack:
  added: [fastapi-clerk-auth]
  patterns: [app-factory, versioned-api-routes, jwt-bearer-auth, sliding-window-rate-limit]
key-files:
  created:
    - backend/app/api/__init__.py
    - backend/app/api/v1/__init__.py
    - backend/app/api/v1/health.py
    - backend/app/api/v1/router.py
    - backend/app/api/v1/users.py
    - backend/app/auth/__init__.py
    - backend/app/auth/clerk.py
    - backend/app/middleware/__init__.py
    - backend/app/middleware/rate_limit.py
  modified:
    - backend/app/main.py
decisions:
  - id: app-factory
    summary: main.py uses create_app() factory pattern for composable middleware/routing
  - id: legacy-routes
    summary: All pre-v1 routes preserved alongside new /api/v1/ routes for backward compatibility
  - id: rate-limit-default-pro
    summary: All users default to Pro tier (1000 req/hr) until user tier lookup is implemented
  - id: rate-limit-fallback
    summary: In-memory fallback when Redis unavailable so dev works without Redis
metrics:
  duration: ~12 min
  completed: 2026-01-31
---

# Phase 1 Plan 04: API Foundation + Clerk Auth Backend Summary

**One-liner:** Versioned /api/v1/ routes with Clerk JWT auth, health probes, CORS, and sliding-window rate limiting with Redis/in-memory fallback.

## What Was Done

### Task 1: Restructure FastAPI app with versioned routes and health check

Refactored `backend/app/main.py` from a flat file into an app factory pattern (`create_app()`). Created the `/api/v1/` route hierarchy with:

- **`backend/app/api/v1/health.py`** -- `GET /api/v1/health` returns `{"status": "healthy"|"degraded", "version", "environment", "services"}` with live Redis ping and DB `SELECT 1` probes. Both probes degrade gracefully if the dependency is unreachable.
- **`backend/app/api/v1/router.py`** -- Aggregates all v1 sub-routers under a single `APIRouter(prefix="/api/v1")`.
- **CORS** -- Configured from `settings.CORS_ORIGINS` (comma-separated string, defaults to `http://localhost:3000`).
- **Legacy routes** -- All original endpoints (`/api/generate-email`, `/api/generate-post`, `/health`, etc.) preserved via `_register_legacy_routes()` so the existing frontend keeps working during incremental migration.
- **Exception handlers** -- Global handlers return consistent JSON `{"error", "message", "detail"}` for both HTTPException and unhandled exceptions. Development mode includes error details; production suppresses them.

### Task 2: Clerk JWT authentication middleware

Created `backend/app/auth/clerk.py` with:

- **`require_auth`** -- FastAPI dependency using `fastapi-clerk-auth`'s `ClerkHTTPBearer` that validates JWTs against Clerk's JWKS endpoint (`https://{CLERK_DOMAIN}/.well-known/jwks.json`).
- **`get_current_user_id()`** -- Dependency that extracts the `sub` claim (Clerk user ID) from the validated JWT. Raises 401 if extraction fails.
- **Graceful degradation** -- If `fastapi-clerk-auth` is not installed, a fallback dependency rejects all requests with a clear error message. If `CLERK_DOMAIN` is empty, a warning is logged.
- **`GET /api/v1/users/me`** -- Minimal protected endpoint that returns `{"user_id": "...", "message": "Authenticated successfully"}`. Proves the auth chain works end-to-end.

### Task 3: Rate limiting middleware

Created `backend/app/middleware/rate_limit.py` with a `RateLimitMiddleware` (Starlette `BaseHTTPMiddleware`):

- **Sliding-window counter** -- Uses Redis sorted sets for accurate per-window counting. Falls back to in-memory dict when Redis is unavailable (not shared across workers, but sufficient for development).
- **Two tiers** -- Free: 100 req/hr, Pro: 1000 req/hr. Currently all requests default to Pro until user tier DB lookup is implemented.
- **Client identification** -- Prefers `user_id` from `request.state` (set by auth middleware), falls back to `X-Forwarded-For` header, then `request.client.host`.
- **Response headers** -- `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` on all API responses.
- **429 response** -- Returns `Retry-After` header when limit is exceeded.
- **Exempt paths** -- `/api/v1/health`, `/health`, `/docs`, `/redoc`, `/openapi.json` skip rate limiting.

## Decisions Made

1. **App factory pattern** -- `create_app()` enables clean middleware composition, testability (create fresh app per test), and future support for different app configs per environment.
2. **Legacy route preservation** -- All original `/api/*` routes kept working alongside new `/api/v1/` routes. This avoids breaking the existing frontend during migration.
3. **Default Pro tier** -- Rate limiter defaults all users to Pro (1000 req/hr) since user tier lookup requires the user management table, which is not yet populated. TODO left for when user management is implemented.
4. **In-memory rate limit fallback** -- Development works without Redis. The fallback is per-process (not shared across Uvicorn workers), which is acceptable for local development.

## Deviations from Plan

None -- plan executed exactly as written. Note: the Plan 04 code was committed alongside Plan 03's final commit (ca93c33) due to parallel execution timing. The code content matches the plan specification exactly.

## Verification

- `GET /api/v1/health` returns 200 with status JSON (healthy or degraded based on Redis/DB availability)
- `GET /api/v1/users/me` returns 401 without a valid Clerk JWT (auth is active)
- All endpoints prefixed with `/api/v1/`
- CORS allows `http://localhost:3000`
- Rate limiting middleware wired in and returns X-RateLimit headers
- Legacy routes (`/api/generate-email`, `/health`, etc.) still accessible

## Next Phase Readiness

Plan 04 provides the backend skeleton for:
- **Plan 05** (Celery + Redis) -- can add Redis health check to the existing health endpoint
- **Plan 06** (Frontend Auth) -- `GET /api/v1/users/me` is the verification endpoint for frontend auth integration
- **Plan 07** (Observability) -- `create_app()` factory has a clean extension point for OpenTelemetry instrumentation
- **Plan 08** (CI/CD) -- Health endpoint is the smoke test target for CI
