# Phase 3: Agent Framework Core - Research

**Researched:** 2026-01-31
**Domain:** AI agent orchestration, LLM observability, real-time WebSocket, emergency brake state machine, daily briefing pipeline
**Confidence:** MEDIUM-HIGH

## Summary

Phase 3 builds the orchestration infrastructure that every future agent depends on. The key architectural decision (ADR-1: LangGraph vs Custom) shapes the entire agent lifecycle. After deep research, both approaches are viable but present distinct tradeoffs that the 2-day prototype must validate. The existing codebase from Phases 1-2 provides solid foundations: Celery with Redis queue routing, WebSocket with Redis pub/sub, SQLAlchemy async models with `AutonomyLevel` enum, and a cost tracker that will be replaced by Langfuse.

This research covers all 8 key questions and provides prescriptive guidance for each. The primary tension is between LangGraph's production-grade checkpointing/human-in-the-loop primitives and the simplicity of a custom orchestrator that avoids framework lock-in. Both approaches share the same BaseAgent pattern, tier enforcement decorator, and emergency brake check -- the difference is in state persistence and execution flow management.

**Primary recommendation:** Prototype both approaches for 1 day each. LangGraph for the orchestrator+brake+approval flow. Custom for the same. Evaluate based on: code complexity, tier enforcement clarity, brake propagation latency, and developer ergonomics. Whichever wins, the BaseAgent interface, Langfuse integration, and briefing pipeline design remain identical.

## Standard Stack

The established libraries/tools for this phase:

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langgraph` | >=0.3.0 | Agent orchestration graphs (if ADR-1 picks LangGraph) | Built-in checkpointing, interrupt(), human-in-the-loop, multi-agent coordination |
| `langgraph-checkpoint-postgres` | >=3.0.2 | Durable state persistence for LangGraph | PostgresSaver/AsyncPostgresSaver with psycopg3; production-grade crash recovery |
| `langfuse` | >=2.0.0 | LLM observability replacing cost_tracker.py | Per-user cost tracking, multi-step trace visualization, `@observe()` decorator, self-hostable |
| `celery[redis]` | >=5.6.0 | Background task execution | Already installed; queue routing for agents/briefings already configured |
| `celery-redbeat` | >=2.3.3 | Dynamic per-user briefing scheduling | Redis-backed beat scheduler; no Django dependency; supports per-user timezone crontabs |
| `redis` | >=5.2.0 | Broker, cache, pub/sub, emergency brake flags | Already installed and configured |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `langchain-core` | >=0.3.0 | Model wrappers + output parsers (if LangGraph chosen) | Only if LangGraph path wins ADR-1; provides ChatOpenAI/ChatAnthropic |
| `langchain-openai` | >=0.3.0 | OpenAI model wrapper for LangGraph | Only with LangGraph |
| `langchain-anthropic` | >=0.3.0 | Anthropic model wrapper for LangGraph | Only with LangGraph |
| `psycopg[binary,pool]` | >=3.1.0 | PostgreSQL driver for LangGraph checkpointer | Required by langgraph-checkpoint-postgres (uses psycopg3, not asyncpg) |
| `deepeval` | >=1.0.0 | LLM evaluation testing | Agent output quality testing in CI |
| `vcrpy` | >=6.0.0 | Record/replay LLM API calls for deterministic tests | Mock LLM responses in unit/integration tests |
| `pytest-recording` | >=0.13.0 | pytest plugin wrapping VCR.py | Ergonomic cassette management in pytest |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LangGraph | Custom orchestrator (no framework) | Less dependency, more control, but must hand-roll checkpointing, interrupt, and state persistence |
| Langfuse | Keep custom cost_tracker.py | Simpler but lacks trace visualization, multi-step agent traces, evaluation scoring, and prompt management |
| RedBeat | rdbbeat (SQLAlchemy scheduler) | Stores schedules in PostgreSQL instead of Redis; more durable but adds DB writes per schedule tick |
| RedBeat | sqlalchemy-celery-beat | Another SQLAlchemy option; less mature than RedBeat |
| VCR.py | llm-mocks | Purpose-built for LLM testing but smaller ecosystem; VCR.py is battle-tested |

**Installation (LangGraph path):**
```bash
pip install langgraph langgraph-checkpoint-postgres "psycopg[binary,pool]" langchain-core langchain-openai langchain-anthropic langfuse celery-redbeat deepeval vcrpy pytest-recording
```

**Installation (Custom path):**
```bash
pip install langfuse celery-redbeat deepeval vcrpy pytest-recording
```

## Architecture Patterns

### ADR-1: LangGraph vs Custom Orchestrator -- Deep Comparison

This is the most consequential decision in Phase 3. The roadmap mandates a 2-day time-boxed prototype to resolve it.

#### Option A: LangGraph

**How it works:** Define agent workflows as `StateGraph` with typed state dictionaries. Nodes are Python functions. Edges route between nodes. `interrupt()` pauses execution at any point. `PostgresSaver` persists state to the database. `Command(resume=...)` continues from where execution paused.

**BaseAgent in LangGraph:**
```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langfuse.decorator import observe
from typing import TypedDict, Literal
import enum

class AgentState(TypedDict):
    user_id: str
    user_tier: str  # "l0", "l1", "l2", "l3"
    is_braked: bool
    task_type: str
    input_data: dict
    output: dict | None
    rationale: str
    confidence: float
    alternatives_considered: list[str]
    requires_approval: bool

