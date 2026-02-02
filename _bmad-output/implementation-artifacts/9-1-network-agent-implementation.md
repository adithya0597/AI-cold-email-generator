# Story 9.1: Network Agent Implementation

Status: done

## Story

As a **system**,
I want **a Network Agent that helps users build professional relationships**,
So that **users can leverage warm introductions for job opportunities**.

## Acceptance Criteria

1. **AC1: Target company analysis trigger** — Given the Network Agent is deployed, when a user has target companies identified (from saved jobs or manual input), then the agent kicks off the network analysis workflow.
2. **AC2: Network analysis workflow orchestration** — Given target companies exist, when the agent executes, then it orchestrates: (a) warm path analysis stub, (b) relationship opportunity identification stub, (c) introduction request draft generation stub. Each sub-step returns structured data.
3. **AC3: Network output generation and storage** — Given analysis sub-steps have completed, when the agent assembles results, then a structured network analysis is persisted to `agent_outputs` table with `agent_type = "network"` and data in the `output` JSON column.
4. **AC4: Autonomy level respect** — Given user autonomy settings exist, when the agent runs, then it respects autonomy level: L0=suggestions only, L1=drafts generated, L2=drafts with approval queue. All direct outreach ALWAYS requires human approval regardless of autonomy level.
5. **AC5: Celery task integration** — Given the agent exists, when invoked via Celery, then it follows the established task pattern: lazy imports, `_run_async()` wrapper, Langfuse trace creation, retry with backoff.
6. **AC6: Emergency brake respect** — Given the emergency brake is active for a user, when the network agent is triggered, then it raises `BrakeActive` and does not execute.
7. **AC7: Suggestion-only constraint** — Given the Network Agent operates, when producing outputs, then it NEVER automates LinkedIn actions or direct messaging. All outputs are suggestions/drafts for user to execute manually.

## Tasks / Subtasks

