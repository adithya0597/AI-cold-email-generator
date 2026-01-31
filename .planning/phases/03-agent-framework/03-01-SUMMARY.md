---
phase: "03"
plan: "01"
subsystem: agent-orchestration
tags: [adr, langgraph, custom-agent, prototype, architecture-decision]
depends_on:
  requires: ["01-05"]  # Celery worker config (acks_late, queue routing)
  provides: ["ADR-1-decision", "BaseAgent-pattern", "agent-output-dataclass"]
  affects: ["03-02", "03-03", "03-04", "03-05", "03-06", "03-07", "03-08"]
tech_stack:
  added: [langfuse, celery-redbeat, vcrpy, pytest-recording]
  removed: [langgraph, langgraph-checkpoint-postgres, psycopg3, langchain-core, langchain-openai]
  patterns: [custom-agent-base, tier-decorator, brake-check-first]
key_files:
  created:
    - backend/app/agents/_prototype_langgraph.py
    - backend/app/agents/_prototype_custom.py
    - docs/adr/ADR-001-agent-orchestration-framework.md
  modified:
    - backend/requirements.txt
decisions:
  - id: ADR-1
    decision: "Custom orchestrator over LangGraph"
    rationale: "Simpler, no dual PG driver, Celery already handles crash recovery, ~30 lines delta for approval queue"
metrics:
  duration: "4 min"
  completed: "2026-01-31"
---

# Phase 3 Plan 01: ADR-1 Prototype -- LangGraph vs Custom Orchestrator Summary

**Custom orchestrator chosen over LangGraph for agent orchestration. Zero additional framework dependencies; Celery + plain Python + decorator-based tier enforcement.**

## What Was Done

### Task 1: Add Prototype Dependencies
- Added LangGraph prototype deps in clearly-marked section to `requirements.txt`
- Added shared Phase 3 deps: langfuse, celery-redbeat, vcrpy, pytest-recording
- Commit: `c3531f0`

### Task 2: LangGraph Prototype
- Built `_prototype_langgraph.py` with full StateGraph implementation
- 5 nodes: check_brake, check_tier, execute, await_approval, record_output
- Used `interrupt()` for brake and L2 approval, `Command(resume=)` for approval decisions
- MemorySaver for in-memory checkpointing
- 4 demo scenarios covering L0/L2/L3/braked paths
- Commit: `7e98427`

### Task 3: Custom Prototype
- Built `_prototype_custom.py` with BaseAgent class and decorator pattern
- `requires_tier()` decorator with brake-first safety check
- `AgentOutput` dataclass as standard output format
- `BrakeActive` and `TierViolation` exception classes
- 5 demo scenarios including brake-before-tier ordering verification
- Commit: `ca8aa18`

### Task 4: Evaluate and Write ADR-1
- Evaluated both prototypes across 8 criteria with weighted scoring
- Custom wins: 4+ criteria (ergonomics, test determinism, deps, Celery integration)
- LangGraph wins: 1 criterion (L2 approval elegance -- ~30 lines delta)
- Wrote comprehensive ADR-001 at `docs/adr/ADR-001-agent-orchestration-framework.md`
- Removed LangGraph deps from requirements.txt
- Commit: `f468e36`

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| ADR-1: Custom over LangGraph | Simpler, no dual PG driver issue, Celery crash recovery sufficient, better testing, ~30 LOC delta for approval queue | All subsequent Phase 3 plans use Custom BaseAgent pattern |
| Keep prototype files | Reference for future re-evaluation if agents become multi-step pipelines | Prototype files remain but are not imported by production code |
| Remove LangGraph deps immediately | No value keeping unused framework dependencies | Cleaner dependency tree, no psycopg3/asyncpg conflict risk |

## Deviations from Plan

None -- plan executed exactly as written.

## Verification

- ADR-001 document exists with DECIDED status and clear rationale
- `requirements.txt` has no LangGraph dependencies
- Both prototype files exist as reference
- Shared Phase 3 dependencies (langfuse, celery-redbeat, vcrpy, pytest-recording) remain in requirements.txt

## Next Phase Readiness

ADR-1 is resolved. All subsequent Phase 3 plans can proceed:
- **Plan 02** (DB Schema): Can define agent models without LangGraph-specific fields
- **Plan 03** (BaseAgent): Will use Custom prototype pattern directly
- **Plans 04-08**: All build on Custom orchestrator foundation