class BaseAgentGraph:
    """Base class for all agent graphs. Subclasses define specific nodes."""

    def __init__(self, checkpointer: AsyncPostgresSaver):
        self.checkpointer = checkpointer

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        # Common nodes every agent has
        graph.add_node("check_brake", self.check_brake)
        graph.add_node("check_tier", self.check_tier)
        graph.add_node("execute", self.execute)  # Subclass overrides
        graph.add_node("await_approval", self.await_approval)
        graph.add_node("record_output", self.record_output)

        # Flow: brake check -> tier check -> execute or approval -> record
        graph.set_entry_point("check_brake")
        graph.add_edge("check_brake", "check_tier")
        graph.add_conditional_edges("check_tier", self.route_by_tier)
        graph.add_edge("execute", "record_output")
        graph.add_edge("await_approval", "record_output")
        graph.add_edge("record_output", END)

        return graph

    async def check_brake(self, state: AgentState) -> AgentState:
        """Check emergency brake before any work."""
        import redis.asyncio as aioredis
        from app.config import settings
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        is_braked = await r.exists(f"paused:{state['user_id']}")
        await r.aclose()
        if is_braked:
            from langgraph.types import interrupt
            interrupt({"reason": "emergency_brake_active"})
        return state

    def route_by_tier(self, state: AgentState) -> Literal["execute", "await_approval"]:
        """L2 write actions go to approval; everything else executes."""
        if state["user_tier"] == "l2" and state.get("requires_approval"):
            return "await_approval"
        return "execute"

    async def await_approval(self, state: AgentState) -> AgentState:
        """Pause for human approval (L2 tier)."""
        from langgraph.types import interrupt
        decision = interrupt({
            "action": "approval_required",
            "proposed_action": state["output"],
            "rationale": state["rationale"],
        })
        # decision comes back from Command(resume={"approved": True/False})
        if not decision.get("approved"):
            state["output"] = None
            state["rationale"] = "Rejected by user"
        return state

    @observe(as_type="generation")
    async def execute(self, state: AgentState) -> AgentState:
        """Override in subclass with actual agent logic."""
        raise NotImplementedError

    async def record_output(self, state: AgentState) -> AgentState:
        """Persist to agent_outputs table."""
        # Lazy import
        from app.db.engine import AsyncSessionLocal
        from app.db.models import AgentOutput
        async with AsyncSessionLocal() as session:
            output = AgentOutput(
                agent_type=state["task_type"],
                user_id=state["user_id"],
                output=state["output"] or {},
                schema_version=1,
            )
            session.add(output)
            await session.commit()
        return state

    def compile(self):
        graph = self._build_graph()
        return graph.compile(checkpointer=self.checkpointer)
```

**LangGraph Pros:**
- `interrupt()` is first-class for L2 approval queue -- state persists automatically, resumes cleanly
- `PostgresSaver` handles crash recovery -- if Celery worker dies, agent state survives
- Checkpointing gives free audit trail of every state transition
- Multi-agent orchestrator pattern is built-in via `Send` API
- LangGraph Studio provides visual debugging of agent flows

**LangGraph Cons:**
- Adds ~100MB dependency tree (langchain-core + langgraph + checkpoint libs)
- Uses psycopg3 for checkpointer while codebase uses asyncpg -- two PostgreSQL drivers
- Learning curve for StateGraph/edge/node model
- Lock-in to LangChain ecosystem for agent structure
- Rollback/monitoring challenges reported in production by multiple teams

#### Option B: Custom Orchestrator

**How it works:** Plain Python classes with a decorator-based tier enforcement pattern. State is managed explicitly via database reads/writes. Emergency brake is a Redis flag check before each logical step. Approval queue is a database table with polling or WebSocket notification.

**BaseAgent in Custom:**
```python
from functools import wraps
from typing import Any
from dataclasses import dataclass, field
from langfuse.decorator import observe
import redis.asyncio as aioredis

from app.config import settings
from app.db.models import AutonomyLevel


@dataclass
class AgentOutput:
    """Standard output every agent must produce."""
    action: str
    rationale: str
    confidence: float
    alternatives_considered: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)
    requires_approval: bool = False


class BrakeActive(Exception):
    """Raised when emergency brake is active."""
    pass


class TierViolation(Exception):
    """Raised when action requires higher tier."""
    pass


async def check_brake(user_id: str) -> bool:
    """Check if emergency brake is active for user."""
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    result = await r.exists(f"paused:{user_id}")
    await r.aclose()
    return bool(result)


def requires_tier(min_tier: str, action_type: str = "read"):
    """Decorator enforcing autonomy tier before agent action."""
    tier_order = {"l0": 0, "l1": 1, "l2": 2, "l3": 3}

    def decorator(func):
        @wraps(func)
        async def wrapper(self, user_id: str, *args, **kwargs):
            # Always check brake first
            if await check_brake(user_id):
                raise BrakeActive(f"Emergency brake active for {user_id}")

            # Get user tier
            from app.db.engine import AsyncSessionLocal
            from app.db.models import UserPreference
            from sqlalchemy import select
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(UserPreference.autonomy_level)
                    .where(UserPreference.user_id == user_id)
                )
                user_tier = result.scalar_one_or_none() or "l0"

            user_level = tier_order.get(user_tier, 0)
            required_level = tier_order.get(min_tier, 0)

            if user_level < required_level:
                raise TierViolation(
                    f"Action requires {min_tier}, user has {user_tier}"
                )

            # L2 write actions queue for approval instead of executing
            if user_tier == "l2" and action_type == "write":
                return await self._queue_for_approval(
                    user_id, func.__name__, args, kwargs
                )

            return await func(self, user_id, *args, **kwargs)
        return wrapper
    return decorator


