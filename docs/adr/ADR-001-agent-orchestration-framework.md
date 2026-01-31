# ADR-001: Agent Orchestration Framework

**Status:** DECIDED
**Date:** 2026-01-31
**Decision:** Custom orchestrator (plain Python + Celery)

## Context

JobPilot requires an agent orchestration layer that supports:

- **Tiered autonomy (L0-L3):** L0 users receive suggestions only; L1 can read but not write; L2 write actions queue for approval; L3 executes autonomously.
- **Emergency brake:** User presses a button and all agent activity pauses within 30 seconds.
- **Approval queue:** L2 write actions persist to a database table, user approves/rejects, agent resumes.
- **Crash recovery:** If a Celery worker dies mid-task, the work is not lost.
- **Observability:** Per-user cost tracking, multi-step trace visualization via Langfuse.
- **Real-time activity feed:** WebSocket events for agent status updates.

Two approaches were prototyped: LangGraph (graph-based state machine) and Custom (plain Python classes with decorators).

## Prototypes Built

### LangGraph Prototype (`backend/app/agents/_prototype_langgraph.py`)

- `StateGraph` with 5 nodes: `check_brake`, `check_tier`, `execute`, `await_approval`, `record_output`
- `interrupt()` for emergency brake pause and L2 approval flow
- `Command(resume=)` to continue after approval decision
- `MemorySaver` for in-memory checkpointing (would use `PostgresSaver` in production)
- Conditional edges route by tier

### Custom Prototype (`backend/app/agents/_prototype_custom.py`)

- `BaseAgent` class with `run()` -> `execute()` -> `_record_output()` -> `_publish_event()` pattern
- `requires_tier()` decorator enforcing brake check (always first) then tier routing
- `AgentOutput` dataclass as standard output format
- `BrakeActive` and `TierViolation` exception classes
- Approval queue via database table insert + WebSocket notification

## Evaluation

| Criterion | Weight | LangGraph | Custom | Winner |
|-----------|--------|-----------|--------|--------|
| **Brake propagation** | HIGH | `interrupt()` + Redis check. Elegant but interrupt only pauses between nodes, not mid-node. | Redis check in decorator + `check_brake_or_raise()` helper called between every logical step. Identical latency. | **Tie** |
| **L2 approval flow** | HIGH | `interrupt()` + `Command(resume=)` auto-persists state. Resumption is a single API call. Very clean. | DB table insert + WebSocket notification + resume endpoint. Must serialize/deserialize action context manually. ~30 lines more code. | **LangGraph** |
| **L0 suggestion-only** | HIGH | Conditional edge routing. Works but requires understanding graph edge semantics. | Decorator modifies `output.action` prefix. Immediately readable. | **Custom** |
| **Worker crash recovery** | MEDIUM | `PostgresSaver` auto-persists state on every node transition. Free crash recovery. | Celery `acks_late` + `reject_on_worker_lost` (already configured in Phase 1). Message returns to queue on crash. Agent re-runs from start, not from last checkpoint. | **LangGraph** (marginal) |
| **Developer ergonomics** | MEDIUM | Must learn StateGraph, nodes, edges, conditional routing, TypedDict state, interrupt/Command API. Steeper onboarding. | Plain Python: dataclass, decorator, async class. Any Python developer can read and modify immediately. | **Custom** |
| **Dependency footprint** | LOW | Adds ~100MB: langgraph, langchain-core, langchain-openai, psycopg3. Introduces second PostgreSQL driver (psycopg3) alongside asyncpg. | Zero additional dependencies. Uses existing asyncpg, Redis, Celery. | **Custom** |
| **Test determinism** | HIGH | Must mock graph state, checkpointer, and interrupt/resume flow. Graph execution is opaque. | Mock plain functions. `requires_tier()` is a standard Python decorator testable with `pytest`. | **Custom** |
| **Celery integration** | HIGH | Graph runs inside Celery task. Entire graph is one unit of work. But PostgresSaver needs its own connection pool (psycopg3), separate from app pool (asyncpg). | Agent runs inside Celery task natively. Same async patterns, same connection pool. No impedance mismatch. | **Custom** |

### Score Summary

