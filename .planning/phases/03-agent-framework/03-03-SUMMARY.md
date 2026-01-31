---
phase: 03-agent-framework
plan: 03
subsystem: agents
tags: [baseagent, tier-enforcement, emergency-brake, redis, asyncio, state-machine, decorator]

# Dependency graph
requires:
  - phase: 03-agent-framework/01
    provides: ADR-1 decision (Custom orchestrator pattern)
  - phase: 03-agent-framework/02
    provides: AgentOutput, ApprovalQueueItem, AgentActivity, Briefing SQLAlchemy models
  - phase: 01-foundation-modernization/04
    provides: FastAPI app factory, Redis config
  - phase: 01-foundation-modernization/05
    provides: Celery worker with queue routing
  - phase: 01-foundation-modernization/08
    provides: WebSocket pub/sub infrastructure (publish_agent_event)
provides:
  - BaseAgent class with run/execute/record/publish lifecycle
  - AgentOutput dataclass (action, rationale, confidence, alternatives, data)
  - BrakeActive and TierViolation exception classes
  - @requires_tier() decorator with L0-L3 enforcement
  - AutonomyGate class for programmatic tier checks
  - Emergency brake state machine (RUNNING/PAUSING/PAUSED/PARTIAL/RESUMING)
  - check_brake(), activate_brake(), resume_agents(), verify_brake_completion()
affects: [03-agent-framework/04, 03-agent-framework/05, 03-agent-framework/06, 03-agent-framework/08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Custom orchestrator pattern (ADR-1) -- plain Python classes, no LangGraph"
    - "Brake-first safety: brake checked before tier enforcement in all paths"
    - "Lazy imports in agent methods to avoid circular dependencies"
    - "Redis hash for brake state machine, simple key for fast brake flag check"
    - "Fire-and-forget persistence: record/publish failures logged but never break hot path"

key-files:
  created:
    - backend/app/agents/__init__.py
    - backend/app/agents/base.py
    - backend/app/agents/tier_enforcer.py
    - backend/app/agents/brake.py
  modified: []

key-decisions:
  - "BaseAgent.run() raises BrakeActive instead of returning blocked output -- callers must handle exception"
  - "Brake state stored as Redis hash (brake_state:{user_id}) with separate simple flag (paused:{user_id}) for fast checks"
  - "verify_brake_completion uses Celery inspect API (best-effort) -- assumes stopped if broker unreachable"
  - "AutonomyGate.check() returns string literals not enums -- simpler for callers to match on"

patterns-established:
  - "Agent lifecycle: run() -> brake check -> execute() -> _record_output() -> _record_activity() -> _publish_event()"
  - "Tier decorator: @requires_tier(min_tier, action_type) on async agent methods"
  - "Approval queue: _queue_for_approval() creates ApprovalQueueItem with 48h expiry + publishes WS event"
  - "Redis event schema: {type, event_id, timestamp, user_id, agent_type, title, severity, data}"

# Metrics
duration: 5min
completed: 2026-01-31
---

# Phase 3 Plan 03: BaseAgent + Tier Enforcement + Brake Module Summary

**Custom orchestrator agent base with L0-L3 tier decorator, AutonomyGate class, and Redis-backed emergency brake state machine (RUNNING/PAUSING/PAUSED/PARTIAL/RESUMING)**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-31T09:07:47Z
- **Completed:** 2026-01-31T09:12:21Z
- **Tasks:** 3/3
- **Files created:** 4

## Accomplishments
- BaseAgent class with full run/execute/record/publish lifecycle following the ADR-1 Custom pattern
- Tier enforcement decorator covering all 4 autonomy levels: L0 (suggest only), L1 (read only), L2 (writes queue for approval), L3 (autonomous)
- Emergency brake state machine with Redis flag for fast checks and hash for full state tracking
- Brake verification via Celery inspect after 30s with PAUSED/PARTIAL transition

## Task Commits

Each task was committed atomically:

1. **Task 1: Create agent base module** - `c428b59` (feat)
2. **Task 2: Create tier enforcement module** - `03cc7e5` (feat)
3. **Task 3: Create brake module** - `a628ea3` (feat)

## Files Created/Modified
- `backend/app/agents/__init__.py` - Package init, exports BaseAgent, AgentOutput, BrakeActive, TierViolation
- `backend/app/agents/base.py` - BaseAgent class with run/execute lifecycle, AgentOutput dataclass, exception classes
- `backend/app/agents/tier_enforcer.py` - @requires_tier() decorator and AutonomyGate class for L0-L3 enforcement
- `backend/app/agents/brake.py` - Emergency brake state machine with check/activate/resume/verify functions

## Decisions Made
- BaseAgent.run() raises BrakeActive exception rather than returning a blocked AgentOutput -- keeps the interface clean and forces callers to handle brake state explicitly
- Brake state uses two Redis structures: simple `paused:{user_id}` flag for O(1) checks (called on every agent step), and `brake_state:{user_id}` hash for full state machine data (activated_at, stuck_tasks)
- verify_brake_completion uses Celery's inspect API which is best-effort -- if the broker is unreachable, assumes tasks have stopped (optimistic)
- AutonomyGate returns plain string literals ("execute", "suggest", "queue_approval", "blocked") instead of enums for simpler pattern matching by callers

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Python sandbox restrictions prevented running import verification commands -- all files were verified via syntax review and line count checks instead

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- BaseAgent, tier enforcer, and brake module are ready for use by Plan 04 (Orchestrator) and Plan 05 (Briefing Pipeline)
- Plan 06 (Emergency Brake Frontend) can call activate_brake/resume_agents/get_brake_state via API endpoints
- Plan 08 (Integration Tests) can test all tier enforcement behaviors and brake state transitions

---
*Phase: 03-agent-framework*
*Completed: 2026-01-31*
