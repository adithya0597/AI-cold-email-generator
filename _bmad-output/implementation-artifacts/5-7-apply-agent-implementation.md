# Story 5.7: Apply Agent Implementation

Status: review

## Story

As a **system**,
I want **an Apply Agent that submits applications autonomously**,
so that **users can apply to jobs without manual form filling**.

## Acceptance Criteria

1. **AC1 - Apply Agent Class:** Given I trigger the ApplyAgent with a job_id, when it executes, then it determines the submission method (api, email_fallback), prepares application materials, and records the outcome.

2. **AC2 - Application Record:** Given the agent submits successfully, when I inspect the database, then an `applications` row exists with user_id, job_id, status='applied', resume_version_id linking to the tailored resume document, and applied_at timestamp.

3. **AC3 - Submission Method Selection:** Given a job record, when the agent analyzes it, then it selects the best method: 'api' for jobs with application URLs, 'email_fallback' for jobs with HR contact info, or returns 'manual_required' if neither is available.

4. **AC4 - Daily Limit Enforcement:** Given tier-based daily limits (Free: 5, Pro: 25, H1B Pro: 25, Career Insurance: 50, Enterprise: 100), when the agent checks limits before applying, then it refuses with `daily_limit_reached` if the user has hit their cap for today.

5. **AC5 - Celery Task Integration:** Given the placeholder `agent_apply` Celery task exists, when the ApplyAgent is implemented, then the task calls `ApplyAgent().run()` instead of returning `not_implemented`.

6. **AC6 - Tests:** Given the ApplyAgent exists, when unit tests run, then coverage exists for successful application, daily limit enforcement, method selection, missing materials handling, and Celery task wiring.

## Tasks / Subtasks