- **Custom wins:** 4 criteria (L0 enforcement, ergonomics, dependency footprint, test determinism, Celery integration)
- **LangGraph wins:** 1 criterion (L2 approval flow -- but the delta is ~30 lines of code, not a fundamental limitation)
- **LangGraph marginal win:** 1 criterion (crash recovery -- but Celery already provides task-level retry which is sufficient for our use case)
- **Tie:** 1 criterion (brake propagation)

## Decision

**Use Custom orchestrator (plain Python + Celery).** Do not adopt LangGraph.

### Rationale

1. **The approval queue delta is small.** LangGraph's `interrupt()/Command(resume=)` is elegant, but our approval flow is: insert row in `approval_queue` table, send WebSocket notification, user approves via API endpoint, Celery task re-dispatches the action. This is ~30 lines of code that we fully control and can test with standard pytest. The Phase 1 infrastructure (WebSocket pub/sub, Celery task dispatch) already supports this pattern.

2. **Dual PostgreSQL driver is a real problem.** LangGraph's `PostgresSaver` requires psycopg3. Our app uses asyncpg via SQLAlchemy. Running two PostgreSQL drivers against the same Supabase instance means:
   - Two connection pools competing for Supabase's limited connection slots
   - Two sets of connection configuration to maintain
   - Potential for subtle bugs when both drivers interact with the same tables
   - Increased memory footprint per worker process

3. **Celery already provides crash recovery.** Our Celery configuration (Phase 1, Plan 05) includes `acks_late=True`, `reject_on_worker_lost=True`, and `prefetch_multiplier=1`. If a worker dies, the message returns to the queue and is retried. This is task-level recovery, not step-level (LangGraph's advantage), but for our agents (which are single LLM call + DB write), task-level is sufficient.

4. **Developer ergonomics matter for a solo/small team.** The Custom approach uses patterns every Python developer knows: decorators, dataclasses, async/await, exceptions. LangGraph requires learning a new mental model (StateGraph, nodes, edges, TypedDict state, interrupt semantics). The learning curve is not justified given the small delta in functionality.

5. **No lock-in.** The Custom approach can be replaced with LangGraph later if requirements change (e.g., multi-agent coordination becomes complex enough to warrant it). The `BaseAgent` interface is framework-agnostic.

### What We Lose

- **Automatic state checkpointing:** If an agent needs to resume from an intermediate step (not just retry from start), we must build that manually. For MVP agents (single LLM call + action), this is not needed. Revisit if agents become multi-step pipelines.
- **Graph visualization:** LangGraph Studio provides visual debugging of agent flows. We lose this but gain standard Python debugging (pdb, logging, stack traces).
- **Built-in multi-agent coordination:** LangGraph's `Send` API enables fan-out/fan-in patterns. If we need this, we can use Celery `group()` and `chord()` which are already available.

### What We Keep (from LangGraph research)

Even though we chose Custom, LangGraph research informed these patterns that we will implement:

- **Brake check before every logical step** (from LangGraph's per-node entry check pattern)
- **Typed state/output** (`AgentOutput` dataclass, inspired by LangGraph's `TypedDict` state)
- **Explicit trace creation in Celery tasks** (from Langfuse integration research, applicable to both approaches)

## Consequences

1. **Remove LangGraph dependencies** from `requirements.txt` (langgraph, langgraph-checkpoint-postgres, psycopg, langchain-core, langchain-openai)
2. **Build approval queue** as DB table + REST endpoints + WebSocket notification (Plan 02-05)
3. **Build BaseAgent** using Custom prototype pattern (Plan 03)
4. **Keep prototype files** as reference (`_prototype_langgraph.py`, `_prototype_custom.py`) -- do not import in production code
5. **Revisit if:** Agent workflows become multi-step pipelines requiring intermediate checkpointing, or multi-agent coordination requires graph-level orchestration beyond what Celery group/chord provides

## References

- Prototype files: `backend/app/agents/_prototype_langgraph.py`, `backend/app/agents/_prototype_custom.py`
- Phase 3 Research: `.planning/phases/03-agent-framework/RESEARCH.md`
- Celery reliability config: `backend/app/worker/celery_app.py` (acks_late, reject_on_worker_lost)
- Existing async DB engine: `backend/app/db/engine.py` (asyncpg, no psycopg3)