class BaseAgent:
    """Base class for all JobPilot agents."""

    agent_type: str = "base"

    @observe()
    async def run(self, user_id: str, task_data: dict) -> AgentOutput:
        """Main entry point. Subclasses override execute()."""
        if await check_brake(user_id):
            return AgentOutput(
                action="blocked",
                rationale="Emergency brake is active",
                confidence=1.0,
            )
        output = await self.execute(user_id, task_data)
        await self._record_output(user_id, output)
        await self._publish_event(user_id, output)
        return output

    async def execute(self, user_id: str, task_data: dict) -> AgentOutput:
        """Override in subclass."""
        raise NotImplementedError

    async def _record_output(self, user_id: str, output: AgentOutput):
        from app.db.engine import AsyncSessionLocal
        from app.db.models import AgentOutput as AgentOutputModel
        async with AsyncSessionLocal() as session:
            record = AgentOutputModel(
                agent_type=self.agent_type,
                user_id=user_id,
                output={"action": output.action, "rationale": output.rationale,
                        "confidence": output.confidence, "data": output.data},
                schema_version=1,
            )
            session.add(record)
            await session.commit()

    async def _publish_event(self, user_id: str, output: AgentOutput):
        """Push real-time update via Redis pub/sub."""
        import json
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.publish(
            f"agent:status:{user_id}",
            json.dumps({
                "type": f"agent.{self.agent_type}.completed",
                "action": output.action,
                "rationale": output.rationale,
            })
        )
        await r.aclose()

    async def _queue_for_approval(self, user_id, action_name, args, kwargs):
        """Store pending action in approval_queue table."""
        import json
        from app.db.engine import AsyncSessionLocal
        from app.db.models import ApprovalQueueItem
        async with AsyncSessionLocal() as session:
            item = ApprovalQueueItem(
                user_id=user_id,
                agent_type=self.agent_type,
                action_name=action_name,
                payload=json.dumps({"args": list(args), "kwargs": kwargs}),
                status="pending",
            )
            session.add(item)
            await session.commit()
        return AgentOutput(
            action="queued_for_approval",
            rationale=f"{action_name} requires L2 approval",
            confidence=1.0,
            requires_approval=True,
        )
```

**Custom Pros:**
- Zero framework dependency beyond what exists
- Tier enforcement is explicit, readable, and testable as plain decorators
- No dual PostgreSQL driver issue (stays on asyncpg)
- Full control over state, no hidden behavior
- Easier to onboard new developers -- plain Python

**Custom Cons:**
- Must hand-roll approval queue persistence and resume logic
- No automatic checkpointing -- if worker dies mid-task, state is lost unless manually saved
- No graph visualization or debugging tools
- Must build interrupt/resume semantics for approval flow manually
- Every pattern LangGraph provides for free must be tested independently

#### Prototype Evaluation Criteria

| Criterion | Weight | LangGraph Signal | Custom Signal |
|-----------|--------|-----------------|---------------|
| Brake propagation latency (<30s) | HIGH | interrupt() + Redis check | Redis check in decorator |
| L2 approval flow clarity | HIGH | interrupt() + Command(resume=) | DB table + poll/WebSocket |
| L0 suggestion-only enforcement | HIGH | Conditional edge routing | Decorator return |
| Worker crash recovery | MEDIUM | PostgresSaver auto-recovery | Must implement manually |
| Developer ergonomics | MEDIUM | Graph definition complexity | Plain Python clarity |
| Dependency footprint | LOW | ~100MB added | Zero added |
| Test determinism | HIGH | Mock graph state | Mock function calls |

### Recommended Project Structure

```
backend/app/
  agents/
    __init__.py
    base.py             # BaseAgent class + AgentOutput dataclass
    orchestrator.py     # Task router (code-based, NOT LLM-based routing)
    state.py            # AgentState TypedDict (if LangGraph) or state helpers
    tier_enforcer.py    # AutonomyGate decorator + tier logic
    brake.py            # Emergency brake check/set/clear functions
  agents/briefing/
    __init__.py
    generator.py        # BriefingGenerator -- aggregates agent data + LLM summary
    scheduler.py        # RedBeat schedule management per user
    delivery.py         # Email + in-app delivery
    fallback.py         # Lite briefing from cache
  worker/
    celery_app.py       # (exists) Celery config
    tasks.py            # (exists) Add agent_*, briefing_* tasks
    beat_schedules.py   # RedBeat dynamic schedule helpers
  api/v1/
    ws.py               # (exists) WebSocket agent status feed
    agents.py           # Agent control endpoints (brake, resume, activity)
    briefings.py        # Briefing retrieval + settings endpoints
    approvals.py        # Approval queue endpoints (list, approve, reject)
  db/
    models.py           # (exists) Add Briefing, ApprovalQueueItem models
