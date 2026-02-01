# Story 5.11: Application Failure Handling

Status: review

## Story

As a **user**,
I want **clear feedback when an application fails**,
so that **I can take manual action if needed**.

## Acceptance Criteria

1. **AC1 - Failure Activity:** Given the ApplyAgent fails, when the failure is recorded, then an agent_activity with severity='warning' and event_type='agent.apply.failed' is created with the error reason.

2. **AC2 - Error Details in Activity:** Given a failure, when I view the activity, then data includes: error reason, job URL for manual application, and whether a retry is scheduled.

3. **AC3 - Failed Applications Don't Count:** Given a failed submission, when I check the daily limit, then the failure does NOT count against the application cap (already correct — limit checks applications table which only has successful records).

4. **AC4 - Tests:** Given the failure handling exists, when unit tests run, then coverage exists for failure activity recording and error detail structure.

## Tasks / Subtasks

- [x] Task 1: Add failure notification to ApplyAgent (AC: #1, #2)
  - [x]1.1: Add `_record_failure_activity()` method to ApplyAgent
  - [x]1.2: Call it on job_not_found, missing_materials, manual_required failures

- [x] Task 2: Write tests (AC: #3, #4)
  - [x]2.1: Add failure activity tests to test_apply_agent.py
  - [x]2.2: Verify failure does not create applications table record (daily limit unaffected)

## Dev Notes

### Architecture Compliance

1. **Fire-and-forget pattern** — failure activity recording must not break the failure return flow.
2. **Only record activity for actionable failures** (job_not_found, missing_materials, manual_required) — not for validation errors (missing_job_id, empty_profile).
3. **NO retry logic in this story.** The epic description mentions retries but the Celery task already has max_retries=1.

### File Structure Requirements

**Files to MODIFY:**
```
backend/app/agents/pro/apply_agent.py           # Add failure activity recording
backend/tests/unit/test_agents/test_apply_agent.py  # Add failure activity tests
```

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
SIMPLE (score: 0/16)

### Debug Log References
- No issues encountered.

### Completion Notes List
- Added `_record_failure_activity()` to ApplyAgent
- Called on job_not_found, missing_materials, manual_required failures
- Activity includes job_url for manual fallback
- 2 new tests for failure activity

### Change Log
- 2026-02-01: Added failure activity recording + 2 tests

### File List
**Created:**
(none)

**Modified:**
- `backend/app/agents/pro/apply_agent.py` — Added _record_failure_activity()
- `backend/tests/unit/test_agents/test_apply_agent.py` — Added 2 failure activity tests
