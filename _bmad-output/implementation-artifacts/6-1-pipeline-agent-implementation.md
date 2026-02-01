# Story 6.1: Pipeline Agent Implementation

Status: review

## Story

As a **system**,
I want **a Pipeline Agent that tracks application status from email**,
So that **users have auto-updating application tracking**.

## Acceptance Criteria

1. **AC1 - Agent Structure:** Given the Pipeline Agent is deployed, when it extends BaseAgent with `agent_type = "pipeline"`, then it follows the established agent pattern (execute method, AgentOutput return, fire-and-forget persistence).

2. **AC2 - Email Parsing:** Given the agent receives email content (subject + body), when it analyzes the email, then it detects application status changes: rejection, interview request, offer, applied confirmation — using keyword/pattern matching and optional LLM classification.

3. **AC3 - Status Update:** Given a status change is detected with sufficient confidence (>=0.7), when the agent processes it, then it updates the `applications` table with the new status and creates an audit trail entry in `application_status_changes`.

4. **AC4 - Confidence & Evidence:** Given the agent detects a status change, when it returns AgentOutput, then the output includes confidence level (0.0-1.0) and evidence (email snippet that triggered the detection).

5. **AC5 - Ambiguity Handling:** Given an email has ambiguous status signals (confidence < 0.7), when the agent processes it, then it flags the email for user review rather than auto-moving the application status.

6. **AC6 - Celery Task & Orchestrator:** Given the agent is registered, when dispatched via orchestrator, then it runs as a Celery task on the `agents` queue with Langfuse tracing, max 2 retries, and 60s retry delay.

7. **AC7 - Database Tables:** Given the pipeline feature needs email tracking, when the migration runs, then `email_connections` and `application_status_changes` tables exist with proper indexes, soft-delete columns, and foreign keys.

## Tasks / Subtasks

