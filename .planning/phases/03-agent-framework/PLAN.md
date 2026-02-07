---
phase: 03-agent-framework
plans: 8
type: phase-plan
---

# Phase 3: Agent Framework Core -- Execution Plan

## Phase Goal

The agent orchestration infrastructure is operational -- orchestrator routes tasks, autonomy tiers are enforced, the emergency brake works, daily briefings are generated and delivered, and real-time activity is visible via WebSocket.

## Success Criteria (all must be TRUE at phase end)

1. The emergency brake button is visible on every page, and pressing it pauses all agent activity for that user within 30 seconds
2. A daily briefing is generated at the user's configured time and delivered both in-app and via email within 15 minutes
3. The agent activity feed shows real-time updates via WebSocket when agents are running
4. Autonomy level (L0-L3) is enforced -- an L0 user's agents only suggest, an L2 user's agents act but surface in approval digest, and this is verifiable via test
5. If the briefing pipeline fails, a "lite briefing" from cache is shown instead of an error

---

## Dependency Graph & Wave Structure

```
Wave 0 (gate -- must complete before all others):
  Plan 01: ADR-1 Prototype -- LangGraph vs Custom Orchestrator

Wave 1 (parallel, depends on Wave 0):
  Plan 02: Database Schema + Agent Models (Alembic migration)
  Plan 03: BaseAgent + Tier Enforcement + Brake Module

Wave 2 (parallel, depends on Wave 1):
  Plan 04: Orchestrator + Langfuse Observability
  Plan 05: Briefing Pipeline Backend (generate, schedule, deliver, fallback)

Wave 3 (parallel, depends on Wave 2):
  Plan 06: Emergency Brake Frontend + Agent Activity Feed (WebSocket)
  Plan 07: Briefing Frontend (in-app display, settings, empty state)

Wave 4 (depends on Wave 3):
  Plan 08: Integration Tests + VCR Cassettes + Phase Verification
```

---

## Plan 01: ADR-1 Prototype -- LangGraph vs Custom Orchestrator

**Wave:** 0 (gates ALL subsequent work)
**Stories:** Partial 3-1 (Orchestrator Agent Infrastructure)
**Estimated effort:** 30-45 min Claude execution

### Objective

Build the same minimal agent flow (brake check -> tier check -> execute -> record output) in both LangGraph and custom Python. Evaluate based on: brake propagation latency, L2 approval flow clarity, test determinism, developer ergonomics, and dependency footprint. Write ADR-1 decision document.

### Tasks

**Task 1: Install prototype dependencies**
- Files: `backend/requirements.txt`
- Action:
  - Add LangGraph dependencies in a clearly-marked "ADR-1 PROTOTYPE" section (remove if custom wins):
    - `langgraph>=0.3.0`
    - `langgraph-checkpoint-postgres>=3.0.2`
    - `psycopg[binary,pool]>=3.1.0`
    - `langchain-core>=0.3.0`
    - `langchain-openai>=0.3.0`
  - Add shared dependencies (needed either way):
    - `langfuse>=2.0.0`
    - `celery-redbeat>=2.3.3`
    - `vcrpy>=6.0.0`
    - `pytest-recording>=0.13.0`
    - `deepeval>=1.0.0`
  - Run `pip install -r requirements.txt` to verify all packages install without conflict
- Verify: `pip install -r requirements.txt` succeeds. `python -c "import langgraph; import langfuse; import redbeat"` works.
- Done: All prototype and shared dependencies installed.

**Task 2: Build LangGraph prototype**
- Files: `backend/app/agents/_prototype_langgraph.py`
- Action:
  - Create a self-contained file with:
    - `AgentState(TypedDict)` with fields: user_id, user_tier, is_braked, task_type, input_data, output, rationale, confidence, requires_approval
    - `PrototypeLangGraphAgent` class with `StateGraph` that has 5 nodes: check_brake, check_tier, execute, await_approval, record_output
    - `check_brake` node: checks Redis key `paused:{user_id}`, calls `interrupt()` if active
    - `check_tier` node: reads user_tier from state, routes via conditional edge to either `execute` or `await_approval`
    - `await_approval` node: uses `interrupt()` to pause for human decision, resumes via `Command(resume={"approved": True/False})`
    - `execute` node: returns a dummy AgentOutput (no real LLM call -- this is a prototype)
    - `record_output` node: prints output (no DB write -- prototype only)
  - Include a `__main__` block that runs: (1) L0 user -- should produce suggestion only, (2) L2 user -- should hit await_approval interrupt, (3) L3 user -- should execute directly, (4) braked user -- should hit brake interrupt
  - Use `MemorySaver` (in-memory) for prototype, not PostgresSaver
- Verify: `python -m backend.app.agents._prototype_langgraph` runs all 4 scenarios and prints expected routing.
- Done: LangGraph prototype demonstrates brake, tier routing, and approval interruption.

