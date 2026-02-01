# Story 5.8: Approval Queue for Applications

Status: review

## Story

As a **user**,
I want **to review and approve applications before they're sent**,
so that **I maintain control over what goes out in my name**.

## Acceptance Criteria

1. **AC1 - List Pending Approvals:** Given I am authenticated, when I call `GET /api/v1/applications/queue`, then I see a list of pending approval items with job title, company, submission method, and material references.

2. **AC2 - Approve Application:** Given a pending approval item, when I call `POST /api/v1/applications/queue/{item_id}/approve`, then the item status changes to 'approved' and the ApplyAgent is dispatched to submit.

3. **AC3 - Reject Application:** Given a pending approval item, when I call `POST /api/v1/applications/queue/{item_id}/reject`, then the item status changes to 'rejected' and no submission occurs.

4. **AC4 - Batch Approve:** Given multiple pending items, when I call `POST /api/v1/applications/queue/batch-approve` with a list of item IDs, then all specified items are approved.

5. **AC5 - Queue Count:** Given I am authenticated, when I call `GET /api/v1/applications/queue/count`, then I receive the number of pending items for navigation badges.

6. **AC6 - Tests:** Given the approval queue endpoints exist, when unit tests run, then coverage exists for list, approve, reject, batch approve, count, and authorization.

## Tasks / Subtasks

- [x] Task 1: Create applications API module (AC: #1, #5)
  - [x]1.1: Create `backend/app/api/v1/applications.py` with router prefix `/applications`
  - [x]1.2: Implement `GET /queue` — list pending approval items for the authenticated user
  - [x]1.3: Implement `GET /queue/count` — return count of pending items

- [x] Task 2: Add approve/reject endpoints (AC: #2, #3, #4)
  - [x]2.1: Implement `POST /queue/{item_id}/approve` — update status to 'approved', dispatch apply task
  - [x]2.2: Implement `POST /queue/{item_id}/reject` — update status to 'rejected' with optional reason
  - [x]2.3: Implement `POST /queue/batch-approve` — approve multiple items at once

- [x] Task 3: Register router (AC: all)
  - [x]3.1: Add applications router to `backend/app/api/v1/router.py`

- [x] Task 4: Write tests (AC: #6)
  - [x]4.1: Create `backend/tests/unit/test_api/test_applications.py`
  - [x]4.2: Test list queue — returns pending items
  - [x]4.3: Test approve — changes status, dispatches task
  - [x]4.4: Test reject — changes status
  - [x]4.5: Test batch approve — approves multiple
  - [x]4.6: Test count — returns correct number
  - [x]4.7: Test not found — 404 for invalid item_id

## Dev Notes

### Architecture Compliance

**CRITICAL — Follow these patterns EXACTLY:**

1. **Use the existing ApprovalQueueItem model** from `backend/app/db/models.py` lines 435-461. Columns: id, user_id, agent_type, action_name, payload (JSONB), status (Text: pending/approved/rejected/expired/paused), rationale, confidence, user_decision_reason, decided_at, expires_at.

2. **Follow the existing API patterns.** Use `Depends(get_current_user_id)` for auth, `AsyncSessionLocal` with lazy imports, raw SQL via `text()`. Follow the documents.py endpoint pattern.

3. **On approve, dispatch via Celery.** Call `dispatch_task("apply", user_id, payload)` from the orchestrator to trigger the ApplyAgent. The payload comes from the approval queue item.

4. **Batch approve is a loop**, not a complex query. For each item_id, update status and dispatch. Keep it simple.

5. **The `GET /queue` endpoint joins with jobs table** to get job title and company for display.

6. **DO NOT modify the ApprovalQueueItem model.** It already has everything needed.

### Previous Story Intelligence (5-7)

- 13 tests passing for ApplyAgent
- ApplyAgent wired to Celery task
- Application model has: id, user_id, job_id, status, applied_at, resume_version_id

### Library/Framework Requirements

**No new dependencies needed.**

### File Structure Requirements

**Files to CREATE:**
```
backend/app/api/v1/applications.py              # Applications API endpoints
backend/tests/unit/test_api/test_applications.py # Endpoint tests
```

**Files to MODIFY:**
```
backend/app/api/v1/router.py    # Register applications router
```

**Files to NOT TOUCH:**
```
backend/app/db/models.py                # ApprovalQueueItem already exists
backend/app/agents/base.py              # _queue_for_approval already exists
backend/app/agents/pro/apply_agent.py   # No changes needed
```

### Testing Requirements

- **Backend Framework:** Pytest + pytest-asyncio
- **Mocking:** Mock `AsyncSessionLocal`, mock `dispatch_task`
- **Tests to write:**
  - List queue with pending items
  - Approve single item (status changes, dispatch called)
  - Reject single item (status changes)
  - Batch approve multiple items
  - Count returns correct number
  - Item not found → 404

### References

- [Source: backend/app/db/models.py] — ApprovalQueueItem model
- [Source: backend/app/agents/base.py] — _queue_for_approval method
- [Source: backend/app/agents/orchestrator.py] — dispatch_task function
- [Source: backend/app/api/v1/documents.py] — API endpoint patterns

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
SIMPLE (score: 1/16, overridden to SIMPLE by user flag)

### Debug Log References
- No issues encountered. All 10 tests passed on first run.

### Completion Notes List
- Created applications.py with 5 endpoints: list queue, count, approve, reject, batch approve
- Uses existing ApprovalQueueItem model — no schema changes
- Approve dispatches apply task via orchestrator.dispatch_task()
- Reject records user_decision_reason and decided_at
- Batch approve iterates and calls approve_item per item
- 409 Conflict for already-decided items
- Registered router in router.py
- 10 tests covering all ACs

### Change Log
- 2026-02-01: Created applications API + registered router + 10 tests

### File List
**Created:**
- `backend/app/api/v1/applications.py` — 5 endpoints
- `backend/tests/unit/test_api/test_applications.py` — 10 tests

**Modified:**
- `backend/app/api/v1/router.py` — Registered applications router
