# Story 0.10: WebSocket Infrastructure

Status: done

## Story

As a **user**,
I want **real-time updates when agents complete actions**,
so that **I see activity without refreshing the page**.

## Acceptance Criteria

1. **AC1 - Authenticated Connection:** Given I have a valid JWT token, when I connect to WebSocket at `/api/v1/ws/agents/{user_id}`, then the connection is authenticated using the JWT token.

2. **AC2 - Real-time Events:** Given I'm connected via WebSocket, when an agent completes a step, then I receive: `{type: "agent.step_completed", data: {...}}`.

3. **AC3 - Auto-Reconnect:** Given the WebSocket disconnects, when the client detects disconnection, then it reconnects automatically with exponential backoff.

4. **AC4 - Missed Events Recovery:** Given I was disconnected, when I reconnect, then missed events are recoverable via REST fallback `GET /api/v1/agents/events?since={timestamp}`.

5. **AC5 - Unauthenticated Rejection:** Given I connect without a valid token, when the WebSocket handshake occurs, then unauthenticated connections are rejected with 401.

## Tasks / Subtasks

- [x] Task 1: Add JWT validation to WebSocket endpoint (AC: #1, #5)
  - [x] 1.1: Create `backend/app/auth/ws_auth.py` with `validate_ws_token(token)` that validates Clerk JWT for WebSocket connections
  - [x] 1.2: Update `ws.py` to call `validate_ws_token()` instead of just checking non-empty token
  - [x] 1.3: Return close code 4401 for invalid/expired tokens with descriptive reason

- [x] Task 2: Add REST fallback endpoint for missed events (AC: #4)
  - [x] 2.1: Add `GET /api/v1/agents/events` endpoint in `agents.py` with `since` query parameter (ISO timestamp)
  - [x] 2.2: Query `AgentActivity` table for events after `since` timestamp for the user
  - [x] 2.3: Return same event format as WebSocket messages for client compatibility

- [x] Task 3: Add exponential backoff to frontend WebSocket reconnect (AC: #3)
  - [x] 3.1: Create `frontend/src/lib/ws-reconnect.ts` utility with exponential backoff (1s, 2s, 4s, 8s, max 30s) and jitter
  - [x] 3.2: Update `AgentActivityFeed.tsx` to use reconnect utility instead of fixed 3-second delay
  - [x] 3.3: Update `EmergencyBrake.tsx` to use reconnect utility instead of fixed 3-second delay

- [x] Task 4: Write comprehensive WebSocket unit tests (AC: #1-#5)
  - [x] 4.1: Create `backend/tests/unit/test_api/test_ws.py`
  - [x] 4.2: Test `validate_ws_token()` accepts valid Clerk JWT
  - [x] 4.3: Test `validate_ws_token()` rejects invalid/empty token
  - [x] 4.4: Test `publish_agent_event()` publishes to correct Redis channel
  - [x] 4.5: Test `publish_agent_event()` handles Redis failure gracefully
  - [x] 4.6: Test REST events endpoint returns events after `since` timestamp
  - [x] 4.7: Test REST events endpoint returns empty list for new user
  - [x] 4.8: Test WebSocket close code 4401 for unauthenticated connections

## Dev Notes

### Architecture Compliance

**CRITICAL — WebSocket infrastructure is ALREADY SUBSTANTIALLY IMPLEMENTED:**

1. **WebSocket endpoint EXISTS:** `backend/app/api/v1/ws.py` with:
   - Route: `/api/v1/ws/agents/{user_id}`
   - Redis pub/sub on channel `agent:status:{user_id}`
   - Ping/pong support
   - Token query parameter (but no JWT validation — just checks non-empty)
   [Source: backend/app/api/v1/ws.py]

2. **Route registration EXISTS:** `backend/app/api/v1/router.py` includes `ws.router`
   [Source: backend/app/api/v1/router.py]

3. **Event publishing EXISTS:** `publish_agent_event()` in ws.py, called from:
   - `BaseAgent.run()` via `_publish_event()` [Source: backend/app/agents/base.py]
   - `EmergencyBrake` [Source: backend/app/agents/brake.py]
   - `BriefingDelivery` [Source: backend/app/agents/briefing/delivery.py]

4. **Frontend WebSocket clients EXIST:**
   - `AgentActivityFeed.tsx` — activity feed with 3-sec fixed reconnect
   - `EmergencyBrake.tsx` — brake status with 3-sec fixed reconnect + 5-sec polling fallback
   [Source: frontend/src/components/AgentActivityFeed.tsx, EmergencyBrake.tsx]

5. **REST activity endpoint EXISTS:** `GET /agents/activity` with pagination
   [Source: backend/app/api/v1/agents.py:114-163]

6. **Clerk JWT auth EXISTS:** `backend/app/auth/clerk.py` with `ClerkHTTPBearer` for HTTP routes
   [Source: backend/app/auth/clerk.py]

7. **Integration tests EXIST:** `backend/tests/integration/test_agent_websocket.py`

**WHAT'S MISSING:**
- JWT validation in WebSocket handler (TODO on ws.py:78) — needs WebSocket-specific auth util
- REST fallback endpoint `GET /agents/events?since={timestamp}` for missed event recovery
- Exponential backoff on frontend reconnect (currently fixed 3-sec delay)
- Unit tests for WebSocket auth, publish, and REST events

### Previous Story Intelligence (0-9)

- 19 error tracking tests passing, 14 OTel tests, 21 cost tracker tests
- Mock pattern: `unittest.mock.patch` for module imports, `AsyncMock` for async Redis
- `MagicMock` (not AsyncMock) for sync return values like `redis.pipeline()`
- Frontend: React components with hooks, Clerk's `useAuth()` for tokens

### Technical Requirements

**WebSocket JWT Validation:**
```python
# backend/app/auth/ws_auth.py
async def validate_ws_token(token: str) -> Optional[str]:
    """Validate Clerk JWT for WebSocket connections. Returns user_id or None."""
    try:
        from fastapi_clerk_auth import ClerkConfig
        # Reuse same JWKS validation as HTTP auth
        config = ClerkConfig(jwks_url=f"https://{settings.CLERK_DOMAIN}/.well-known/jwks.json")
        decoded = config.decode(token)
        return decoded.get("sub")
    except Exception:
        return None
```

**REST Events Fallback:**
```python
@router.get("/events")
async def get_events_since(
    user_id: str = Query(...),
    since: str = Query(..., description="ISO timestamp"),
):
    # Query AgentActivity where created_at > since, ordered by created_at asc
```

**Frontend Reconnect with Exponential Backoff:**
```typescript
function createReconnect(baseDelay = 1000, maxDelay = 30000) {
  let attempt = 0;
  return {
    nextDelay(): number {
      const delay = Math.min(baseDelay * 2 ** attempt, maxDelay);
      const jitter = delay * 0.1 * Math.random();
      attempt++;
      return delay + jitter;
    },
    reset() { attempt = 0; },
  };
}
```

### Library/Framework Requirements

**No new dependencies needed.** All packages already installed:
- `sentry-sdk[fastapi]`, `redis`, `fastapi-clerk-auth` (backend)
- `@clerk/clerk-react` (frontend)

### File Structure Requirements

**Files to CREATE:**
```
backend/app/auth/ws_auth.py
backend/tests/unit/test_api/test_ws.py
frontend/src/lib/ws-reconnect.ts
```

**Files to MODIFY:**
```
backend/app/api/v1/ws.py               # Add JWT validation call
backend/app/api/v1/agents.py           # Add GET /events?since= endpoint
frontend/src/components/AgentActivityFeed.tsx  # Use exponential backoff reconnect
frontend/src/components/EmergencyBrake.tsx     # Use exponential backoff reconnect
```

**Files to NOT TOUCH:**
```
backend/app/auth/clerk.py              # HTTP auth — separate concern
backend/app/api/v1/router.py           # Already includes ws.router
backend/app/agents/base.py             # Already publishes events
backend/app/agents/brake.py            # Already publishes events
backend/tests/integration/             # Integration tests — separate
```

### Testing Requirements

- **Backend Framework:** Pytest + pytest-asyncio
- **Mocking:** Mock `fastapi_clerk_auth`, mock Redis pub/sub, mock SQLAlchemy session
- **Tests to write:**
  - `validate_ws_token` returns user_id for valid JWT
  - `validate_ws_token` returns None for invalid/empty token
  - `validate_ws_token` returns None when Clerk not configured
  - `publish_agent_event` publishes JSON to `agent:status:{user_id}` channel
  - `publish_agent_event` handles Redis failure without raising
  - REST events endpoint returns events after `since` timestamp
  - REST events endpoint returns empty list for no matching events
  - WebSocket rejects connection with 4401 when token is empty

### References

- [Source: backend/app/api/v1/ws.py] — Full WebSocket endpoint
- [Source: backend/app/api/v1/agents.py:114-163] — Activity feed endpoint
- [Source: backend/app/auth/clerk.py] — Clerk JWT auth
- [Source: frontend/src/components/AgentActivityFeed.tsx] — Frontend WS client
- [Source: frontend/src/components/EmergencyBrake.tsx] — Frontend WS client

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