**Task 3: Build Custom prototype**
- Files: `backend/app/agents/_prototype_custom.py`
- Action:
  - Create a self-contained file with:
    - `AgentOutput` dataclass with fields: action, rationale, confidence, alternatives_considered, data, requires_approval
    - `BrakeActive` and `TierViolation` exception classes
    - `check_brake(user_id)` async function: checks Redis key `paused:{user_id}`
    - `requires_tier(min_tier, action_type)` decorator: checks brake, validates tier, routes L2 write actions to `_queue_for_approval`
    - `BaseAgent` class with: `run()` entry (checks brake, calls execute, records output, publishes event), `execute()` abstract, `_record_output()` stub, `_publish_event()` stub, `_queue_for_approval()` stub
    - `PrototypeAgent(BaseAgent)` with dummy execute
  - Include a `__main__` block running same 4 scenarios as LangGraph prototype
- Verify: `python -m backend.app.agents._prototype_custom` runs all 4 scenarios and prints expected routing.
- Done: Custom prototype demonstrates brake, tier routing, and approval queuing.

**Task 4: Evaluate and write ADR-1**
- Files: `docs/adr/ADR-001-agent-orchestration-framework.md`
- Action:
  - Create `docs/adr/` directory if not exists
  - Write ADR-1 comparing both prototypes on these criteria (fill in observations from running prototypes):
    - **Brake propagation**: Both use Redis check; functionally equivalent
    - **L2 approval flow**: LangGraph uses `interrupt()`+`Command(resume=)` (state auto-persisted); Custom uses DB table + resume endpoint (must hand-roll)
    - **L0 suggestion-only**: Both route by tier; functionally equivalent
    - **Worker crash recovery**: LangGraph has PostgresSaver; Custom must checkpoint manually
    - **Developer ergonomics**: LangGraph requires learning StateGraph model; Custom is plain Python
    - **Dependency footprint**: LangGraph adds ~100MB + psycopg3 (dual PG driver); Custom adds nothing
    - **Test determinism**: Custom is simpler to mock (plain functions); LangGraph requires graph state mocking
  - **Recommendation**: Based on the research, recommend **Custom approach** if the prototype confirms:
    - Approval queue via DB table + WebSocket notification is straightforward (it is -- Phase 1 already built WebSocket infra)
    - Agent tasks are Celery-managed (crash recovery via Celery acks_late + reject_on_worker_lost, already configured in Phase 1)
    - Avoiding dual PostgreSQL driver (psycopg3 + asyncpg) is worth the tradeoff of hand-rolling approval resume
  - If LangGraph prototype reveals significant advantages not captured in research, recommend LangGraph instead
  - Record decision with status: DECIDED, date, and rationale
  - If Custom wins: update `requirements.txt` to REMOVE the LangGraph prototype dependencies (langgraph, langgraph-checkpoint-postgres, psycopg, langchain-core, langchain-openai)
- Verify: ADR document exists with clear decision. `requirements.txt` reflects the chosen path (no unused framework deps).
- Done: ADR-1 is resolved. Prototype files can remain as reference but are not imported by production code.

---

## Plan 02: Database Schema + Agent Models

**Wave:** 1 (depends on Plan 01 -- ADR-1 must be resolved)
**Stories:** Partial 3-1, 3-2, 3-7
**Estimated effort:** 15-25 min Claude execution

### Objective

Create the Alembic migration and SQLAlchemy models for: `agent_outputs`, `approval_queue`, `briefings`, and `agent_activities` tables. Also add `briefing_time` and `briefing_channels` columns to `user_preferences`. These models are needed by all subsequent plans.

### Tasks

