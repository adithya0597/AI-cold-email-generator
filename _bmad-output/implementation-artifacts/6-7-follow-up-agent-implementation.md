# Story 6.7: Follow-up Agent Implementation

Status: review

## Story

As a **system**,
I want **a Follow-up Agent that suggests timely follow-ups**,
So that **users don't miss opportunities due to lack of follow-up**.

## Acceptance Criteria

1. **AC1 - Follow-up Timing:** Given an application reaches a follow-up milestone, when the agent evaluates it, then it calculates optimal follow-up timing: after application (5-7 business days), after interview (1-2 business days), after no response (2 weeks).
2. **AC2 - Draft Generation:** Given a follow-up is due, when the agent processes the application, then it generates a draft follow-up message.
3. **AC3 - Briefing Integration:** Given follow-ups are due, when the agent completes, then follow-up suggestions appear as "suggested action" items retrievable via API.
4. **AC4 - Aggressiveness Preference:** Given a user has set follow-up aggressiveness preference, when the agent calculates timing, then it adjusts timing based on the preference (conservative / normal / aggressive).
5. **AC5 - Agent Output:** Given the agent runs, when it completes, then it returns a standard AgentOutput with action, rationale, confidence, and follow-up data.
6. **AC6 - Celery Task:** Given the follow-up agent is registered, when dispatched via orchestrator, then it runs as a Celery task in the agents queue.

## Tasks / Subtasks

- [x] Task 1: Create FollowUpAgent class (AC: #1, #4, #5)
  - [x]1.1: Create `backend/app/agents/core/followup_agent.py` inheriting from BaseAgent
  - [x]1.2: Implement `execute()` — load user applications needing follow-up
  - [x]1.3: Implement `_calculate_followup_timing()` with business day logic for each milestone
  - [x]1.4: Implement `_adjust_for_preference()` to scale timing based on aggressiveness preference
  - [x]1.5: Return AgentOutput with follow-up suggestions list in data

- [x] Task 2: Create follow-up draft generator (AC: #2)
  - [x]2.1: Implement `_generate_followup_draft()` method in FollowUpAgent
  - [x]2.2: Use LLM (GPT-3.5-turbo) to generate subject line and email body
  - [x]2.3: Include application context (company, title, status, applied date) in prompt

- [x] Task 3: Create follow-up suggestions storage (AC: #3)
  - [x]3.1: Implement `_store_suggestions()` to save follow-up suggestions to `followup_suggestions` table
  - [x]3.2: Add GET `/api/v1/applications/followups` endpoint to retrieve pending suggestions
  - [x]3.3: Add PATCH `/api/v1/applications/followups/{id}/dismiss` endpoint to dismiss a suggestion

- [x] Task 4: Register Celery task and orchestrator routing (AC: #6)
  - [x]4.1: Add `agent_followup` Celery task to `worker/tasks.py`
  - [x]4.2: Add `followup` entry to `TASK_ROUTING` in orchestrator.py

- [x] Task 5: Write comprehensive tests (AC: #1-#6)
  - [x]5.1: Write agent tests (>=5 tests): timing calculation, preference adjustment, draft generation, no applications needing followup, agent output format
  - [x]5.2: Write API endpoint tests (>=3 tests): list followups, dismiss followup, empty list

## Dev Notes

### Architecture Compliance
- Backend agent pattern: inherit from `BaseAgent`, override `execute()`, return `AgentOutput`
- Use raw SQL via `text()` with parameterized queries (no ORM models)
- Lazy imports inside methods (same pattern as PipelineAgent)
- LLM calls use lazy `from openai import AsyncOpenAI` inside method body
- Celery task pattern: `@celery_app.task(bind=True, name=..., queue="agents", max_retries=2)`
- Orchestrator routing: add to `TASK_ROUTING` dict in orchestrator.py
- FastAPI endpoints: add to applications router with `Depends(get_current_user_id)`
- Follow-up timing is business-day aware (skip weekends)
- The `followup_suggestions` table doesn't exist yet — create it via raw SQL in the agent's first run (CREATE TABLE IF NOT EXISTS pattern) or assume it exists from migration

### File Structure Requirements

**Files to CREATE:**
```
backend/app/agents/core/followup_agent.py                # Follow-up agent
backend/tests/unit/test_agents/test_followup_agent.py    # Agent tests
backend/tests/unit/test_api/test_followup_endpoints.py   # API tests
```

**Files to MODIFY:**
```
backend/app/agents/orchestrator.py                       # Add followup to TASK_ROUTING
backend/app/worker/tasks.py                              # Add agent_followup Celery task
backend/app/api/v1/applications.py                       # Add followup endpoints
```

### Previous Story Intelligence
- Story 6-1 created PipelineAgent with the same BaseAgent pattern — follow exact same structure
- `_mock_session_cm()` helper and `_sample_application_row()` pattern from test_pipeline_agent.py
- Detection method tracking uses `detection_method` field in audit trail
- Email parser has `detect_enhanced()` async method — similar LLM pattern for draft generation
- Lazy import pattern: `from openai import AsyncOpenAI` inside method, patch `openai.AsyncOpenAI` in tests
- Applications router already has PATCH status endpoint from Story 6-5

### Testing Requirements
- **Timing Tests:** Test each milestone timing (post-application, post-interview, no-response)
- **Preference Tests:** Test conservative/normal/aggressive adjustments
- **Draft Tests:** Test LLM draft generation with mocked OpenAI
- **No-followup Test:** Test when no applications need follow-up
- **API Tests:** Test GET followups, PATCH dismiss, empty state
- Use `patch` + `AsyncMock` for DB sessions and OpenAI, same pattern as test_pipeline_agent.py

## Dev Agent Record
### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)
### Route Taken
SIMPLE (score: 4/16, overridden by user flag)
### GSD Subagents Used
None (direct execution)
### Debug Log References
- Fix: Patched `app.db.engine.AsyncSessionLocal` instead of `app.api.v1.applications.AsyncSessionLocal` for lazy import
### Completion Notes List
- Created FollowUpAgent with business-day timing, aggressiveness preference, LLM draft generation
- Timing rules: applied (6 bdays), interview (2 bdays), screening (10 bdays)
- Aggressiveness multipliers: conservative (1.5x), normal (1.0x), aggressive (0.7x)
- LLM draft generation via GPT-3.5-turbo with template fallback
- followup_suggestions table created via CREATE TABLE IF NOT EXISTS
- GET /followups and PATCH /followups/{id}/dismiss endpoints
- Celery task and orchestrator routing registered
- 15 tests total (11 agent + 4 API), all passing
### Change Log
- 2026-02-01: Story implemented and moved to review
### File List
**Created:**
- backend/app/agents/core/followup_agent.py
- backend/tests/unit/test_agents/test_followup_agent.py
- backend/tests/unit/test_api/test_followup_endpoints.py

**Modified:**
- backend/app/agents/orchestrator.py
- backend/app/worker/tasks.py
- backend/app/api/v1/applications.py
