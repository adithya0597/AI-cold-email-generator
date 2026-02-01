# Story 5.10: Application Submission Confirmation

Status: review

## Story

As a **user**,
I want **confirmation when my application is successfully submitted**,
so that **I know the agent completed its task**.

## Acceptance Criteria

1. **AC1 - Success Notification Activity:** Given the ApplyAgent submits successfully, when the result is recorded, then an agent_activity record is created with event_type='agent.apply.completed', severity='info', and data containing job title, company, submission method, and material IDs.

2. **AC2 - Application Details in Activity:** Given a successful submission, when I view the activity feed, then I can see: job title, company, timestamp, materials sent (resume version, cover letter), and submission method used.

3. **AC3 - Tests:** Given the notification logic exists, when unit tests run, then coverage exists for activity creation on success and activity data structure.

## Tasks / Subtasks

- [x] Task 1: Add success notification to ApplyAgent (AC: #1, #2)
  - [x]1.1: After successful `_record_application()`, create an agent_activity record via `_record_activity()` in base class or direct SQL insert
  - [x]1.2: Include job title, company, method, material IDs in activity data

- [x] Task 2: Write tests (AC: #3)
  - [x]2.1: Add test to `test_apply_agent.py` verifying activity is recorded on success
  - [x]2.2: Test activity data structure includes required fields

## Dev Notes

### Architecture Compliance

1. **Use BaseAgent._record_activity()** pattern from base.py if accessible, or insert directly into agent_activities table following the existing pattern.

2. **The activity feed endpoint already exists** at `GET /agents/activity`. No new endpoints needed.

3. **This is a minimal enhancement** to the ApplyAgent — add an activity record after successful application recording.

### File Structure Requirements

**Files to CREATE:**
```
(none)
```

**Files to MODIFY:**
```
backend/app/agents/pro/apply_agent.py           # Add activity recording after success
backend/tests/unit/test_agents/test_apply_agent.py  # Add notification tests
```

**Files to NOT TOUCH:**
```
backend/app/api/v1/agents.py    # Activity feed endpoint already exists
```
