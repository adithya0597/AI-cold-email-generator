# Phase 0 Plan 10: WebSocket Infrastructure Summary

**One-liner:** JWT auth on WebSocket endpoint, REST events fallback, exponential backoff reconnect with jitter

## What Was Done

### Task 1: JWT validation on WebSocket endpoint
- Created `backend/app/auth/ws_auth.py` with `validate_ws_token()` using Clerk JWKS
- Dev mode (no CLERK_DOMAIN): skips validation, falls through with URL user_id
- Production: validates JWT, rejects invalid tokens with close code 4401
- Updated `ws.py` to call `validate_ws_token()` after empty-token check

### Task 2: REST fallback for missed events
- Added `GET /agents/events?since={timestamp}` endpoint to `agents.py`
- Returns events in chronological order (oldest first) for client replay
- `EventItem` and `EventsResponse` Pydantic models
- Supports limit parameter (1-200, default 50)

### Task 3: Exponential backoff reconnect
- Created `frontend/src/lib/ws-reconnect.ts` with `createReconnect()` utility
- Backoff: 1s, 2s, 4s, 8s... up to 30s max with 10% jitter
- Updated `AgentActivityFeed.tsx` and `EmergencyBrake.tsx` to use backoff
- Reset attempt counter on successful connection (onopen)

### Task 4: Comprehensive unit tests
- 14 tests in `backend/tests/unit/test_api/test_ws.py`, all passing
- `TestValidateWsToken`: 6 tests (empty, no domain, valid JWT, invalid JWT, missing sub, none-like)
- `TestPublishAgentEvent`: 4 tests (correct channel, JSON payload, Redis failure, cleanup)
- `TestEventsEndpoint`: 4 tests (model validation, empty list, optional fields, all fields)

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Dev mode skips JWT validation (returns None) | Allows testing without Clerk instance; caller uses URL user_id as fallback |
| Close code 4401 (not 401) for WS rejection | WebSocket spec uses 4000-4999 for app-specific codes; mirrors existing empty-token behavior |
| Lazy import of fastapi_clerk_auth in ws_auth | Graceful fallback when package not installed; consistent with clerk.py pattern |
| Events endpoint returns oldest-first order | Client replays missed events chronologically after reconnect |

## Deviations from Plan

None - plan executed exactly as written.

## Files

### Created
- `backend/app/auth/ws_auth.py`
- `backend/tests/unit/test_api/test_ws.py`
- `frontend/src/lib/ws-reconnect.ts`

### Modified
- `backend/app/api/v1/ws.py`
- `backend/app/api/v1/agents.py`
- `frontend/src/components/AgentActivityFeed.tsx`
- `frontend/src/components/EmergencyBrake.tsx`

## Metrics

- **Duration:** ~4 min
- **Tests:** 14 passing
- **Completed:** 2026-02-01
