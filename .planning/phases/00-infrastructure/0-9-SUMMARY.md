# Phase 0 Plan 9: Error Tracking Integration Summary

Sentry error tracking with PII scrubbing, custom fingerprinting, user-context middleware, frontend ErrorBoundary and source map upload.

## What Was Built

### Backend Error Tracking Module (`error_tracking.py`)
- `_before_send(event, hint)` callback: strips PII from user context (keeps only `id`), applies custom fingerprinting for `RateLimitError`, `WebScrapingError`, `LLMGenerationError`
- `configure_sentry_scope` ASGI middleware: sets `user_id` on Sentry scope from `request.state.user_id` (Clerk auth), clears on response/exception
- `capture_error(exc, **context)` helper: captures exceptions with arbitrary extras (agent_type, request_path), graceful degradation when Sentry not configured
- Alert configuration documentation in module docstring (AC3)

### Sentry Init Enhancement (`tracing.py`)
- Added `before_send=_before_send` parameter to `sentry_sdk.init()` call

### Frontend Sentry SDK
- `frontend/src/lib/sentry.ts`: browser SDK init with tracing, replay integration, environment-aware sample rates
- `App.tsx`: wrapped with `Sentry.ErrorBoundary`, `initSentry()` called at module level
- `vite.config.ts`: conditional `sentryVitePlugin` for source map upload when `SENTRY_AUTH_TOKEN` is set, `build.sourcemap: true`
- `.env.example`: added `VITE_SENTRY_DSN` and `SENTRY_AUTH_TOKEN`

### Tests
- 19 tests in `test_error_tracking.py`, all passing
- Coverage: `_before_send` PII scrubbing (5 tests), fingerprinting (4 tests), edge cases (2 tests)
- `configure_sentry_scope` middleware (4 tests including exception cleanup)
- `capture_error` helper (3 tests)
- `_init_sentry` integration (1 test verifying `before_send` wiring)

## Acceptance Criteria Verification

| AC | Description | Status |
|----|------------|--------|
| AC1 | Unhandled exceptions captured with stack trace and context | Done -- Sentry SDK with FastAPI/Starlette integrations + before_send |
| AC2 | user_id attached without PII | Done -- configure_sentry_scope middleware + PII scrubbing in before_send |
| AC3 | Alert mechanism for 1% error rate documented | Done -- module docstring in error_tracking.py |
| AC4 | Errors grouped by type via custom fingerprinting | Done -- _before_send fingerprints RateLimitError, WebScrapingError, LLMGenerationError |
| AC5 | Frontend source maps configured | Done -- sentryVitePlugin + build.sourcemap: true |

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

- `sentry_sdk.set_user()` used instead of deprecated `configure_scope()` context manager (Sentry SDK v2 API)
- User context cleared in `finally` block after each request to prevent leaking across requests
- Sentry Vite plugin conditionally added only when `SENTRY_AUTH_TOKEN` env var exists (no build failure without token)

## Files

### Created
- `backend/app/observability/error_tracking.py`
- `backend/tests/unit/test_observability/test_error_tracking.py`
- `frontend/src/lib/sentry.ts`

### Modified
- `backend/app/observability/tracing.py` -- added `before_send` import and parameter
- `backend/app/observability/__init__.py` -- exported `capture_error`
- `backend/app/main.py` -- registered `configure_sentry_scope` middleware
- `frontend/package.json` -- added `@sentry/react`, `@sentry/vite-plugin`
- `frontend/vite.config.ts` -- added Sentry Vite plugin, enabled source maps
- `frontend/src/App.tsx` -- added ErrorBoundary wrapper and initSentry call
- `frontend/.env.example` -- added Sentry env vars

## Metrics

- Duration: ~4 min
- Tasks: 4/4
- Tests: 19 passing
- Commits: 3 task commits + 1 metadata
