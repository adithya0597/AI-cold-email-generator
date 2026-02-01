# Story 0.9: Error Tracking Integration

Status: done

## Story

As an **operator**,
I want **automated error tracking with alerts**,
so that **I'm notified of issues before users report them**.

## Acceptance Criteria

1. **AC1 - Error Capture:** Given Sentry is configured, when an unhandled exception occurs, then the error is captured with stack trace and context.

2. **AC2 - User Context:** Given an authenticated request fails, when the error is captured, then `user_id` is attached (without PII like email).

3. **AC3 - Error Rate Alert:** Given error rate is monitored, when it exceeds 1%, then a mechanism exists to trigger alerts (Sentry alert rule configuration documented).

4. **AC4 - Error Grouping:** Given errors are captured, when reviewed, then errors are grouped by type for triage (Sentry fingerprinting configured).

5. **AC5 - Frontend Source Maps:** Given the frontend is built, when an error occurs in production, then source maps are available for debugging (Sentry browser SDK + Vite source map upload configured).

## Tasks / Subtasks

- [x] Task 1: Enhance backend Sentry integration with user context and fingerprinting (AC: #1, #2, #4)
  - [x] 1.1: Create `backend/app/observability/error_tracking.py` with `configure_sentry_scope()` middleware that sets `user_id` on Sentry scope from Clerk auth
  - [x] 1.2: Add `before_send` callback to Sentry init that scrubs PII (email, name) and applies custom fingerprinting
  - [x] 1.3: Register Sentry scope middleware in `main.py` exception handlers to enrich context
  - [x] 1.4: Add `capture_error()` helper that attaches extra context (agent_type, request_path, etc.)

- [x] Task 2: Configure frontend Sentry SDK with source maps (AC: #5)
  - [x] 2.1: Add `@sentry/react` and `@sentry/vite-plugin` to frontend dependencies
  - [x] 2.2: Create `frontend/src/lib/sentry.ts` initializing Sentry browser SDK with DSN, environment, replay integration
  - [x] 2.3: Add Sentry ErrorBoundary wrapper in App.tsx
  - [x] 2.4: Configure Vite plugin for source map upload in `vite.config.ts`
  - [x] 2.5: Add `VITE_SENTRY_DSN` and `SENTRY_AUTH_TOKEN` to frontend env config

- [x] Task 3: Document alert configuration for 1% error rate (AC: #3)
  - [x] 3.1: Add alert rule documentation in error_tracking.py docstring describing Sentry dashboard alert setup for error rate > 1%

- [x] Task 4: Write comprehensive error tracking tests (AC: #1-#4)
  - [x] 4.1: Create `backend/tests/unit/test_observability/test_error_tracking.py`
  - [x] 4.2: Test `before_send` callback scrubs PII fields
  - [x] 4.3: Test `before_send` applies custom fingerprinting for known error types
  - [x] 4.4: Test `configure_sentry_scope()` sets user_id from request state
  - [x] 4.5: Test `capture_error()` attaches extra context
  - [x] 4.6: Test Sentry init includes `before_send` when DSN is configured
  - [x] 4.7: Test graceful degradation when Sentry is not configured

## Dev Notes

### Architecture Compliance

**CRITICAL — Sentry is ALREADY PARTIALLY IMPLEMENTED:**

1. **Sentry SDK initialized:** `backend/app/observability/tracing.py:70-86` — `_init_sentry()` with FastAPI + Starlette integrations, `send_default_pii=False`
   [Source: backend/app/observability/tracing.py:70-86]

2. **Config setting exists:** `SENTRY_DSN: str = ""` in config.py
   [Source: backend/app/config.py:46]

3. **Package installed:** `sentry-sdk[fastapi]>=2.0.0` in requirements.txt
   [Source: backend/requirements.txt:32]

4. **Global exception handlers:** `main.py:78-102` — HTTP + general exception handlers returning JSON
   [Source: backend/app/main.py:78-102]

5. **Custom error classes:** `error_handlers.py` — ServiceError hierarchy (WebScrapingError, LLMGenerationError, etc.)
   [Source: backend/app/core/error_handlers.py]

6. **Manual Sentry capture:** `briefing/fallback.py:45-51` — `sentry_sdk.capture_exception(exc)`
   [Source: backend/app/agents/briefing/fallback.py:45-51]

**WHAT'S MISSING:**
- No `before_send` callback for PII scrubbing and custom fingerprinting
- No middleware to set `user_id` on Sentry scope from Clerk auth
- No `capture_error()` helper with rich context
- No frontend Sentry SDK (`@sentry/react` not installed)
- No source map upload configuration
- No alert configuration documentation
- No tests for error tracking

### Previous Story Intelligence (0-8)

- Mock pattern: `unittest.mock.patch` for module-level functions, `MagicMock` for sync returns, `AsyncMock` for async
- Key learning: `redis.asyncio.Redis.pipeline()` is sync, returns async context manager — use `MagicMock` not `AsyncMock`
- Test directory `backend/tests/unit/test_observability/` already exists
- 21 cost tracker tests + 14 OTel tracing tests all passing

### Technical Requirements

**Backend `before_send` Callback:**
```python
def _before_send(event, hint):
    """Scrub PII and apply custom fingerprinting."""
    # Scrub PII from user context
    if "user" in event:
        event["user"] = {"id": event["user"].get("id")}  # Keep only user_id

    # Custom fingerprinting for known error types
    if "exception" in event:
        exc_type = event["exception"]["values"][0].get("type", "")
        if exc_type in ("RateLimitError", "WebScrapingError"):
            event["fingerprint"] = [exc_type]

    return event
```

**Sentry Scope Middleware:**
```python
async def configure_sentry_scope(request, call_next):
    """Set user context on Sentry scope from Clerk auth."""
    with sentry_sdk.configure_scope() as scope:
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            scope.set_user({"id": user_id})
        response = await call_next(request)
    return response
```

**Frontend Sentry Init:**
```typescript
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.VITE_APP_ENV || "development",
  integrations: [Sentry.browserTracingIntegration(), Sentry.replayIntegration()],
  tracesSampleRate: import.meta.env.VITE_APP_ENV === "production" ? 0.1 : 1.0,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
});
```

### Library/Framework Requirements

**New backend dependencies:** None (sentry-sdk already installed)

**New frontend dependencies:**
```
@sentry/react
@sentry/vite-plugin
```

### File Structure Requirements

**Files to CREATE:**
```
backend/app/observability/error_tracking.py
backend/tests/unit/test_observability/test_error_tracking.py
frontend/src/lib/sentry.ts
```

**Files to MODIFY:**
```
backend/app/observability/tracing.py        # Add before_send to _init_sentry()
backend/app/observability/__init__.py       # Export capture_error
backend/app/main.py                         # Register Sentry scope middleware
frontend/package.json                       # Add @sentry/react, @sentry/vite-plugin
frontend/vite.config.ts                     # Add Sentry Vite plugin
frontend/src/App.tsx                        # Wrap with Sentry ErrorBoundary
frontend/src/lib/sentry.ts                  # New file — Sentry browser init
```

**Files to NOT TOUCH:**
```
backend/app/core/error_handlers.py          # Existing error classes — separate concern
backend/app/observability/cost_tracker.py   # Separate cost tracking
backend/app/observability/langfuse_client.py # Separate LLM observability
backend/app/agents/briefing/fallback.py     # Already has manual Sentry capture
```

### Testing Requirements

- **Backend Framework:** Pytest + pytest-asyncio
- **Mocking:** Mock `sentry_sdk` module functions
- **Tests to write:**
  - `before_send` scrubs PII (removes email, name, keeps user_id)
  - `before_send` applies fingerprinting for RateLimitError, WebScrapingError
  - `before_send` passes through events without exceptions unchanged
  - `configure_sentry_scope` sets user_id from request.state
  - `configure_sentry_scope` handles missing user_id gracefully
  - `capture_error` attaches extra context (agent_type, path)
  - Sentry init includes `before_send` callback
  - Graceful degradation when SENTRY_DSN is empty

### References

- [Source: backend/app/observability/tracing.py:70-86] — Existing Sentry init
- [Source: backend/app/main.py:78-102] — Exception handlers
- [Source: backend/app/config.py:46] — SENTRY_DSN setting
- [Source: backend/app/core/error_handlers.py] — Custom error classes
- [Source: backend/requirements.txt:32] — sentry-sdk package

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