**Task 1: Add SQLAlchemy models**
- Files: `backend/app/db/models.py`
- Action:
  - Add `AgentType` text constants (not PG Enum per Phase 2 convention): `"job_scout"`, `"resume"`, `"apply"`, `"pipeline"`, `"briefing"`, `"orchestrator"`
  - Add `ApprovalStatus` text constants: `"pending"`, `"approved"`, `"rejected"`, `"expired"`, `"paused"`
  - Add `BrakeState` text constants: `"running"`, `"pausing"`, `"paused"`, `"partial"`, `"resuming"`
  - Add `AgentOutput` model:
    - `id` UUID PK, `user_id` FK to users, `agent_type` Text, `task_id` Text (Celery task ID), `output` JSONB, `rationale` Text nullable, `confidence` Numeric(3,2) nullable, `schema_version` Integer default 1, `created_at` timestamp
    - Index on (user_id, created_at DESC) for activity feed queries
  - Add `ApprovalQueueItem` model (from RESEARCH.md schema -- use SoftDeleteMixin, TimestampMixin):
    - `id` UUID PK, `user_id` FK, `agent_type` Text, `action_name` Text, `payload` JSONB, `status` Text default "pending", `rationale` Text nullable, `confidence` Numeric(3,2) nullable, `user_decision_reason` Text nullable, `decided_at` DateTime nullable, `expires_at` DateTime
    - Index on (user_id, status) for pending query, index on expires_at for cleanup
  - Add `Briefing` model:
    - `id` UUID PK, `user_id` FK, `content` JSONB, `briefing_type` Text default "full" (values: "full", "lite"), `generated_at` DateTime, `delivered_at` DateTime nullable, `delivery_channels` ARRAY(Text) default [], `read_at` DateTime nullable, `schema_version` Integer default 1
    - Index on (user_id, generated_at DESC) for latest briefing query
  - Add `AgentActivity` model (for activity feed persistence):
    - `id` UUID PK, `user_id` FK, `event_type` Text, `agent_type` Text nullable, `title` Text, `severity` Text default "info" (values: "info", "warning", "action_required"), `data` JSONB default {}, `created_at` timestamp
    - Index on (user_id, created_at DESC) for feed queries
  - Add to `UserPreference` model (or alter existing):
    - `briefing_hour` Integer default 8 (0-23, UTC equivalent of user's local 8am)
    - `briefing_minute` Integer default 0
    - `briefing_timezone` Text default "UTC"
    - `briefing_channels` ARRAY(Text) default ["in_app", "email"]
- Verify: `python -c "from app.db.models import AgentOutput, ApprovalQueueItem, Briefing, AgentActivity"` succeeds.
- Done: All 4 new models importable. UserPreference has briefing fields.

**Task 2: Create Alembic migration**
- Files: `backend/alembic/versions/0003_agent_framework_tables.py`
- Action:
  - Write migration manually (consistent with Phase 2 pattern -- no DB connection for autogenerate)
  - Create tables: `agent_outputs`, `approval_queue`, `briefings`, `agent_activities`
  - Add columns to `user_preferences`: `briefing_hour`, `briefing_minute`, `briefing_timezone`, `briefing_channels`
  - Include all indexes defined in Task 1
  - Include downgrade that drops new tables and columns
  - Note: Mark as "review when first applied" (same pattern as 0002)
- Verify: Migration file is syntactically valid Python. Alembic can parse it: `cd backend && python -c "from alembic.config import Config; from alembic import command; c = Config('alembic.ini')"` (or equivalent check that the migration module imports cleanly).
- Done: Migration file exists at correct path with upgrade/downgrade functions.

---

## Plan 03: BaseAgent + Tier Enforcement + Brake Module

**Wave:** 1 (depends on Plan 01 -- uses the ADR-1 winner's pattern)
**Stories:** 3-1 (orchestrator infrastructure -- agent base), 3-6 (emergency brake -- backend), 3-7 (brake state machine), 3-8 (resume after pause)
**Estimated effort:** 25-35 min Claude execution

### Objective

Create the core agent infrastructure modules: `BaseAgent` class, `AgentOutput` dataclass, tier enforcement decorator, and emergency brake state machine. These are the building blocks every agent and the orchestrator depend on.

### Tasks

**Task 1: Create agent base module**
- Files: `backend/app/agents/__init__.py`, `backend/app/agents/base.py`
- Action:
  - Create `backend/app/agents/` package with `__init__.py`
  - In `base.py`, implement (use the ADR-1 winning pattern -- likely Custom per research recommendation):
    - `AgentOutput` dataclass: `action` str, `rationale` str, `confidence` float, `alternatives_considered` list[str], `data` dict, `requires_approval` bool
    - `BrakeActive(Exception)` -- raised when brake is active
    - `TierViolation(Exception)` -- raised when action exceeds tier
    - `BaseAgent` class with:
      - `agent_type: str` class attribute
      - `async run(self, user_id: str, task_data: dict) -> AgentOutput` -- checks brake, calls execute, records output to DB, publishes WebSocket event
      - `async execute(self, user_id: str, task_data: dict) -> AgentOutput` -- abstract, subclasses override
      - `async _record_output(self, user_id: str, output: AgentOutput)` -- writes to agent_outputs table via SQLAlchemy
      - `async _publish_event(self, user_id: str, output: AgentOutput)` -- publishes to Redis channel `agent:status:{user_id}`
      - `async _record_activity(self, user_id: str, event_type: str, title: str, severity: str, data: dict)` -- writes to agent_activities table
    - Langfuse `@observe()` decorator on `run()` method for automatic tracing
    - At START of each Celery task that invokes an agent, create explicit Langfuse trace (contextvars don't propagate across Celery process boundary -- see RESEARCH.md pitfall 6)
  - In `__init__.py`, export: `BaseAgent`, `AgentOutput`, `BrakeActive`, `TierViolation`
- Verify: `python -c "from app.agents import BaseAgent, AgentOutput, BrakeActive, TierViolation"` succeeds.
- Done: BaseAgent class with all required methods. Langfuse integration on run().

**Task 2: Create tier enforcement module**
- Files: `backend/app/agents/tier_enforcer.py`
- Action:
  - Implement `requires_tier(min_tier: str, action_type: str = "read")` decorator:
    - Always checks brake first (calls `check_brake` from brake module)
    - Looks up user's autonomy_level from UserPreference table via SQLAlchemy
    - Tier ordering: l0=0, l1=1, l2=2, l3=3
    - If user_level < required_level: raise `TierViolation`
    - **L0 behavior**: Can only receive suggestions. If action_type is "write", always raise TierViolation. If "read", the agent runs but output is tagged as "suggestion" (output.action prefixed with "suggest:")
    - **L1 behavior**: Can read and get recommendations. Write actions blocked.
    - **L2 behavior**: Read actions execute directly. Write actions route to `_queue_for_approval()` on the agent instance -- creates ApprovalQueueItem in DB with 48h default expiry, publishes "approval.new" WebSocket event
    - **L3 behavior**: All actions execute directly (within volume caps -- caps enforced by individual agents, not the tier decorator)
  - Implement `AutonomyGate` class as alternative to decorator (for agents that need programmatic tier checks):
    - `async check(user_id, action_type) -> Literal["execute", "suggest", "queue_approval", "blocked"]`
- Verify: Module imports cleanly. Decorator can be applied to an async method without error.
- Done: Tier enforcement decorator and AutonomyGate class implemented with all 4 tier behaviors.

**Task 3: Create brake module**
- Files: `backend/app/agents/brake.py`
- Action:
  - Implement `BrakeState` enum: RUNNING, PAUSING, PAUSED, PARTIAL, RESUMING
  - Implement `async check_brake(user_id: str) -> bool` -- checks Redis key `paused:{user_id}`
  - Implement `async check_brake_or_raise(user_id: str)` -- raises BrakeActive if braked (convenience for calling between agent steps)
  - Implement `async activate_brake(user_id: str)` -- follows RESEARCH.md pattern:
    - Set Redis key `paused:{user_id}` with value "1"
    - Set Redis hash `brake_state:{user_id}` with state=PAUSING, activated_at=now
    - Publish `system.brake.activated` event via Redis pub/sub to `agent:status:{user_id}`
    - Schedule `verify_brake_completion` Celery task with 30s countdown
  - Implement `async resume_agents(user_id: str)`:
    - Delete Redis key `paused:{user_id}`
    - Set brake_state to RUNNING
    - Publish `system.brake.resumed` event
    - Re-queue any interrupted tasks (mark as needs-requeue in agent_activities)
  - Implement `async get_brake_state(user_id: str) -> dict` -- returns current state, activated_at, paused_tasks count
  - Implement `async verify_brake_completion(user_id: str)` (called by Celery task after 30s):
    - Check if all agent tasks for user have stopped (no running Celery tasks with that user_id)
    - If all stopped: set state to PAUSED
    - If some still running: set state to PARTIAL with list of stuck task IDs
    - Mark all pending ApprovalQueueItems for this user as status="paused"
  - Use `redis.asyncio` throughout. Get Redis URL from `app.config.settings`
- Verify: Module imports cleanly. `check_brake`, `activate_brake`, `resume_agents` are all async functions.
- Done: Complete brake state machine with RUNNING->PAUSING->PAUSED->RESUMING->RUNNING cycle and PARTIAL fallback.

---

## Plan 04: Orchestrator + Langfuse Observability

**Wave:** 2 (depends on Plans 02 + 03)
**Stories:** 3-1 (orchestrator routing, shared memory, logging)
**Estimated effort:** 20-30 min Claude execution

### Objective

Build the task router (deterministic, code-based -- NOT LLM-based), Langfuse observability integration replacing cost_tracker.py, and the Celery task definitions for agent execution.

### Tasks

**Task 1: Create orchestrator / task router**
- Files: `backend/app/agents/orchestrator.py`
- Action:
  - Implement `TaskRouter` class (deterministic routing -- NO LLM):
    - `route_task(task_type: str, user_id: str, task_data: dict) -> str` -- returns Celery task name based on task_type
    - Task type to Celery task mapping: `"job_scout" -> "app.worker.tasks.agent_job_scout"`, `"resume" -> "app.worker.tasks.agent_resume"`, `"briefing" -> "app.worker.tasks.briefing_generate"`, etc.
    - Before routing: check brake state (if braked, raise BrakeActive)
    - Before routing: validate autonomy tier allows this task type
    - Logs all routing decisions to agent_activities table for debugging (Story 3-1 AC)
  - Implement `async dispatch_task(task_type: str, user_id: str, task_data: dict) -> str`:
    - Routes task, then sends to Celery via `.apply_async()`
    - Uses queue routing by naming convention (agent_* -> agents queue, briefing_* -> briefings queue) -- consistent with Phase 1 Plan 05 setup
    - Returns Celery task_id for tracking
  - Implement `async get_user_context(user_id: str) -> dict`:
    - Loads shared memory accessible to all agents: user profile, preferences, recent history
    - Query from DB, cache in Redis with 5-minute TTL (avoid per-agent DB queries)
    - This is the "shared memory" from Story 3-1 AC
- Verify: `python -c "from app.agents.orchestrator import TaskRouter"` succeeds.
- Done: Deterministic task router with brake/tier pre-checks, shared context loading, and Celery dispatch.

**Task 2: Create Langfuse observability module**
- Files: `backend/app/observability/langfuse_client.py`, `backend/app/config.py` (update)
- Action:
  - Add to `app/config.py` (Settings class):
    - `LANGFUSE_PUBLIC_KEY: str = ""`
    - `LANGFUSE_SECRET_KEY: str = ""`
    - `LANGFUSE_HOST: str = "http://localhost:3000"`
  - Create `langfuse_client.py`:
    - Initialize Langfuse client at module level using settings
    - Export `langfuse` instance for direct trace creation in Celery tasks
    - Export `create_agent_trace(user_id, agent_type, celery_task_id)` helper that creates a properly-tagged Langfuse trace (solves Celery contextvars pitfall from RESEARCH.md)
    - Export `flush_traces()` for calling in Celery task finally blocks
  - NOTE: Do NOT delete existing `cost_tracker.py` yet. Keep as fallback for 1 sprint (RESEARCH.md recommendation). Langfuse becomes primary; cost_tracker is secondary.
- Verify: `python -c "from app.observability.langfuse_client import langfuse, create_agent_trace"` succeeds.
- Done: Langfuse client configured. Agent trace helper available for Celery tasks.

**Task 3: Create agent Celery task definitions**
- Files: `backend/app/worker/tasks.py` (update existing)
- Action:
  - Add to existing tasks.py:
    - `agent_job_scout(user_id, task_data)` -- placeholder that imports and runs JobScoutAgent (agent not built until Phase 4, but task must exist for routing)
    - `agent_resume(user_id, task_data)` -- placeholder for Phase 5
    - `agent_apply(user_id, task_data)` -- placeholder for Phase 8
    - `briefing_generate(user_id, channels=None)` -- calls briefing generator (built in Plan 05)
    - `verify_brake_completion(user_id)` -- calls brake.verify_brake_completion
    - `cleanup_expired_approvals()` -- periodic task, marks expired ApprovalQueueItems
  - Each agent task follows this pattern (from RESEARCH.md):
    ```python
    @celery_app.task(name="app.worker.tasks.agent_job_scout", queue="agents")
    def agent_job_scout(user_id: str, task_data: dict):
        from app.observability.langfuse_client import create_agent_trace, flush_traces
        async def _execute():
            trace = create_agent_trace(user_id, "job_scout", agent_job_scout.request.id)
            try:
                # Agent implementation goes here (Phase 4)
                pass
            finally:
                flush_traces()
        return asyncio.run(_execute())
    ```
  - Register `cleanup_expired_approvals` as a periodic beat task (every 6 hours)
- Verify: `python -c "from app.worker.tasks import briefing_generate, verify_brake_completion"` succeeds.
- Done: All agent task stubs registered. Briefing and brake verification tasks callable.

---

## Plan 05: Briefing Pipeline Backend

**Wave:** 2 (depends on Plans 02 + 03)
**Stories:** 3-2 (briefing generation), 3-4 (email delivery), 3-5 (configurable time), 3-11 (fallback)
**Estimated effort:** 30-40 min Claude execution

### Objective

Build the complete briefing backend: data aggregation, LLM summarization, RedBeat per-user scheduling, dual delivery (in-app + email via Resend), Redis caching, and lite briefing fallback.

### Tasks

**Task 1: Briefing generator + fallback**
- Files: `backend/app/agents/briefing/generator.py`, `backend/app/agents/briefing/fallback.py`, `backend/app/agents/briefing/__init__.py`
- Action:
  - Create `backend/app/agents/briefing/` package
  - In `generator.py`, implement `async generate_full_briefing(user_id: str) -> dict`:
    - Use `asyncio.gather()` with per-query 15-second timeout to collect data in parallel:
      - Recent job matches (from agent_outputs where agent_type="job_scout", last 24h)
      - Application status changes (from agent_outputs where agent_type="apply/pipeline")
      - Pending approval count (from approval_queue where status="pending")
      - Agent errors/issues (from agent_activities where severity="warning")
    - LLM summarization call (30-second timeout):
      - Prompt: "Summarize the following job search activity into a daily briefing with sections: Summary, Actions Needed, New Matches, Activity Log"
      - Structured output: `{"summary": str, "actions_needed": [str], "new_matches": [dict], "activity_log": [dict], "metrics": {"total_matches": int, "pending_approvals": int, "applications_sent": int}}`
      - Use `@observe(name="briefing_generate")` Langfuse decorator
    - If first briefing with zero matches: return empty state content (Story 3-10): "Your agent is still learning your preferences. Check back tomorrow!" with tips
    - Store briefing in `briefings` table with briefing_type="full"
    - Cache successful briefing in Redis: key `briefing_cache:{user_id}`, 48h TTL (for fallback use)
    - Return briefing content dict
  - In `fallback.py`, implement (from RESEARCH.md):
    - `async generate_briefing_with_fallback(user_id: str) -> dict`: wraps generate_full_briefing in try/except. On failure: logs to Sentry, returns lite briefing, schedules retry in 1 hour
    - `async generate_lite_briefing(user_id: str) -> dict`: reads from Redis cache `briefing_cache:{user_id}`. If cache hit: returns lite briefing with cached data. If cache miss: returns minimal "check back soon" message. Always sets briefing_type="lite"
- Verify: `python -c "from app.agents.briefing.generator import generate_full_briefing; from app.agents.briefing.fallback import generate_briefing_with_fallback"` succeeds.
- Done: Full briefing pipeline with LLM summarization and lite fallback from Redis cache.

**Task 2: RedBeat scheduler + delivery**
- Files: `backend/app/agents/briefing/scheduler.py`, `backend/app/agents/briefing/delivery.py`
- Action:
  - In `scheduler.py`:
    - `create_user_briefing_schedule(user_id, hour, minute, timezone, channels)`:
      - Convert user's local time to UTC (handle timezone offset)
      - Create RedBeatSchedulerEntry with name `briefing:{user_id}`, task `app.worker.tasks.briefing_generate`, crontab at UTC hour/minute
      - Uses `celery_app` from existing worker config
    - `update_user_briefing_schedule(user_id, hour, minute, timezone, channels)`: deletes existing entry, creates new one
    - `remove_user_briefing_schedule(user_id)`: deletes entry by key `redbeat:briefing:{user_id}` (safe if doesn't exist)
    - `cleanup_stale_schedules()`: removes schedules for deactivated/braked users (run weekly)
  - In `delivery.py`:
    - `async deliver_briefing(user_id, briefing_content, channels)`:
      - If "in_app" in channels: store in briefings table (already done by generator), publish WebSocket event `system.briefing.ready`
      - If "email" in channels: send via Resend (using existing transactional_email module from Phase 1 Plan 08)
        - HTML template with: personalized greeting ("Good morning, {name}!"), summary cards, key metrics, action buttons ("View in App", "Approve All"), unsubscribe link
        - Subject: "Your Daily JobPilot Briefing - {date}"
      - Update briefing record with `delivered_at` timestamp and `delivery_channels`
    - `async mark_briefing_read(user_id, briefing_id)`: sets `read_at` on briefing record
  - Update Celery worker config to use RedBeat scheduler:
    - In `backend/app/worker/celery_app.py`, add `beat_scheduler = "redbeat.RedBeatScheduler"` to celery config
    - Add RedBeat config: `redbeat_redis_url` pointing to same Redis instance
- Verify: `python -c "from app.agents.briefing.scheduler import create_user_briefing_schedule; from app.agents.briefing.delivery import deliver_briefing"` succeeds.
- Done: Per-user briefing scheduling via RedBeat. Dual delivery (in-app + email). Celery beat configured for RedBeat.

**Task 3: Briefing + Approval API endpoints**
- Files: `backend/app/api/v1/briefings.py`, `backend/app/api/v1/approvals.py`
- Action:
  - In `briefings.py`:
    - `GET /api/v1/briefings/latest` -- returns latest briefing for authenticated user (or empty state if none)
    - `GET /api/v1/briefings/{briefing_id}` -- returns specific briefing
    - `GET /api/v1/briefings` -- returns paginated briefing history (last 30 days)
    - `POST /api/v1/briefings/{briefing_id}/read` -- marks briefing as read
    - `PUT /api/v1/briefings/settings` -- updates briefing time/timezone/channels in user_preferences + updates RedBeat schedule
    - `GET /api/v1/briefings/settings` -- returns current briefing configuration
  - In `approvals.py`:
    - `GET /api/v1/approvals` -- returns pending approval items for user (status="pending")
    - `POST /api/v1/approvals/{item_id}/approve` -- sets status="approved", triggers execution of queued action, records decided_at
    - `POST /api/v1/approvals/{item_id}/reject` -- sets status="rejected" with optional reason, records decided_at
    - `POST /api/v1/approvals/approve-all` -- bulk approve all pending items (for "Approve All" button in briefing email)
  - Register both routers in main app (update `backend/app/main.py` or app factory)
- Verify: Routes are registered. `python -c "from app.api.v1.briefings import router; from app.api.v1.approvals import router"` succeeds.
- Done: All briefing and approval REST endpoints implemented and registered.

---

## Plan 06: Emergency Brake Frontend + Agent Activity Feed

**Wave:** 3 (depends on Plans 03 + 04)
**Stories:** 3-6 (emergency brake button), 3-8 (resume after pause), 3-9 (agent activity feed)
**Estimated effort:** 25-35 min Claude execution

### Objective

Build the frontend emergency brake button (visible on every page), the agent activity feed with real-time WebSocket updates, and the brake API endpoints.

### Tasks

**Task 1: Brake API endpoints**
- Files: `backend/app/api/v1/agents.py`
- Action:
  - `POST /api/v1/agents/brake` -- calls activate_brake(user_id), returns {state: "pausing", activated_at}
  - `POST /api/v1/agents/resume` -- calls resume_agents(user_id), returns {state: "running"}
  - `GET /api/v1/agents/brake/status` -- calls get_brake_state(user_id), returns {state, activated_at, paused_tasks_count}
  - `GET /api/v1/agents/activity` -- returns paginated agent_activities for user (last 20 by default, with "load more" offset)
  - Register router in main app
- Verify: `python -c "from app.api.v1.agents import router"` succeeds.
- Done: Brake and activity feed REST endpoints implemented.

**Task 2: Emergency Brake button component**
- Files: `frontend/src/components/EmergencyBrake.tsx`
- Action:
  - Create `EmergencyBrake` component that renders in the app header/nav (visible on EVERY page per Story 3-6):
    - Shows current state: "Agents Active" (green dot) or "Agents Paused" (red dot) or "Pausing..." (yellow, animated)
    - Button click: immediately calls `POST /api/v1/agents/brake` (NO confirmation dialog -- speed critical per Story 3-6 AC)
    - When paused: button changes to "Resume Agents" and calls `POST /api/v1/agents/resume`
    - Polls `GET /api/v1/agents/brake/status` every 5 seconds while in "pausing" state to detect transition to "paused"
    - Also listens on WebSocket for `system.brake.activated` and `system.brake.resumed` events for instant UI updates
  - Style: Red button with white text, prominent but not intrusive. Use existing Tailwind classes.
  - Add to app layout so it appears on every page (update `frontend/src/App.tsx` or layout component)
- Verify: Component renders without errors. Button is visible in app header.
- Done: Emergency brake button visible on every page with real-time state updates.

**Task 3: Agent Activity Feed component**
- Files: `frontend/src/components/AgentActivityFeed.tsx`
- Action:
  - Create `AgentActivityFeed` component:
    - Loads initial activities from `GET /api/v1/agents/activity?limit=20`
    - Subscribes to WebSocket channel for real-time updates (extend existing WebSocket connection from Phase 1):
      - Listen for events matching `agent.*` and `system.*` patterns
      - Prepend new events to the feed list
    - Each activity item shows: icon (by agent_type), title, timestamp (relative: "2 min ago"), severity indicator (info=blue, warning=yellow, action_required=red)
    - Clicking an item could expand to show detail data (optional, nice-to-have)
    - "View All" link at bottom for full history
    - Empty state: "No agent activity yet. Configure your preferences to get started!"
  - Place on dashboard page (update Dashboard component to include ActivityFeed)
  - Standard event type to display mapping (from RESEARCH.md ACTIVITY_EVENTS):
    - `agent.*.searching` -> "Searching..." with spinner
    - `agent.*.completed` -> "Found X results" with check icon
    - `system.brake.*` -> Brake state changes with warning icon
    - `system.briefing.ready` -> "Your daily briefing is ready" with bell icon
    - `approval.new` -> "New action requires your approval" with attention icon
- Verify: Component renders without errors. WebSocket subscription established.
- Done: Real-time activity feed showing agent events via WebSocket.

---

## Plan 07: Briefing Frontend (In-App Display + Settings + Empty State)

**Wave:** 3 (depends on Plan 05)
**Stories:** 3-3 (briefing in-app), 3-5 (configurable time -- frontend), 3-10 (empty state)
**Estimated effort:** 25-35 min Claude execution

### Objective

Build the in-app briefing display (dashboard hero), briefing settings UI, briefing history, and empty state for new users.

### Tasks

**Task 1: Briefing display component**
- Files: `frontend/src/components/BriefingCard.tsx`, `frontend/src/components/BriefingDetail.tsx`
- Action:
  - `BriefingCard` -- hero component displayed prominently at top of dashboard when unread briefing exists:
    - Personalized greeting: "Good morning, {name}!" (time-aware: morning/afternoon/evening)
    - Summary cards showing key metrics: new matches count, pending approvals, pipeline updates
    - Expandable sections: Summary, Actions Needed, New Matches, Activity Log
    - "Mark as Read" button that calls `POST /api/v1/briefings/{id}/read` and clears notification badge
    - Notification badge on nav/header when unread briefing exists
    - Lite briefing rendering: if briefing_type="lite", show softer styling with "We're having some trouble today" message and cached data
  - `BriefingDetail` -- full-page view for individual briefing:
    - Accessed from briefing history or "View Full Briefing" link
    - Shows complete briefing content with all sections expanded
    - Previous/Next navigation between briefings
  - Fetch latest briefing from `GET /api/v1/briefings/latest` on dashboard load
- Verify: Components render without errors.
- Done: Briefing display with greeting, metrics, expandable sections, and lite briefing support.

**Task 2: Briefing settings + history**
- Files: `frontend/src/components/BriefingSettings.tsx`, `frontend/src/components/BriefingHistory.tsx`
- Action:
  - `BriefingSettings`:
    - Hour dropdown (1-12 AM/PM format, converted to 24h for API)
    - Timezone display (auto-detected from browser via `Intl.DateTimeFormat().resolvedOptions().timeZone`, editable)
    - Delivery channel checkboxes: In-App, Email, Both (at least one required)
    - Default: 8:00 AM local time, both channels
    - Save calls `PUT /api/v1/briefings/settings`
    - "Changes take effect from tomorrow" note
    - Place in Settings page or as a section in preferences
  - `BriefingHistory`:
    - Paginated list of past briefings (last 30 days) from `GET /api/v1/briefings`
    - Each entry: date, type (full/lite), read status, summary preview
    - Click to open BriefingDetail
  - Empty state for new users (Story 3-10):
    - If no briefings exist yet: show encouraging message "Your first briefing is being prepared!"
    - Tips: "Add more skills to your profile", "Fine-tune your deal-breakers"
    - Show that agents are working (link to activity feed)
- Verify: Components render without errors. Settings form submits successfully.
- Done: Briefing settings with time/timezone/channel config. History view. Empty state for new users.

---

## Plan 08: Integration Tests + VCR Cassettes + Phase Verification

**Wave:** 4 (depends on Waves 1-3)
**Stories:** All -- cross-cutting verification
**Estimated effort:** 25-35 min Claude execution

### Objective

Write tests that verify all 5 success criteria. Use VCR.py for deterministic LLM call recording. Test tier enforcement for all levels. Verify brake propagation. Verify briefing fallback.

### Tasks

**Task 1: Tier enforcement tests (TDD-style)**
- Files: `backend/tests/unit/test_agents/test_tier_enforcement.py`, `backend/tests/conftest.py` (update)
- Action:
  - Add fixtures to conftest.py:
    - `mock_user_l0`, `mock_user_l1`, `mock_user_l2`, `mock_user_l3` -- create user_preferences rows with each tier level
    - `redis_brake_active` -- sets `paused:{user_id}` in test Redis
    - `redis_brake_inactive` -- ensures no brake key
  - Test cases in `test_tier_enforcement.py`:
    - `test_l0_user_gets_suggestion_only` -- L0 user's agent output action starts with "suggest:", never direct execution
    - `test_l0_user_cannot_write` -- L0 user write action raises TierViolation
    - `test_l1_user_can_read_not_write` -- L1 read succeeds, write raises TierViolation
    - `test_l2_write_action_queues_for_approval` -- L2 write action returns requires_approval=True, creates ApprovalQueueItem in DB
    - `test_l2_read_action_executes_directly` -- L2 read action executes without approval
    - `test_l3_executes_directly` -- L3 actions execute without approval
    - `test_brake_blocks_all_tiers` -- even L3 is blocked when brake is active (raises BrakeActive)
    - `test_brake_check_happens_before_tier_check` -- verify brake is checked first (important for safety)
  - Use a simple `TestAgent(BaseAgent)` subclass with dummy execute() for these tests
- Verify: `cd backend && python -m pytest tests/unit/test_agents/test_tier_enforcement.py -v` -- all tests pass.
- Done: All tier enforcement behaviors verified by tests. Success criterion 4 met.

**Task 2: Brake + briefing integration tests**
- Files: `backend/tests/unit/test_agents/test_brake.py`, `backend/tests/unit/test_agents/test_briefing.py`, `backend/tests/conftest.py` (update VCR config)
- Action:
  - Add VCR config to conftest.py:
    ```python
    @pytest.fixture
    def vcr_config():
        return {
            "filter_headers": ["authorization", "x-api-key", "api-key"],
            "record_mode": "none",
            "cassette_library_dir": "backend/tests/cassettes",
            "decode_compressed_response": True,
        }
    ```
  - Create `backend/tests/cassettes/` directory
  - In `test_brake.py`:
    - `test_activate_brake_sets_redis_flag` -- activate_brake creates `paused:{user_id}` key
    - `test_activate_brake_transitions_to_pausing` -- brake_state hash shows "pausing"
    - `test_verify_completion_transitions_to_paused` -- after verification, state is "paused"
    - `test_resume_clears_brake_flag` -- resume_agents deletes Redis key, state is "running"
    - `test_brake_publishes_websocket_event` -- mock Redis pub/sub, verify event published
    - `test_approval_items_paused_on_brake` -- pending approvals get status="paused"
  - In `test_briefing.py`:
    - `test_lite_briefing_returned_on_failure` -- when generate_full_briefing raises, lite briefing is returned from cache
    - `test_lite_briefing_no_cache` -- when no cache exists, minimal briefing returned
    - `test_successful_briefing_cached` -- after successful generation, Redis cache is set with 48h TTL
    - `test_briefing_empty_state_for_new_user` -- first briefing with zero matches returns encouraging message
    - `test_briefing_retry_scheduled_on_failure` -- failure schedules retry in 1 hour
  - For briefing tests that need LLM responses: create VCR cassette files manually with recorded response format (or use `record_mode="once"` on first run with a real API key, then switch to "none")
- Verify: `cd backend && python -m pytest tests/unit/test_agents/ -v` -- all tests pass.
- Done: Brake state machine and briefing fallback verified by tests. Success criteria 1, 2, 5 met.

**Task 3: WebSocket + end-to-end verification**
- Files: `backend/tests/integration/test_agent_websocket.py`
- Action:
  - Test that agent events flow through WebSocket:
    - `test_activity_event_received_via_websocket` -- publish event to Redis `agent:status:{user_id}`, verify WebSocket client receives it
    - `test_brake_event_received_via_websocket` -- activate brake, verify WebSocket client receives "system.brake.activated"
    - `test_briefing_ready_event_via_websocket` -- deliver briefing, verify "system.briefing.ready" event
  - Use FastAPI TestClient with WebSocket support (`client.websocket_connect`)
  - If WebSocket tests are too flaky for CI, mark as `@pytest.mark.integration` and document manual verification steps
  - Final verification checklist (run all together):
    - `python -m pytest tests/unit/test_agents/ -v` -- all tier, brake, briefing tests pass
    - Verify emergency brake module imports: `python -c "from app.agents.brake import activate_brake, resume_agents, check_brake"`
    - Verify briefing pipeline imports: `python -c "from app.agents.briefing.generator import generate_full_briefing; from app.agents.briefing.fallback import generate_briefing_with_fallback"`
    - Verify orchestrator imports: `python -c "from app.agents.orchestrator import TaskRouter"`
- Verify: All tests pass. Import verification commands succeed.
- Done: WebSocket event flow verified. All 5 success criteria have backing tests or verifiable behavior.

---

## Phase Verification Checklist

After all 8 plans complete, verify these directly map to success criteria:

| # | Success Criterion | Verified By |
|---|-------------------|-------------|
| 1 | Emergency brake visible on every page, pauses within 30s | Plan 06 (frontend button), Plan 03 (brake module), Plan 08 (brake tests) |
| 2 | Daily briefing at configured time, in-app + email, within 15 min | Plan 05 (pipeline + RedBeat), Plan 07 (frontend), Plan 08 (briefing tests) |
| 3 | Activity feed shows real-time updates via WebSocket | Plan 06 (activity feed component), Plan 08 (WebSocket tests) |
| 4 | Autonomy L0-L3 enforced and verifiable | Plan 03 (tier enforcer), Plan 08 (tier tests) |
| 5 | Lite briefing from cache on failure | Plan 05 (fallback module), Plan 08 (fallback tests) |