- [x] Task 1: Create database migration for pipeline tables (AC: #7)
  - [x]1.1: Create `email_connections` table (user_id, provider, encrypted tokens, email, connected_at, last_sync_at, status)
  - [x]1.2: Create `application_status_changes` table (application_id, old_status, new_status, detected_at, detection_method, confidence, evidence_snippet, source_email_id)
  - [x]1.3: Add indexes on user_id, application_id, and provider columns
  - [x]1.4: Add soft-delete columns (deleted_at, deleted_by, deletion_reason) to both tables

- [x] Task 2: Implement email status detection service (AC: #2, #4, #5)
  - [x]2.1: Create `backend/app/services/email_parser.py` with `EmailStatusDetector` class
  - [x]2.2: Implement keyword/pattern matching for status detection (rejection, interview, offer, applied)
  - [x]2.3: Return structured result with detected_status, confidence score, and evidence snippet
  - [x]2.4: Handle ambiguous emails — return confidence < 0.7 for unclear signals
  - [x]2.5: Write unit tests for each status detection pattern (>=8 test cases)

- [x] Task 3: Implement PipelineAgent class (AC: #1, #3, #4, #5)
  - [x]3.1: Create `backend/app/agents/core/pipeline_agent.py` extending BaseAgent
  - [x]3.2: Set `agent_type = "pipeline"` class attribute
  - [x]3.3: Implement `execute()` method: validate inputs -> load email content -> detect status -> update DB -> return AgentOutput
  - [x]3.4: Implement `_detect_status()` calling EmailStatusDetector
  - [x]3.5: Implement `_update_application_status()` — update applications table + insert status change audit record
  - [x]3.6: Implement `_flag_for_review()` — create approval queue item for ambiguous emails
  - [x]3.7: Return AgentOutput with action, confidence, evidence, and status change details
  - [x]3.8: Write unit tests (>=6 test cases: happy path, rejection, interview, ambiguous, missing app, error)

- [x] Task 4: Register agent in orchestrator and Celery (AC: #6)
  - [x]4.1: Add `"pipeline"` to TASK_ROUTING in `backend/app/agents/orchestrator.py`
  - [x]4.2: Add `agent_pipeline` Celery task in `backend/app/worker/tasks.py` (lazy imports, Langfuse trace, retry config)
  - [x]4.3: Write unit test for task registration and routing

## Dev Notes

### Architecture Compliance

1. **BaseAgent Pattern:** Extend `BaseAgent` from `app.agents.base`. Set `agent_type = "pipeline"`. Override `execute()` which returns `AgentOutput`. The `run()` method handles lifecycle (brake check, persistence, event publish). [Source: backend/app/agents/base.py]

2. **AgentOutput Structure:** Must return `AgentOutput(action=str, rationale=str, confidence=float, data=dict)`. The `data` dict should contain `detected_status`, `application_id`, `evidence_snippet`, `old_status`, `new_status`. [Source: backend/app/agents/base.py]

3. **Database Access:** Use `AsyncSessionLocal` context manager with raw SQL via `text()`. Lazy import inside methods. Never import DB at module level. [Source: backend/app/agents/pro/apply_agent.py]

4. **Orchestrator Registration:** Add `"pipeline": "app.worker.tasks.agent_pipeline"` to `TASK_ROUTING` dict. [Source: backend/app/agents/orchestrator.py]

5. **Celery Task Pattern:** Use `bind=True`, `queue="agents"`, `max_retries=2`, `default_retry_delay=60`. Lazy imports inside `_execute()`. Create Langfuse trace. Call `flush_traces()` in finally block. [Source: backend/app/worker/tasks.py]

6. **Fire-and-Forget:** The `run()` base method handles `_record_output()`, `_record_activity()`, `_publish_event()` automatically. Don't re-implement these in the agent.

7. **Agent Type Enum:** `pipeline` is already in the `agent_type` enum in the database schema. No migration needed for the enum value. [Source: supabase/migrations/00001_initial_schema.sql line 27]

8. **Status Enum:** The `application_status` enum includes: `applied`, `screening`, `interview`, `offer`, `closed`, `rejected`. Map detected email statuses to these values.

### Previous Story Intelligence

- Epic 5 established the ApplyAgent, CoverLetterAgent, and ResumeAgent patterns — all follow identical BaseAgent extension pattern.
- `_mock_session_cm()` helper used across all test files for DB mocking.
- Tests use `patch("app.agents.orchestrator.get_user_context", ...)` for user context.
- 55 Epic 5 tests all passing as of last commit.
- The `applications` table has columns: id, user_id, job_id, status, applied_at, resume_version_id, created_at, updated_at, deleted_at.
- Code review found duplicate `_load_job()` across agents — consider extracting to shared helper if this agent also needs it.

### Library/Framework Requirements

- No new external dependencies needed.
- Uses existing: SQLAlchemy (async), Pydantic, OpenAI (optional for LLM classification), pytest + pytest-asyncio.
- Email parsing uses Python stdlib `re` module for pattern matching — no new library needed for this story.
- Note: Gmail/Outlook OAuth integration is Story 6-2 and 6-3. This story implements the agent that *processes* email content, not the email fetching itself. The agent receives email content as `task_data`.

### File Structure Requirements

**Files to CREATE:**
```
supabase/migrations/00002_pipeline_tables.sql          # New tables for email tracking
backend/app/services/email_parser.py                    # Email status detection service
backend/app/agents/core/pipeline_agent.py               # Pipeline Agent implementation
backend/tests/unit/test_services/test_email_parser.py   # Email parser tests
backend/tests/unit/test_agents/test_pipeline_agent.py   # Pipeline Agent tests
```

**Files to MODIFY:**
```
backend/app/agents/orchestrator.py                      # Add pipeline to TASK_ROUTING
backend/app/worker/tasks.py                             # Add agent_pipeline Celery task
```

### Testing Requirements

- **Email Parser Tests:** Test each status pattern (rejection words, interview phrases, offer language, confirmation). Test ambiguous emails return low confidence. Test edge cases (empty body, non-English snippets). Minimum 8 test cases.
- **Pipeline Agent Tests:** Test happy path (status detected + DB updated). Test each status type. Test ambiguous email flagged for review. Test missing application returns failure. Test error handling. Minimum 6 test cases.
- **Mock Pattern:** Use `_mock_session_cm()` for all DB operations. Patch `AsyncSessionLocal` with `side_effect` for multiple session calls. Import agent inside `with patch(...)` block.

### References

- [Source: backend/app/agents/base.py] — BaseAgent, AgentOutput
- [Source: backend/app/agents/orchestrator.py] — TASK_ROUTING, dispatch_task, get_user_context
- [Source: backend/app/worker/tasks.py] — Celery task pattern (agent_job_scout example)
- [Source: backend/app/agents/pro/apply_agent.py] — Most recent agent implementation pattern
- [Source: supabase/migrations/00001_initial_schema.sql] — Schema, enums, table patterns
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-6] — Epic 6 requirements

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5

### Route Taken

SIMPLE (score: 6/16, overridden by user flag)

### GSD Subagents Used

None (direct execution)

### Debug Log References

- Email parser screening pattern required fix: `currently being reviewed` not matched by original regex. Added optional word group `(\w+\s+)?` to pattern.

### Completion Notes List

- Created `email_connections` and `application_status_changes` database tables with indexes and soft-delete
- Implemented `EmailStatusDetector` with regex patterns for rejection, interview, offer, applied, screening
- Confidence threshold at 0.7 — below triggers `pipeline_review_needed` instead of auto-update
- Subject-line matches get +0.05 confidence boost
- PipelineAgent extends BaseAgent with full lifecycle: validate -> load app -> detect -> update/flag
- Registered `pipeline` in orchestrator TASK_ROUTING and added `agent_pipeline` Celery task
- 24 total tests: 14 email parser + 10 pipeline agent, all passing
- No regressions in existing 583 unit tests

### Change Log

- 2026-02-01: Story 6-1 implemented — pipeline agent, email parser, migration, tests

### File List

**Created:**
- `supabase/migrations/00002_pipeline_tables.sql`
- `backend/app/services/email_parser.py`
- `backend/app/agents/core/pipeline_agent.py`
- `backend/tests/unit/test_services/test_email_parser.py`
- `backend/tests/unit/test_agents/test_pipeline_agent.py`

**Modified:**
- `backend/app/agents/orchestrator.py`
- `backend/app/worker/tasks.py`
