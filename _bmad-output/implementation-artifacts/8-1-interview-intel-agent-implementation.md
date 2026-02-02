# Story 8.1: Interview Intel Agent Implementation

Status: done

## Story

As a **system**,
I want **an Interview Intel Agent that generates prep briefings**,
So that **users are well-prepared for interviews automatically**.

## Acceptance Criteria

1. **AC1: Interview detection trigger** — Given the Interview Intel Agent is deployed, when an interview is detected (from pipeline status change to "interview" or manual trigger via API), then the agent kicks off the research workflow for that interview.
2. **AC2: Research workflow orchestration** — Given an interview is detected, when the agent executes, then it orchestrates research sub-steps: (a) company research stub, (b) interviewer research stub (if name known), (c) role-specific question generation stub, (d) STAR response suggestions stub. Each sub-step returns structured data that feeds into the briefing.
3. **AC3: Prep briefing generation and storage** — Given research sub-steps have completed, when the agent assembles the briefing, then a structured prep briefing is persisted to the `agent_outputs` table with `agent_type = "interview_intel"` and the briefing data in the `output` JSON column.
4. **AC4: Delivery scheduling** — Given a prep briefing has been generated, when the interview datetime is known, then the agent schedules a Celery task to deliver the briefing 24 hours before the interview (or immediately if < 24 hours away).
5. **AC5: Celery task integration** — Given the agent exists, when invoked via Celery, then it follows the established task pattern: lazy imports, `_run_async()` wrapper, Langfuse trace creation, retry with backoff.
6. **AC6: Emergency brake respect** — Given the emergency brake is active for a user, when the interview intel agent is triggered, then it raises `BrakeActive` and does not execute.

## Tasks / Subtasks

