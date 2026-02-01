# Story 0.8: LLM Cost Tracking Middleware

Status: review

## Story

As a **business owner**,
I want **per-request LLM cost tracking**,
so that **I can monitor costs and maintain margin targets**.

## Acceptance Criteria

1. **AC1 - Cost Recording:** Given an LLM request is made, when the request completes, then token count (input + output) and cost are recorded with user_id.

2. **AC2 - Monthly Aggregation:** Given costs are tracked, when aggregated, then costs are summed per user per month in Redis.

3. **AC3 - Budget Alert:** Given a user's monthly spend, when it reaches 80% of $6 budget, then an alert is published via Redis pub/sub.

4. **AC4 - Admin Dashboard:** Given admin access, when `GET /api/v1/admin/llm-costs` is called, then it returns: total cost today/month, per-user breakdown, projected month-end cost.

## Tasks / Subtasks

- [x] Task 1: Add per-agent cost breakdown to admin endpoint (AC: #4)
  - [x] 1.1: Add `agent_type` parameter to `track_llm_cost()` function
  - [x] 1.2: Store per-agent cost breakdown in Redis hash alongside user totals
  - [x] 1.3: Include per-agent breakdown in `get_all_costs_summary()` response

- [x] Task 2: Write comprehensive cost tracking tests (AC: #1-#4)
  - [x] 2.1: Create `backend/tests/unit/test_observability/__init__.py` (already exists from 0-7)
  - [x] 2.2: Create `backend/tests/unit/test_observability/test_cost_tracker.py`
  - [x] 2.3: Test track_llm_cost records cost correctly with Redis pipeline
  - [x] 2.4: Test monthly key format and TTL setting
  - [x] 2.5: Test budget alert fires at 80% threshold via pub/sub
  - [x] 2.6: Test get_user_monthly_cost returns correct summary
  - [x] 2.7: Test get_all_costs_summary returns aggregate with projection
  - [x] 2.8: Test cost calculation for known models (gpt-4o, claude-3-sonnet)
  - [x] 2.9: Test fallback pricing for unknown models
  - [x] 2.10: Test graceful degradation when Redis unavailable

## Dev Notes

### Architecture Compliance

**CRITICAL — Cost tracker is ALREADY FULLY IMPLEMENTED:**

1. **cost_tracker.py EXISTS:** `backend/app/observability/cost_tracker.py` with complete implementation:
   - `track_llm_cost()` — records cost via Redis pipeline, publishes budget alert
   - `get_user_monthly_cost()` — returns per-user monthly summary
   - `get_all_costs_summary()` — scans all users, aggregates, projects month-end
   - Model pricing table for OpenAI and Anthropic models
   - 80% of $6 budget alert via Redis pub/sub
   - Redis key schema: `llm_cost:{user_id}:{YYYY-MM}` with 35-day TTL
   [Source: backend/app/observability/cost_tracker.py]

2. **Admin endpoint EXISTS:** `GET /api/v1/admin/llm-costs` in admin.py calls `get_all_costs_summary()`
   [Source: backend/app/api/v1/admin.py:18-26]

**WHAT'S MISSING:**
- No per-agent breakdown (epic requires "per-agent breakdown" in admin response)
- No `agent_type` parameter in `track_llm_cost()`
- No tests for any cost tracking functionality

### Previous Story Intelligence (0-7)

- Test directory `backend/tests/unit/test_observability/` already exists with __init__.py
- 14 OTel tracing tests passing
- Mock pattern: unittest.mock.patch for Redis operations

### Technical Requirements

**Per-Agent Breakdown:**
Add optional `agent_type` param to `track_llm_cost()`. When provided, also increment a per-agent counter in the same Redis hash:
```
llm_cost:{user_id}:{YYYY-MM}  ->  Hash {
    total_cost: "0.0342"
    total_input: "12450"
    total_output: "3210"
    calls: "17"
    agent:job_scout:cost: "0.02"     # NEW
    agent:job_scout:calls: "10"      # NEW
    agent:resume:cost: "0.0142"      # NEW
    agent:resume:calls: "7"          # NEW
}
```

### Library/Framework Requirements

**No new dependencies needed.**

### File Structure Requirements

**Files to CREATE:**
```
backend/tests/unit/test_observability/test_cost_tracker.py
```

**Files to MODIFY:**
```
backend/app/observability/cost_tracker.py   # Add agent_type param, per-agent breakdown
```

**Files to NOT TOUCH:**
```
backend/app/api/v1/admin.py                 # Already has /llm-costs endpoint
backend/app/observability/tracing.py        # Separate OTel tracing
backend/app/observability/langfuse_client.py # Separate LLM observability
```

### Testing Requirements

- **Backend Framework:** Pytest + pytest-asyncio
- **Mocking:** Mock redis.asyncio with unittest.mock.AsyncMock
- **Tests to write:**
  - Cost calculation: gpt-4o (input=1000, output=500) → correct USD amount
  - Cost calculation: unknown model uses fallback pricing
  - track_llm_cost: calls Redis pipeline with hincrbyfloat, hincrby, expire
  - track_llm_cost: includes agent_type counters when provided
  - Monthly key format: `llm_cost:{user_id}:{YYYY-MM}`
  - Budget alert: publishes to `alerts:cost:{user_id}` when ≥ 80% of $6
  - Budget alert: does NOT publish when below threshold
  - get_user_monthly_cost: returns correct summary dict
  - get_user_monthly_cost: returns zeros for new user
  - get_all_costs_summary: scans keys, aggregates, includes projection
  - Graceful degradation: Redis failure doesn't raise, returns cost anyway

### References

- [Source: backend/app/observability/cost_tracker.py] — Full implementation
- [Source: backend/app/api/v1/admin.py:18-26] — Admin endpoint
- [Source: backend/app/config.py:36] — REDIS_URL setting

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
SIMPLE (score: 2/16) — direct execution, no GSD subagents

### Debug Log References
- Mock fix: `mock_redis.pipeline` needed to be `MagicMock` (not `AsyncMock`) since `redis.asyncio.Redis.pipeline()` is synchronous and returns an async context manager

### Completion Notes List
- Added `agent_type` optional parameter to `track_llm_cost()` with per-agent Redis hash fields (`agent:{type}:cost`, `agent:{type}:calls`)
- Updated `get_all_costs_summary()` to aggregate per-agent breakdown from Redis hash fields
- Updated docstring with per-agent Redis key schema
- Created 21 comprehensive tests covering: cost calculation, month key format, pipeline recording, agent_type tracking, budget alerts, user/admin summaries, graceful degradation, constants

### Change Log
- 2026-02-01: Implemented per-agent cost breakdown + 21 tests

### File List
**Modified:**
- `backend/app/observability/cost_tracker.py` — agent_type param, per-agent breakdown
- `backend/tests/unit/test_observability/test_cost_tracker.py` — 21 tests

**Created:**
- `backend/tests/unit/test_observability/test_cost_tracker.py`