- [x] Task 1: Create ApplyAgent class (AC: #1, #2, #3)
  - [x]1.1: Create `backend/app/agents/pro/apply_agent.py` following ResumeAgent/CoverLetterAgent pattern
  - [x]1.2: Implement `execute()` — validate inputs, check daily limit, select submission method, prepare materials, record application
  - [x]1.3: Implement `_check_daily_limit()` — count today's applications for user, compare against tier limit
  - [x]1.4: Implement `_select_submission_method()` — analyze job record for application URL vs email vs manual
  - [x]1.5: Implement `_prepare_materials()` — load latest tailored resume and cover letter documents for this job
  - [x]1.6: Implement `_record_application()` — insert into applications table with status='applied'

- [x] Task 2: Wire Celery task (AC: #5)
  - [x]2.1: Update `agent_apply` in `backend/app/worker/tasks.py` to import and call `ApplyAgent`

- [x] Task 3: Write comprehensive tests (AC: #6)
  - [x]3.1: Create `backend/tests/unit/test_agents/test_apply_agent.py`
  - [x]3.2: Test happy path — agent records application with correct fields
  - [x]3.3: Test daily limit enforcement — returns failure when limit reached
  - [x]3.4: Test submission method selection — api, email_fallback, manual_required
  - [x]3.5: Test missing materials — returns failure when no resume/cover letter available
  - [x]3.6: Test missing job — returns failure for nonexistent job_id

## Dev Notes

### Architecture Compliance

**CRITICAL — Follow these patterns EXACTLY:**

1. **Follow the ResumeAgent/CoverLetterAgent pattern exactly.** ApplyAgent extends BaseAgent, uses `agent_type = "apply"`, overrides `execute()`.
   [Source: backend/app/agents/pro/cover_letter_agent.py]

2. **Application model already exists** at `backend/app/db/models.py` lines 272-292. Columns: id, user_id, job_id, status (ApplicationStatus enum), applied_at, resume_version_id. Use raw SQL `INSERT INTO applications` like other agents.

3. **ApplicationStatus enum already exists** with values: APPLIED, SCREENING, INTERVIEW, OFFER, CLOSED, REJECTED. Use `'applied'` for new applications.

4. **AgentType.APPLY already exists** in the enum. The Celery task `agent_apply` is already defined as a placeholder.

5. **Daily limits are NOT in the rate limiter.** Application daily limits are separate from API rate limits. Define them as a constant dict in the agent module: `DAILY_APPLICATION_LIMITS = {"free": 5, "pro": 25, "h1b_pro": 25, "career_insurance": 50, "enterprise": 100}`.

6. **This story does NOT implement actual browser automation or API submission.** The agent prepares materials and records the application. Actual submission integrations (Indeed Easy Apply, LinkedIn) are separate stories (5-12, etc.). The `_select_submission_method()` returns the method type; actual submission is a future concern.

7. **NO new API endpoints in this story.** The agent is triggered via the existing Celery task dispatch (`POST /agents/tasks` → orchestrator → `agent_apply` task). The approval queue (story 5-8) adds the user-facing endpoint.

8. **Use `get_user_context()` for profile and preferences** (includes tier info). Use `_load_job()` pattern from CoverLetterAgent for job data.

### Previous Story Intelligence (5-6)

- 17 tests passing for CoverLetterAgent
- CoverLetterAgent pattern: execute() → validate → load job → process → store → return AgentOutput
- Mock pattern: `_mock_session_cm()`, patch at source module, mock OpenAI client

### Library/Framework Requirements

**No new dependencies needed.**

### File Structure Requirements

**Files to CREATE:**
```
backend/app/agents/pro/apply_agent.py         # ApplyAgent class
backend/tests/unit/test_agents/test_apply_agent.py  # Agent tests
```

**Files to MODIFY:**
```
backend/app/worker/tasks.py    # Wire agent_apply task to ApplyAgent
```

**Files to NOT TOUCH:**
```
backend/app/db/models.py                # Application model already exists
backend/app/agents/orchestrator.py      # Routing already maps "apply"
backend/app/api/v1/agents.py            # No new endpoints
backend/app/middleware/rate_limit.py     # API rate limits != application limits
```

### Testing Requirements

- **Backend Framework:** Pytest + pytest-asyncio
- **Mocking:** Mock `AsyncSessionLocal`, mock `get_user_context` (for tier info)
- **Tests to write:**
  - Happy path: agent creates application record
  - Daily limit enforcement: refuse when at cap
  - Method selection: api/email_fallback/manual_required
  - Missing materials: no resume available
  - Missing job: nonexistent job_id

### References

- [Source: backend/app/agents/pro/cover_letter_agent.py] — Agent pattern reference
- [Source: backend/app/agents/base.py] — BaseAgent, AgentOutput
- [Source: backend/app/db/models.py] — Application model, ApplicationStatus enum
- [Source: backend/app/worker/tasks.py] — agent_apply placeholder task
- [Source: backend/app/agents/orchestrator.py] — dispatch_task, get_user_context

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
SIMPLE (score: 1/16, overridden to SIMPLE by user flag)

### Debug Log References
- No issues encountered. All 13 tests passed on first run.

### Completion Notes List
- Created ApplyAgent extending BaseAgent with agent_type="apply"
- 8-step execute() workflow: validate → context → limit check → load job → method selection → materials → record → output
- Daily limits: free=5, pro=25, h1b_pro=25, career_insurance=50, enterprise=100
- Submission method selection: api (URL present) > email_fallback (email in desc) > manual_required
- Materials preparation loads latest tailored resume and optional cover letter
- Application recorded in applications table with status='applied'
- Wired Celery agent_apply task to import and call ApplyAgent
- 13 tests covering happy path, daily limits, method selection, error cases

### Change Log
- 2026-02-01: Created ApplyAgent + wired Celery task + 13 tests

### File List
**Created:**
- `backend/app/agents/pro/apply_agent.py` — ApplyAgent class
- `backend/tests/unit/test_agents/test_apply_agent.py` — 13 tests

**Modified:**
- `backend/app/worker/tasks.py` — Wired agent_apply to ApplyAgent