- [x] Task 1: Create InterviewIntelAgent class (AC: #1, #2, #3, #6)
  - [x]1.1 Create `backend/app/agents/core/interview_intel_agent.py` extending `BaseAgent` with `agent_type = "interview_intel"`
  - [x]1.2 Implement `execute(user_id, task_data)` that expects `task_data` to contain `application_id` and optional `interview_datetime`, `interviewer_names`, `company_name`
  - [x]1.3 Implement `_run_company_research(company_name)` stub returning structured dict with placeholder keys: `mission`, `recent_news`, `products`, `competitors`, `culture_indicators`
  - [x]1.4 Implement `_run_interviewer_research(names)` stub returning list of dicts with placeholder keys: `name`, `role`, `career_highlights`, `talking_points`
  - [x]1.5 Implement `_generate_questions(role_title, company_name, seniority)` stub returning categorized question list: `behavioral`, `technical`, `company_specific`, `role_specific`
  - [x]1.6 Implement `_generate_star_suggestions(questions, profile)` stub returning list of STAR outlines keyed to questions
  - [x]1.7 Implement `_assemble_briefing(company_research, interviewer_research, questions, star_suggestions)` that merges all sub-step outputs into a single briefing dict
  - [x]1.8 Return `AgentOutput` with `action="interview_prep_complete"`, briefing data in `output.data`, and confidence based on data completeness

- [x] Task 2: Create Celery task for InterviewIntelAgent (AC: #5)
  - [x]2.1 Add `agent_interview_intel` task to `backend/app/worker/tasks.py` on the `"agents"` queue, following the `agent_job_scout` pattern exactly
  - [x]2.2 Use lazy imports, `_run_async()`, Langfuse trace, max_retries=2, default_retry_delay=60

- [x] Task 3: Implement delivery scheduling (AC: #4)
  - [x]3.1 After briefing generation, compute delivery time: `interview_datetime - 24h`, clamped to `now` if < 24h away
  - [x]3.2 Schedule a `briefing_generate` task (existing) with the computed ETA and `channels=["in_app", "email"]`, passing the interview briefing ID in task_data
  - [x]3.3 Store the scheduled delivery task ID in the briefing output data for traceability

- [x]Task 4: Write unit tests (AC: #1-#6)
  - [x]4.1 Create `backend/tests/unit/test_agents/test_interview_intel_agent.py`
  - [x]4.2 Test execute() produces correct AgentOutput structure with all briefing sections
  - [x]4.3 Test execute() with missing interviewer names skips interviewer research
  - [x]4.4 Test execute() with missing interview_datetime skips delivery scheduling
  - [x]4.5 Test delivery scheduling computes correct ETA (24h before, and immediate if < 24h)
  - [x]4.6 Test BrakeActive is raised when brake is active (inherited from BaseAgent.run())
  - [x]4.7 Test Celery task follows the standard pattern (lazy imports, Langfuse trace)

## Dev Notes

### Architecture Compliance

- **Agent location**: `backend/app/agents/core/interview_intel_agent.py` — follows the `core/` directory for system agents (like `job_scout.py`, `pipeline_agent.py`, `followup_agent.py`)
- **Agent pattern**: Must extend `BaseAgent`, set `agent_type = "interview_intel"`, override `execute()` → return `AgentOutput`
- **AgentType enum**: `INTERVIEW_INTEL = "interview_intel"` already exists in `backend/app/db/models.py:68-77` — do NOT modify
- **Celery task pattern**: Follow `agent_job_scout` exactly — `@celery_app.task(bind=True, ...)`, lazy imports inside `async def _execute()`, `_run_async()` wrapper, Langfuse trace with `create_agent_trace()` and `flush_traces()` in `finally`
- **Research sub-steps are stubs**: Stories 8-2 through 8-5 implement the real research logic. This story creates the agent skeleton with stub methods that return placeholder data. Stubs must return the correct data shape so downstream code (briefing assembly, tests) works.
- **Delivery scheduling**: Use `celery_app.send_task()` with `eta=` parameter for time-delayed delivery. Do NOT create a new beat schedule entry.
- **No new DB tables**: Briefing output is stored via `BaseAgent._record_output()` in `agent_outputs` table. No new tables needed.
- **No new API endpoints**: The agent is invoked via Celery task, not directly via API. API endpoints for interview prep come in later stories (8-6).

### Project Structure Notes

- Agent file goes in `backend/app/agents/core/` alongside `job_scout.py`, `pipeline_agent.py`, `followup_agent.py`
- Test file goes in `backend/tests/unit/test_agents/` — create directory if needed
- Celery task added to existing `backend/app/worker/tasks.py`

### References

- [Source: backend/app/agents/base.py — BaseAgent class, AgentOutput dataclass, BrakeActive exception]
- [Source: backend/app/agents/core/job_scout.py — Reference agent implementation pattern]
- [Source: backend/app/worker/tasks.py — Celery task pattern with lazy imports and Langfuse]
- [Source: backend/app/db/models.py:68-77 — AgentType enum with INTERVIEW_INTEL]
- [Source: _bmad-output/planning-artifacts/epics.md:2487-2504 — Epic 8, Story 8.1 definition]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Route Taken

SIMPLE (score: 3/16)

### GSD Subagents Used

none (direct execution)

### Debug Log References

- Mock patch paths needed correction: `celery_app` lazy import resolved to `app.worker.celery_app.celery_app`, `check_brake` to `app.agents.brake.check_brake`

### Completion Notes List

- Created InterviewIntelAgent extending BaseAgent with `agent_type = "interview_intel"`
- Implemented execute() with 6-step workflow: validate → company research → interviewer research → questions → STAR → assemble briefing
- All research sub-steps are stubs returning correctly-shaped data (real implementations in 8-2 to 8-5)
- Delivery scheduling via `celery_app.send_task()` with ETA 24h before interview, clamped to now if < 24h
- Confidence computation based on data completeness
- Added `agent_interview_intel` Celery task following established pattern
- 17 tests: 7 execute, 3 delivery scheduling, 1 brake, 3 Celery task, 3 confidence

### Change Log

- 2026-02-02: Story implemented, all 17 tests passing
- 2026-02-02: Code review passed — no issues found specific to 8-1; all HIGH/MEDIUM issues from review were in downstream stories (8-2 to 8-6)

### File List

#### Files to CREATE
- `backend/app/agents/core/interview_intel_agent.py`
- `backend/tests/unit/test_agents/test_interview_intel_agent.py`

#### Files to MODIFY
- `backend/app/worker/tasks.py`
