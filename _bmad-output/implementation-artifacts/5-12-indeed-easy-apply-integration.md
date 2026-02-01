# Story 5.12: Indeed Easy Apply Integration

Status: review

## Story

As an **Apply Agent**,
I want **to submit applications via Indeed Easy Apply**,
so that **users can apply to Indeed jobs seamlessly**.

## Acceptance Criteria

1. **AC1 - Indeed Source Detection:** Given a job record with source='indeed', when the ApplyAgent selects submission method, then it returns 'indeed_easy_apply' as the method type.

2. **AC2 - Indeed Submission Strategy:** Given an Indeed Easy Apply job, when the agent prepares submission, then it builds the submission payload with required fields (name, email, resume_path) from user profile.

3. **AC3 - Rate Limit:** Given Indeed-specific rate limits, when the agent checks limits, then it respects a max of 50 Indeed applications per day separate from the general daily limit.

4. **AC4 - Tests:** Given the Indeed integration exists, when unit tests run, then coverage exists for source detection, payload building, and rate limiting.

## Tasks / Subtasks

- [x] Task 1: Enhance submission method selection for Indeed (AC: #1)
  - [x]1.1: Update `_select_submission_method()` to detect Indeed jobs via source field
  - [x]1.2: Return 'indeed_easy_apply' for Indeed-sourced jobs with URLs

- [x] Task 2: Add Indeed submission payload builder (AC: #2)
  - [x]2.1: Add `_build_indeed_payload()` method that extracts name, email, resume from profile
  - [x]2.2: Include in apply agent output data when method is indeed_easy_apply

- [x] Task 3: Add Indeed-specific rate limit (AC: #3)
  - [x]3.1: Add INDEED_DAILY_LIMIT constant (50)
  - [x]3.2: Add `_check_indeed_limit()` that counts today's Indeed applications

- [x] Task 4: Write tests (AC: #4)
  - [x]4.1: Test Indeed source detection
  - [x]4.2: Test payload structure
  - [x]4.3: Test Indeed rate limit

## Dev Notes

### Architecture Compliance

1. **This does NOT implement actual Indeed API calls.** It adds Indeed-specific method detection, payload building, and rate limiting. The actual submission (browser automation or API) is future work.

2. **Indeed jobs have `source='indeed'`** in the jobs table (set by JobScoutAgent in Epic 4).

3. **The Indeed rate limit is separate from the general daily limit.** A user can hit 50 Indeed applications AND still have general applications available.

### File Structure Requirements

**Files to MODIFY:**
```
backend/app/agents/pro/apply_agent.py           # Indeed method detection, payload, rate limit
backend/tests/unit/test_agents/test_apply_agent.py  # Indeed-specific tests
```

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
SIMPLE (score: 0/16)

### Completion Notes List
- Enhanced _select_submission_method() to detect Indeed source
- Added _build_indeed_payload() for Indeed-specific submission data
- Added INDEED_DAILY_LIMIT (50) and _check_indeed_limit()
- 3 new tests for Indeed detection, payload, and rate limit

### Change Log
- 2026-02-01: Added Indeed Easy Apply integration + 3 tests

### File List
**Modified:**
- `backend/app/agents/pro/apply_agent.py`
- `backend/tests/unit/test_agents/test_apply_agent.py`