```

### Pattern: Emergency Brake State Machine

**States:** RUNNING -> PAUSING -> PAUSED -> RESUMING -> RUNNING
Additional terminal: PARTIAL (some tasks failed to pause)

```python
# State machine stored in Redis as a hash
# Key: brake_state:{user_id}
# Fields: state, activated_at, paused_tasks[], stuck_tasks[]

class BrakeState(str, enum.Enum):
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    PARTIAL = "partial"  # some tasks stuck
    RESUMING = "resuming"

async def activate_brake(user_id: str) -> None:
    """Called when user presses emergency brake button."""
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    # Set the brake flag (checked by all agents)
    await r.set(f"paused:{user_id}", "1")

    # Set state machine to PAUSING
    await r.hset(f"brake_state:{user_id}", mapping={
        "state": BrakeState.PAUSING,
        "activated_at": datetime.now(timezone.utc).isoformat(),
    })

    # Publish brake event for WebSocket
    await r.publish(f"agent:status:{user_id}", json.dumps({
        "type": "system.brake.activated",
        "state": "pausing",
    }))

    # After 30 seconds, check if all tasks have stopped
    # (Celery task that verifies and transitions to PAUSED or PARTIAL)
    from app.worker.tasks import verify_brake_completion
    verify_brake_completion.apply_async(
        args=[user_id],
        countdown=30,
        queue="default",
    )
    await r.aclose()


async def resume_agents(user_id: str) -> None:
    """Called when user presses resume button."""
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    await r.delete(f"paused:{user_id}")
    await r.hset(f"brake_state:{user_id}", "state", BrakeState.RUNNING)
    await r.publish(f"agent:status:{user_id}", json.dumps({
        "type": "system.brake.resumed",
        "state": "running",
    }))
    await r.aclose()
```

**Brake propagation to Celery tasks:**
- Every agent checks `paused:{user_id}` BEFORE each logical step (LLM call, DB write, external API call)
- In-flight LLM calls cannot be cancelled -- the brake prevents the NEXT step, not the current one
- In-flight applications (if Apply Agent is running) cannot be un-submitted -- brake prevents next application
- All pending approval items are marked "paused" so user sees nothing will execute

### Pattern: Daily Briefing Pipeline

```
Celery Beat (RedBeat, per-user schedule)
    |
    v
briefing_generate task (briefings queue)
    |
    +-- 1. Gather data (parallel queries)
    |   |-- Recent matches from Job Scout
    |   |-- Application status changes
    |   |-- Pending approvals count
    |   |-- Follow-up reminders due
    |   |-- Agent errors/issues
    |
    +-- 2. LLM summarize (one call, structured output)
    |   |-- Summary paragraph
    |   |-- Actions needed list
    |   |-- Key metrics
    |
    +-- 3. Store briefing in database
    |   |-- briefings table with user_id, content JSONB, generated_at
    |
    +-- 4. Deliver (parallel)
        |-- In-app: store + WebSocket notification
        |-- Email: Resend API with HTML template
```

**Fallback (Story 3-11):**
```python
async def generate_briefing_with_fallback(user_id: str) -> dict:
    """Generate briefing with lite fallback on failure."""
    try:
        briefing = await generate_full_briefing(user_id)
        # Cache successful briefing for fallback use
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.set(
            f"briefing_cache:{user_id}",
            json.dumps(briefing),
            ex=86400 * 2,  # 48-hour TTL
        )
        await r.aclose()
        return briefing
    except Exception as exc:
        logger.error("Briefing generation failed for user=%s: %s", user_id, exc)
        # Alert ops team
        sentry_sdk.capture_exception(exc)
        # Generate lite briefing from cache
        lite = await generate_lite_briefing(user_id)
        # Schedule retry in 1 hour
        briefing_generate.apply_async(
            args=[user_id],
            countdown=3600,
            queue="briefings",
        )
        return lite

