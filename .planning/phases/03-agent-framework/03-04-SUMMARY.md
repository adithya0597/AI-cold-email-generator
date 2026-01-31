---
phase: 03
plan: 04
subsystem: agent-orchestration
tags: [orchestrator, langfuse, celery, observability, task-routing]
depends_on:
  requires: [03-01, 03-02, 03-03]
  provides: [orchestrator-routing, langfuse-tracing, agent-celery-tasks]
  affects: [03-05, 03-06, 03-08]
tech_stack:
  added: [langfuse]
  patterns: [deterministic-routing, explicit-celery-traces, lazy-langfuse-init, noop-fallback]
key_files:
  created:
    - backend/app/agents/orchestrator.py
    - backend/app/observability/langfuse_client.py
  modified:
    - backend/app/config.py
    - backend/app/worker/tasks.py
decisions:
  - "Orchestrator is module-level singleton with TaskRouter class + dispatch_task function"
  - "Langfuse client uses lazy initialization with NoOp fallback when SDK unavailable"
  - "cost_tracker.py kept as fallback for 1 sprint -- Langfuse is primary"
  - "Each Celery agent task creates explicit Langfuse trace (contextvars pitfall)"
  - "cleanup_expired_approvals runs every 6 hours via Celery beat"
  - "apply tasks limited to 1 retry (non-idempotent); other agents get 2 retries"
metrics:
  duration: ~4 min
  completed: 2026-01-31
---

# Phase 3 Plan 04: Orchestrator + Langfuse Observability Summary

Deterministic task router, Langfuse LLM tracing replacing cost_tracker, and agent Celery tasks with explicit trace creation for cross-process observability.

## What Was Built

### Task 1: Orchestrator Module
- **TaskRouter** class with deterministic `task_type -> Celery task name` mapping (job_scout, resume, apply, briefing)
- **dispatch_task()** async function: checks brake, validates autonomy tier via AutonomyGate, routes to Celery, logs routing decision to agent_activities
- **get_user_context()** loads shared memory (profile, preferences, last 10 outputs) with 5-minute Redis cache TTL
- All routing decisions recorded to agent_activities table for debugging

### Task 2: Langfuse Observability Client
- Added `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` to Settings
- Lazy-initialized Langfuse singleton with `_NoOpLangfuse` fallback when SDK unavailable or keys missing
- `create_agent_trace()` helper solves the Celery contextvars propagation pitfall -- each task creates fresh trace
- `flush_traces()` for Celery task `finally` blocks
- Existing `cost_tracker.py` preserved as fallback (will be removed in ~1 sprint)

### Task 3: Agent Celery Tasks
- `agent_job_scout` (Phase 4 placeholder), `agent_resume` (Phase 5), `agent_apply` (Phase 8) -- all on `agents` queue
- `briefing_generate` on `briefings` queue (Plan 05 will wire the generator)
- `verify_brake_completion` on `default` queue -- wired to brake module
- `cleanup_expired_approvals` periodic task (every 6 hours via beat_schedule)
- Each agent task follows the pattern: create_agent_trace -> try/execute -> trace.update -> finally flush_traces

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | `1831164` | Orchestrator task router module |
| 2 | `250e84f` | Langfuse client + config settings |
| 3 | `64bc937` | Agent Celery tasks with Langfuse tracing |

## Decisions Made

1. **Orchestrator as module singleton**: TaskRouter is a class but instantiated once at module level. `dispatch_task()` and `get_user_context()` are module-level async functions. No need for a class instance to be passed around.

2. **Lazy Langfuse init with NoOp fallback**: Avoids import-time crashes when langfuse is not installed or keys are missing. `_NoOpLangfuse` and `_NoOpTrace` provide the same interface so callers never need guard clauses.

3. **cost_tracker.py kept**: Per RESEARCH.md recommendation, Langfuse is primary but cost_tracker stays for 1 sprint as fallback. Remove when Langfuse is verified in staging.

4. **Apply agent limited retries**: `agent_apply` has `max_retries=1` (vs 2 for others) because application submission is not idempotent -- retrying could double-submit.

5. **Tier decision for routing**: `apply` is the only "write" action type at the orchestrator level. `job_scout`, `resume`, and `briefing` are treated as "read" for tier checking purposes at the routing layer (individual agents can enforce stricter tier rules internally).

## Deviations from Plan

None -- plan executed exactly as written.

## Next Phase Readiness

Plan 04 provides the routing infrastructure that Plan 05 (briefing pipeline), Plan 06 (brake frontend), and Plan 08 (integration tests) depend on. All agent task stubs are registered and ready for their respective agent implementations in later phases.