- [x] Task 1: Create NetworkAgent class (AC: #1, #2, #3, #4, #6, #7)
  - [x] 1.1 Create `backend/app/agents/core/network_agent.py` extending `BaseAgent` with `agent_type = "network"`
  - [x] 1.2 Implement `execute(user_id, task_data)` that expects `task_data` to contain `target_companies` (list of company names/IDs) and optional `connection_data` (user's network info)
  - [x] 1.3 Implement `_analyze_warm_paths(target_companies, connection_data)` stub returning list of dicts with keys: `company`, `paths` (list of path dicts with `contact_name`, `relationship`, `path_type`, `strength`)
  - [x] 1.4 Implement `_identify_opportunities(target_companies)` stub returning list of dicts with keys: `company`, `opportunities` (list with `type`, `description`, `suggested_action`)
  - [x] 1.5 Implement `_generate_intro_drafts(warm_paths)` stub returning list of dicts with keys: `recipient`, `connection`, `message_draft`, `context`
  - [x] 1.6 Implement `_assemble_network_analysis(warm_paths, opportunities, intro_drafts)` that merges all sub-step outputs
  - [x] 1.7 Return `AgentOutput` with `action="network_analysis_complete"`, data in `output.data`, confidence based on data completeness, `requires_approval=True` for any outreach drafts

- [x] Task 2: Create Celery task for NetworkAgent (AC: #5)
  - [x] 2.1 Add `agent_network` task to `backend/app/worker/tasks.py` on the `"agents"` queue, following the `agent_interview_intel` pattern exactly
  - [x] 2.2 Use lazy imports, `_run_async()`, Langfuse trace, max_retries=2, default_retry_delay=60

- [x] Task 3: Write unit tests (AC: #1-#7)
  - [x] 3.1 Create `backend/tests/unit/test_agents/test_network_agent.py`
  - [x] 3.2 Test execute() produces correct AgentOutput structure with all sections
  - [x] 3.3 Test execute() with empty target_companies returns meaningful guidance
  - [x] 3.4 Test execute() with missing connection_data still produces opportunities
  - [x] 3.5 Test requires_approval=True when intro drafts are generated
  - [x] 3.6 Test BrakeActive is raised when brake is active
  - [x] 3.7 Test Celery task follows the standard pattern
  - [x] 3.8 Test confidence computation based on data completeness

## Dev Notes

### Architecture Compliance

- **Agent location**: `backend/app/agents/core/network_agent.py` — follows `core/` directory for system agents
- **Agent pattern**: Must extend `BaseAgent`, set `agent_type = "network"`, override `execute()` → return `AgentOutput`
- **AgentType enum**: `NETWORK = "network"` already exists in `backend/app/db/models.py:68-77` — do NOT modify
- **Celery task pattern**: Follow `agent_interview_intel` exactly — `@celery_app.task(bind=True, ...)`, lazy imports inside `async def _execute()`, `_run_async()` wrapper, Langfuse trace with `create_agent_trace()` and `flush_traces()` in `finally`
- **Research sub-steps are stubs**: Stories 9-2 through 9-5 implement real logic. This story creates the agent skeleton with stub methods returning placeholder data. Stubs must return the correct data shape.
- **Suggestion-only constraint**: Per ROADMAP, Network Agent is redesigned as suggestion-only — NO LinkedIn automation (legal risk). All outputs are drafts/suggestions for manual user execution.
- **Approval queue**: Use `_queue_for_approval()` from BaseAgent for outreach drafts. The `ApprovalQueueItem` model already exists with 48-hour expiry.
- **No new DB tables**: Output stored via `BaseAgent._record_output()` in `agent_outputs`. No new tables needed.
- **No new API endpoints**: Agent invoked via Celery task. API endpoints come in later stories (9-7).

### Existing Utilities to Use

- `get_user_context(user_id)` — fetch user preferences and profile
- `check_brake(user_id)` — emergency brake check (handled by BaseAgent.run())
- `_queue_for_approval()` — BaseAgent method for L2 approval workflow
- `get_redis_client()` from `app.cache.redis_client` — for pub/sub events
- `create_agent_trace()`, `flush_traces()` from `app.observability.langfuse_client`

### Previous Epic Intelligence (Epic 8)

- Mock patch paths must target source module (e.g., `app.agents.brake.check_brake`)
- Use `asyncio.gather()` for parallel independent operations from the start
- All `to_dict()` methods must include ALL fields — test with key assertions
- Celery task pattern: `_run_async()` wrapper around async `_execute()`

### Project Structure Notes

- Agent file: `backend/app/agents/core/network_agent.py`
- Test file: `backend/tests/unit/test_agents/test_network_agent.py`
- Celery task: added to existing `backend/app/worker/tasks.py`

### References

- [Source: backend/app/agents/base.py — BaseAgent class, AgentOutput dataclass, BrakeActive exception, _queue_for_approval()]
- [Source: backend/app/agents/core/interview_intel_agent.py — Reference agent implementation pattern]
- [Source: backend/app/worker/tasks.py — Celery task pattern with lazy imports and Langfuse]
- [Source: backend/app/db/models.py:68-77 — AgentType enum with NETWORK]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Route Taken

SIMPLE (score: 3/16)

### GSD Subagents Used

none (direct execution)

### Debug Log References

- No issues encountered

### Completion Notes List

- Created NetworkAgent extending BaseAgent with `agent_type = "network"`
- Implemented execute() with 3-step workflow: warm paths → opportunities → intro drafts → assemble
- All research sub-steps are stubs returning correctly-shaped data (real implementations in 9-2 to 9-5)
- Suggestion-only constraint enforced: agent only returns drafts/suggestions, never automates actions
- requires_approval=True when intro drafts are generated
- Confidence computed from data completeness (warm paths, opportunities, drafts)
- Added `agent_network` Celery task following established pattern
- 17 tests: 10 execute, 1 brake, 3 Celery task, 3 confidence

### Change Log

- 2026-02-02: Story implemented, all 17 tests passing

### File List

#### Files to CREATE
- `backend/app/agents/core/network_agent.py`
- `backend/tests/unit/test_agents/test_network_agent.py`

#### Files to MODIFY
- `backend/app/worker/tasks.py`
