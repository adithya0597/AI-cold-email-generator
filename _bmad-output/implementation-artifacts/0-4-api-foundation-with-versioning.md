# Story 0.4: API Foundation with Versioning

Status: ready-for-dev

## Story

As a **developer**,
I want **a versioned REST API structure with health checks and rate limiting**,
so that **the backend is production-ready and maintainable**.

## Acceptance Criteria

1. **AC1 - Health Check Endpoint:** Given the FastAPI application is running, when I call `GET /api/v1/health`, then I receive a JSON response with `status`, `version`, and service health details.

2. **AC2 - API Versioning:** Given the API is initialized, when I make any request, then all endpoints are prefixed with `/api/v1/`.

3. **AC3 - CORS Configuration:** Given a frontend request comes in, when the request originates from a configured origin, then CORS headers are properly set.

4. **AC4 - JWT Authentication Middleware:** Given a protected route is accessed, when the request is processed, then JWT authentication middleware validates the token on protected routes.

5. **AC5 - Rate Limiting (Tier-based):** Given a user makes repeated API requests, when the request count is tracked, then rate limiting enforces tier-based limits: Free=100/hr, Pro=1000/hr, H1B Pro=1000/hr.

6. **AC6 - Rate Limit Error Response:** Given the rate limit is exceeded, when a request is made, then 429 Too Many Requests is returned with Retry-After header.

## Tasks / Subtasks

- [ ] Task 1: Add h1b_pro and career_insurance tiers to rate limiting (AC: #5)
  - [ ] 1.1: Update TIER_LIMITS in `backend/app/middleware/rate_limit.py` to include `h1b_pro: 1000` and `career_insurance: 1000`
  - [ ] 1.2: Update `_get_tier` method to look up user tier from request state (when available) instead of hardcoding "pro"

- [ ] Task 2: Write comprehensive API foundation tests (AC: #1-#6)
  - [ ] 2.1: Create `backend/tests/unit/test_api/test_health.py` — test health endpoint returns correct structure
  - [ ] 2.2: Create `backend/tests/unit/test_middleware/test_rate_limit.py` — test tier limits, 429 response, Retry-After header, exempt paths
  - [ ] 2.3: Verify all existing routers are prefixed with /api/v1/

## Dev Notes

### Architecture Compliance

**CRITICAL — Most of this story is ALREADY IMPLEMENTED:**

1. **Health check EXISTS:** `backend/app/api/v1/health.py` — returns status, version "1.0.0", environment, and service checks (Redis + DB). Already registered in router.py.
   [Source: backend/app/api/v1/health.py]

2. **API versioning EXISTS:** `backend/app/api/v1/router.py` uses `APIRouter(prefix="/api/v1")`. All sub-routers are included under this prefix.
   [Source: backend/app/api/v1/router.py]

3. **CORS EXISTS:** Configured in `backend/app/main.py` via `CORSMiddleware` with `settings.CORS_ORIGINS`.
   [Source: backend/app/main.py:45-53]

4. **JWT middleware EXISTS:** `backend/app/auth/clerk.py` provides `require_auth` and `get_current_user_id`. Already used by protected endpoints.
   [Source: backend/app/auth/clerk.py]

5. **Rate limiting EXISTS:** `backend/app/middleware/rate_limit.py` with Redis + in-memory fallback, sliding window, 429 responses with Retry-After, rate limit headers. BUT:
   - Missing `h1b_pro` and `career_insurance` tiers (only has `free` and `pro`)
   - `_get_tier()` is hardcoded to return "pro" (TODO comment exists)
   [Source: backend/app/middleware/rate_limit.py:35-40, 137-143]

6. **Error handling EXISTS:** Global exception handlers in main.py for HTTPException and general exceptions.
   [Source: backend/app/main.py:81-102]

**THIS STORY IS PRIMARILY A TEST/VERIFICATION STORY** — the implementation is already there from earlier stories. Main tasks are adding missing tiers and writing comprehensive tests.

### Previous Story Intelligence (0-3)

- Auth sync endpoint added; ProtectedRoute wired up
- All protected routes already use `get_current_user_id` dependency
- Rate limiting currently gives everyone "pro" limits — needs actual tier lookup

### Technical Requirements

**Rate Limit Tier Updates:**
```python
TIER_LIMITS: Dict[str, int] = {
    "free": 100,
    "pro": 1000,
    "h1b_pro": 1000,
    "career_insurance": 1000,
    "enterprise": 5000,  # enterprise tier from architecture
}
```

### Library/Framework Requirements

**No new dependencies needed.**

### File Structure Requirements

**Files to CREATE:**
```
backend/tests/unit/test_api/test_health.py
backend/tests/unit/test_middleware/__init__.py
backend/tests/unit/test_middleware/test_rate_limit.py
```

**Files to MODIFY:**
```
backend/app/middleware/rate_limit.py    # Add h1b_pro tier, update _get_tier
```

**Files to NOT TOUCH:**
```
backend/app/main.py
backend/app/api/v1/health.py
backend/app/api/v1/router.py
backend/app/auth/clerk.py
backend/app/config.py
```

### Testing Requirements

- **Backend Framework:** Pytest + pytest-asyncio
- **Tests to write:**
  - Health endpoint returns JSON with status, version, services keys
  - Health endpoint is at /api/v1/health path
  - All router prefixes start with /api/v1
  - Rate limit middleware has correct tier limits (free=100, pro=1000, h1b_pro=1000)
  - Rate limit returns 429 with Retry-After header when exceeded
  - Health endpoint is exempt from rate limiting
  - Rate limit headers present on responses (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)

## Dev Agent Record

### Agent Model Used

### Route Taken

### GSD Subagents Used

### Debug Log References

### Completion Notes List

### Change Log

### File List