async def generate_lite_briefing(user_id: str) -> dict:
    """Lite briefing from cached data when full pipeline fails."""
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    cached = await r.get(f"briefing_cache:{user_id}")
    await r.aclose()

    if cached:
        previous = json.loads(cached)
        return {
            "type": "lite",
            "message": "We're having some trouble today. Here's what we know:",
            "last_known_pipeline": previous.get("pipeline_status"),
            "cached_matches": previous.get("new_matches", [])[:5],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # No cache available -- minimal briefing
    return {
        "type": "lite",
        "message": "We're having some trouble today. Check back soon!",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
```

### Anti-Patterns to Avoid

- **God Orchestrator:** Split into TaskRouter (deterministic code), BriefingGenerator (LLM), TierEnforcer (decorator), BrakeManager (Redis). Never put all in one class.
- **LLM-based routing:** The orchestrator routes tasks by task type and schedule, NOT by asking an LLM "which agent should handle this?" Routing is deterministic code.
- **Synchronous agent calls:** All agent work goes through Celery. API returns task_id immediately. Client polls or gets WebSocket update.
- **Shared mutable state between agents:** Each agent reads its input snapshot and writes to agent_outputs. Agents never directly modify each other's data.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM cost tracking | Extend custom cost_tracker.py | Langfuse `@observe()` | Automatic per-user cost, trace visualization, evaluation scoring, prompt management |
| Per-user dynamic cron scheduling | Custom scheduler or static celery beat | RedBeat (celery-redbeat) | Redis-backed, dynamic add/modify/remove without restart, timezone support |
| Agent state checkpointing | Custom PostgreSQL checkpoint tables | LangGraph PostgresSaver (if LangGraph) | Handles serialization, versioning, crash recovery, thread management |
| LLM response mocking for tests | Custom mock classes | VCR.py + pytest-recording | Record real API calls once, replay deterministically; filter auth headers automatically |
| Agent output quality testing | Custom assertion logic | DeepEval | 50+ metrics, native pytest integration, hallucination detection, CI/CD integration |
| Real-time event delivery | Custom WebSocket polling | Existing Redis pub/sub + WebSocket (already built) | Phase 1 already created this infrastructure; extend, don't rebuild |

**Key insight:** The biggest "don't hand-roll" for this phase is the approval queue resume logic. If using LangGraph, `interrupt()` + `Command(resume=)` handles this natively. If custom, you must build: serialize pending action to DB, notify user, wait for response, deserialize and re-execute. This is the main complexity delta between the two approaches.

## Common Pitfalls

### Pitfall 1: Dual PostgreSQL Driver Conflict (LangGraph path only)
**What goes wrong:** LangGraph's `PostgresSaver` requires psycopg3 (`psycopg`). The existing codebase uses asyncpg via SQLAlchemy. Running both drivers against the same database can cause connection pool exhaustion and confusion.
**Why it happens:** LangGraph checkpoint library was built around psycopg3, not asyncpg.
**How to avoid:** Use separate connection pools. SQLAlchemy async engine stays on asyncpg for all app queries. LangGraph checkpointer gets its own psycopg3 pool with limited size (2-3 connections). Document this clearly.
**Warning signs:** `TooManyConnections` errors, checkpoint writes timing out.

### Pitfall 2: Brake Check Only at Task Start
**What goes wrong:** Agent checks brake once when task starts, then runs for 5 minutes without checking again. User presses brake, nothing happens for 5 minutes.
**Why it happens:** Developers forget to add brake checks between logical steps.
**How to avoid:** In BaseAgent, provide a `check_brake_or_raise()` helper. Call it before EVERY LLM call, EVERY external API call, and EVERY database write. In LangGraph, add brake check as entry to every node.
**Warning signs:** Brake latency exceeding 30-second requirement.

### Pitfall 3: RedBeat Schedule Explosion
**What goes wrong:** Creating a new RedBeat schedule entry per user without cleanup leads to thousands of stale entries when users churn or deactivate.
**Why it happens:** Schedules are stored in Redis but never garbage-collected.
**How to avoid:** Include user_id in schedule name. Add cleanup task that removes schedules for deactivated/braked users. Set TTL on schedule entries or run periodic cleanup.
**Warning signs:** Redis memory growing linearly with user count, even for inactive users.

### Pitfall 4: Briefing Generation Timeout
**What goes wrong:** Briefing aggregates data from 5+ sources + LLM summarization. One slow query blocks the entire pipeline past the 2-minute requirement.
**Why it happens:** Sequential data gathering instead of parallel.
**How to avoid:** Use `asyncio.gather()` for parallel data collection with per-query timeout of 15 seconds. If any source fails, proceed with partial data. LLM summary has its own 30-second timeout.
**Warning signs:** Briefing generation time exceeding 2 minutes in monitoring.

### Pitfall 5: WebSocket Connection Leak
**What goes wrong:** The existing `ws.py` creates a new Redis client per WebSocket connection and may not clean up on all disconnect paths.
**Why it happens:** The current code has try/finally for cleanup but exception paths can still leak connections.
**How to avoid:** Use a shared Redis connection pool for WebSocket pub/sub. Implement connection counting. Add health check that reports active WebSocket count vs Redis subscription count.
**Warning signs:** Redis connection count growing over time, `REDIS_MAX_CLIENTS` errors.

### Pitfall 6: Langfuse Context Loss in Celery Workers
**What goes wrong:** Langfuse's `@observe()` decorator uses Python `contextvars` to track traces. Celery workers run in separate processes, and `contextvars` don't propagate across process boundaries.
**Why it happens:** Celery tasks are serialized to JSON and sent via Redis; execution context is lost.
**How to avoid:** Initialize a new Langfuse trace at the START of each Celery task, passing `user_id` and `session_id` explicitly. Do NOT rely on decorator nesting across process boundaries.
**Warning signs:** Langfuse traces showing disconnected spans, missing parent traces.

## Code Examples

### Langfuse Integration (Replacing cost_tracker.py)

```python
# backend/app/observability/langfuse_client.py
# Replaces: backend/app/observability/cost_tracker.py

from langfuse import Langfuse
from langfuse.decorator import observe, langfuse_context
from app.config import settings

# Initialize once at module level
langfuse = Langfuse(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    host=settings.LANGFUSE_HOST,  # Self-hosted URL
)


# Usage in agent methods:
class JobScoutAgent(BaseAgent):
    agent_type = "job_scout"

    @observe(name="job_scout_execute")
    async def execute(self, user_id: str, task_data: dict) -> AgentOutput:
        # Set user context for per-user cost tracking
        langfuse_context.update_current_trace(
            user_id=user_id,
            tags=["agent:job_scout"],
        )
        # LLM call -- automatically tracked by @observe
        result = await self.llm_client.chat(
            model="gpt-4o-mini",
            messages=[...],
        )
        return AgentOutput(
            action="jobs_matched",
            rationale="Found 5 jobs matching preferences",
            confidence=0.85,
            data={"matches": result},
        )


# Usage in Celery task (explicit trace creation):
@celery_app.task(name="app.worker.tasks.agent_job_scout")
def agent_job_scout(user_id: str, task_data: dict):
    async def _execute():
        # Create explicit trace for Celery context
        trace = langfuse.trace(
            name="job_scout_task",
            user_id=user_id,
            metadata={"task_id": agent_job_scout.request.id},
        )
        try:
            agent = JobScoutAgent()
            result = await agent.run(user_id, task_data)
            trace.update(output=result.__dict__)
        except Exception as exc:
            trace.update(level="ERROR", status_message=str(exc))
            raise
        finally:
            langfuse.flush()

    return asyncio.run(_execute())
```

**Config additions to settings:**
```python
# In app/config.py
LANGFUSE_PUBLIC_KEY: str = ""
LANGFUSE_SECRET_KEY: str = ""
LANGFUSE_HOST: str = "http://localhost:3000"  # Self-hosted Langfuse
```

### RedBeat Per-User Briefing Schedule

```python
# backend/app/agents/briefing/scheduler.py
from redbeat import RedBeatSchedulerEntry
from celery.schedules import crontab
from app.worker.celery_app import celery_app


def create_user_briefing_schedule(
    user_id: str,
    hour: int = 8,
    minute: int = 0,
    timezone: str = "UTC",
    channels: list[str] = None,
) -> None:
    """Create or update a per-user daily briefing schedule."""
    channels = channels or ["in_app", "email"]

    entry = RedBeatSchedulerEntry(
        name=f"briefing:{user_id}",
        task="app.worker.tasks.briefing_generate",
        schedule=crontab(hour=hour, minute=minute),
        args=[user_id],
        kwargs={"channels": channels},
        app=celery_app,
    )
    entry.save()


def remove_user_briefing_schedule(user_id: str) -> None:
    """Remove a user's briefing schedule (e.g., on brake or deactivation)."""
    try:
        entry = RedBeatSchedulerEntry.from_key(
            f"redbeat:briefing:{user_id}",
            app=celery_app,
        )
        entry.delete()
    except KeyError:
        pass  # Schedule doesn't exist
```

**Note on timezone handling:** RedBeat does not natively support per-entry timezones the way django-celery-beat does. The workaround is to convert the user's desired local time to UTC before creating the crontab. When the user is in US/Eastern and wants 8am, compute the UTC hour (13:00 EST / 12:00 EDT) and store that. Update the schedule on DST transitions via a periodic cleanup task.

### Approval Queue Schema

```python
# Add to backend/app/db/models.py

class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    PAUSED = "paused"  # Set when brake is active


class ApprovalQueueItem(SoftDeleteMixin, TimestampMixin, Base):
    """Pending agent actions awaiting L2 user approval."""
    __tablename__ = "approval_queue"
    __table_args__ = (
        Index("ix_approval_queue_user_status", "user_id", "status"),
        Index("ix_approval_queue_expires", "expires_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_type = Column(
        Enum(AgentType, name="agent_type", create_type=False),
        nullable=False,
    )
    action_name = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False)  # Serialized action context
    status = Column(
        Enum(ApprovalStatus, name="approval_status", create_type=False),
        nullable=False,
        default=ApprovalStatus.PENDING,
    )
    rationale = Column(Text, nullable=True)  # Agent's rationale for the action
    confidence = Column(Numeric(3, 2), nullable=True)
    user_decision_reason = Column(Text, nullable=True)  # Why user approved/rejected
    decided_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # If using LangGraph: store the thread_id to resume execution
    langgraph_thread_id = Column(Text, nullable=True)
    langgraph_checkpoint_ns = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", backref="approval_items")


class Briefing(TimestampMixin, Base):
    """Daily briefing records."""
    __tablename__ = "briefings"
    __table_args__ = (
        Index("ix_briefings_user_generated", "user_id", "generated_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    content = Column(JSONB, nullable=False)  # Structured briefing data
    briefing_type = Column(Text, nullable=False, default="full")  # "full" | "lite"
    generated_at = Column(DateTime(timezone=True), nullable=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    delivery_channels = Column(ARRAY(Text), default=[])  # ["in_app", "email"]
    read_at = Column(DateTime(timezone=True), nullable=True)
    schema_version = Column(Integer, nullable=False, default=1)

    # Relationships
    user = relationship("User", backref="briefings")
```

### Agent Activity Feed (WebSocket Extension)

```python
# Extend existing backend/app/api/v1/ws.py publish_agent_event()

# Standard event schema for activity feed:
ACTIVITY_EVENTS = {
    "agent.job_scout.searching": {
        "title": "Job Scout is searching for matches...",
        "severity": "info",
    },
    "agent.job_scout.completed": {
        "title": "Job Scout found {count} new matches",
        "severity": "info",
    },
    "agent.resume.tailoring": {
        "title": "Resume Agent is tailoring for {company}...",
        "severity": "info",
    },
    "agent.resume.completed": {
        "title": "Resume tailored for {company}",
        "severity": "info",
    },
    "system.brake.activated": {
        "title": "Emergency brake activated",
        "severity": "warning",
    },
    "system.brake.resumed": {
        "title": "Agents resumed",
        "severity": "info",
    },
    "system.briefing.ready": {
        "title": "Your daily briefing is ready",
        "severity": "action_required",
    },
    "approval.new": {
        "title": "New action requires your approval",
        "severity": "action_required",
    },
}

# Event payload structure (used by all agents):
# {
#     "type": "agent.job_scout.completed",
#     "event_id": "uuid",
#     "timestamp": "2026-01-31T08:00:00Z",
#     "user_id": "user_...",
#     "agent_type": "job_scout",
#     "title": "Job Scout found 5 new matches",
#     "severity": "info",
#     "data": { ... event-specific payload ... }
# }
```

### Testing: VCR-Style LLM Mocking

```python
# backend/tests/conftest.py additions
import pytest

@pytest.fixture
def vcr_config():
    """VCR configuration for recording LLM API calls."""
    return {
        "filter_headers": ["authorization", "x-api-key", "api-key"],
        "record_mode": "none",  # Use "once" to record, "none" to replay
        "cassette_library_dir": "backend/tests/cassettes",
        "decode_compressed_response": True,
    }


# backend/tests/unit/test_agents/test_tier_enforcement.py
import pytest
from app.agents.base import BaseAgent, TierViolation, BrakeActive

class TestTierEnforcement:
    """Deterministic tests -- no LLM calls needed."""

    def test_l0_user_cannot_auto_apply(self, mock_user_l0):
        """L0 users MUST only receive suggestions."""
        agent = ApplyAgent()
        with pytest.raises(TierViolation):
            asyncio.run(agent.apply(mock_user_l0.id, job_id="123"))

    def test_l2_write_action_queues_for_approval(self, mock_user_l2):
        """L2 write actions go to approval queue, not direct execution."""
        agent = ApplyAgent()
        result = asyncio.run(agent.apply(mock_user_l2.id, job_id="123"))
        assert result.action == "queued_for_approval"
        assert result.requires_approval is True

    def test_l3_executes_directly(self, mock_user_l3):
        """L3 actions execute without approval."""
        agent = ApplyAgent()
        result = asyncio.run(agent.apply(mock_user_l3.id, job_id="123"))
        assert result.action != "queued_for_approval"

    def test_brake_blocks_all_tiers(self, mock_user_l3, redis_brake_active):
        """Emergency brake blocks even L3 users."""
        agent = JobScoutAgent()
        with pytest.raises(BrakeActive):
            asyncio.run(agent.run(mock_user_l3.id, {}))


# backend/tests/unit/test_agents/test_briefing_quality.py
import pytest

@pytest.mark.vcr()  # Uses recorded LLM response
def test_briefing_has_required_sections():
    """Briefing must have all required sections."""
    briefing = asyncio.run(generate_full_briefing("test_user"))
    assert "summary" in briefing
    assert "actions_needed" in briefing
    assert "new_matches" in briefing
    assert "activity_log" in briefing

@pytest.mark.vcr()
def test_lite_briefing_on_failure(mock_cached_briefing):
    """Lite briefing returns cached data when full pipeline fails."""
    with pytest.raises(Exception):
        asyncio.run(generate_full_briefing("test_user"))
    lite = asyncio.run(generate_lite_briefing("test_user"))
    assert lite["type"] == "lite"
    assert "last_known_pipeline" in lite
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| langchain 0.0.x monolith | langchain-core + langgraph 1.0 (separate packages) | Oct 2025 | Must use new package names; old `langchain` is deprecated |
| Custom Redis cost tracking | Langfuse @observe() | 2024-2025 | Automatic per-user cost/latency; trace visualization; built on OpenTelemetry |
| Static celery beat config file | RedBeat (Redis-backed dynamic scheduler) | Stable since 2020 | Per-user timezone-aware scheduling without restart |
| LangGraph breakpoints (static) | LangGraph interrupt() (dynamic) | Late 2025 | Simpler, more flexible human-in-the-loop; conditional pausing |
| PostgresSaver via langchain_postgres | langgraph-checkpoint-postgres (psycopg3) | Dec 2025 | New package, new driver (psycopg3 not psycopg2), setup() required |
| Jest for frontend testing | Vitest (already in codebase) | 2024 | Faster, Vite-native, API-compatible |

**Deprecated/outdated:**
- `langchain` 0.0.340 in the codebase: **Dead**. Must be removed entirely. Replace with either LangGraph or custom.
- Custom `cost_tracker.py`: Will be superseded by Langfuse. Keep for 1 sprint as fallback, then remove.
- `langgraph.checkpoint.postgres.PostgresSaver` from `langchain_postgres` package: **Replaced** by `langgraph-checkpoint-postgres` (separate package with psycopg3).

## Open Questions

Things that couldn't be fully resolved:

1. **psycopg3 vs asyncpg coexistence**
   - What we know: LangGraph checkpointer requires psycopg3. Codebase uses asyncpg via SQLAlchemy.
   - What's unclear: Connection pool sizing when both drivers target the same Supabase instance. Supabase free tier has limited connections.
   - Recommendation: Test during prototype. If connection limits are tight, consider using asyncpg-based custom checkpointer instead.

2. **RedBeat timezone handling accuracy**
   - What we know: RedBeat stores schedules in Redis with crontab. No native per-entry timezone support.
   - What's unclear: Exact behavior during DST transitions when UTC offset changes.
   - Recommendation: Convert user local time to UTC on schedule creation. Run a weekly "DST correction" task that adjusts schedules for users in DST-affected timezones.

3. **Langfuse self-hosted resource requirements**
   - What we know: Langfuse can be self-hosted via Docker Compose or Kubernetes. GDPR compliance requires self-hosting.
   - What's unclear: Memory/CPU requirements for the volume of traces this system will generate (100+ agent runs/day at scale).
   - Recommendation: Start with Langfuse Cloud free tier for development. Plan self-hosting for production as a Phase 3 task. Budget 1 small VM (2 CPU, 4GB RAM) for self-hosted Langfuse.

4. **LangGraph + Celery interaction model**
   - What we know: LangGraph graphs run as Python functions. Celery tasks are Python functions.
   - What's unclear: Best pattern for running a LangGraph graph inside a Celery task. Should the graph run synchronously (blocking the worker) or should each node be a separate Celery task?
   - Recommendation: Run the entire graph in a single Celery task (simpler). Each graph execution is a single unit of work. The graph handles its own internal state. Celery handles scheduling, retries, and queue routing.

5. **Approval queue item expiration policy**
   - What we know: Approval items should expire to prevent stale actions from executing.
   - What's unclear: What's the right TTL? 24 hours? 7 days? Does it depend on action type?
   - Recommendation: Default 48-hour expiry. Job applications expire in 24 hours (job may be filled). Resume tailoring expires in 7 days. Make configurable per action type.

## Sources

### Primary (HIGH confidence)
- [LangGraph Interrupts - Official Docs](https://docs.langchain.com/oss/python/langgraph/interrupts) -- interrupt(), Command(resume=), checkpointing
- [LangGraph Overview - Official Docs](https://docs.langchain.com/oss/python/langgraph/overview) -- StateGraph, nodes, edges, orchestrator pattern
- [langgraph-checkpoint-postgres - PyPI](https://pypi.org/project/langgraph-checkpoint-postgres/) -- v3.0.2, psycopg3, setup() method
- [Langfuse Decorator-Based Python Integration](https://langfuse.com/docs/sdk/python/decorators) -- @observe(), contextvars, FastAPI setup
- [Langfuse Model Usage & Cost Tracking](https://langfuse.com/docs/observability/features/token-and-cost-tracking) -- per-user cost, automatic model pricing
- [Celery Periodic Tasks - Official Docs](https://docs.celeryq.dev/en/main/userguide/periodic-tasks.html) -- crontab, beat scheduler
- [celery-redbeat - PyPI](https://pypi.org/project/celery-redbeat/) -- v2.3.3, Redis-backed dynamic scheduling
- [VCR.py - GitHub](https://github.com/kevin1024/vcrpy) -- HTTP interaction recording/replay

### Secondary (MEDIUM confidence)
- [LangGraph 2025 Review: State-Machine Agents for Production AI](https://neurlcreators.substack.com/p/langgraph-agent-state-machine-review) -- Production pros/cons
- [ZenML Blog: LangGraph Alternatives](https://www.zenml.io/blog/langgraph-alternatives) -- Framework comparison with production evaluation
- [LangWatch: Best AI Agent Frameworks 2025](https://langwatch.ai/blog/best-ai-agent-frameworks-in-2025-comparing-langgraph-dspy-crewai-agno-and-more) -- Multi-framework comparison
- [Medium: Scaling AI-Powered Agents with Distributed LangGraph](https://medium.com/@mukshobhit/scaling-ai-powered-agents-building-a-distributed-langgraph-workflow-engine-13e57e368953) -- Celery + LangGraph integration pattern
- [Medium: LangGraph interrupt() Function](https://medium.com/@areebahmed575/langgraphs-interrupt-function-the-simpler-way-to-build-human-in-the-loop-agents-faef98891a92) -- Practical interrupt() tutorial
- [Mastering LangGraph Checkpointing Best Practices 2025](https://sparkco.ai/blog/mastering-langgraph-checkpointing-best-practices-for-2025) -- PostgresSaver production patterns

### Tertiary (LOW confidence)
- [Medium: Using Celery RedBeat for Dynamic Scheduling](https://medium.com/@MarinAgli1/using-celery-redbeat-for-basic-dynamic-scheduling-of-periodic-tasks-5e131d3d30a0) -- RedBeat usage patterns
- [DEV: rdbbeat SQLAlchemy Scheduler](https://dev.to/evanstjabadi/supercharge-celery-beat-with-a-custom-scheduler-rdbbeat-20cd) -- rdbbeat as alternative
- [Medium: VCR Tests for LLMs](https://anaynayak.medium.com/eliminating-flaky-tests-using-vcr-tests-for-llms-a3feabf90bc5) -- VCR.py for LLM testing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries verified via PyPI and official docs
- Architecture (ADR-1 LangGraph vs Custom): MEDIUM - both approaches well-understood, but the right choice for THIS project depends on prototype results
- Architecture (briefing pipeline, brake state machine): HIGH - standard patterns verified
- Langfuse integration: HIGH - official docs clearly document decorator pattern and per-user cost tracking
- Pitfalls: MEDIUM-HIGH - psycopg3/asyncpg coexistence and RedBeat timezone edge cases need prototype validation
- Testing strategy: HIGH - VCR.py and DeepEval well-established with clear documentation

**Research date:** 2026-01-31
**Valid until:** 2026-03-01 (30 days; LangGraph ecosystem evolving rapidly)
