# Story 9.6: Human Approval for Direct Outreach

Status: done

## Story

As a **user**,
I want **all direct messages to require my approval**,
So that **I maintain control over my professional reputation**.

## Acceptance Criteria

1. **AC1: Approval queue integration** — Given the Network Agent drafts outreach, when the message is ready, then it appears in my approval queue.
2. **AC2: Approval actions** — Given a draft is in the approval queue, when I review it, then I can: Approve, Edit & Approve, or Reject.
3. **AC3: Hard constraint** — Given the Network Agent operates, when any outreach is generated, then the agent NEVER sends messages without approval regardless of autonomy level.
4. **AC4: Approval context** — Given a draft is in the queue, when displayed, then it shows: Recipient, Message preview, Relationship context (temperature, mutual connections, path type).
5. **AC5: Integration with existing approval system** — Given the approval queue exists from Epic 5, when network drafts are added, then they use the same `ApprovalQueueItem` model and workflow.

## Tasks / Subtasks

- [x] Task 1: Create NetworkApprovalService (AC: #1, #2, #3, #4, #5)
  - [x] 1.1 Create `backend/app/services/network/approval.py` with `NetworkApprovalService` class
  - [x] 1.2 Implement `async queue_outreach(user_id: str, draft: dict, context: dict) -> str` that creates an ApprovalQueueItem with agent_type="network", action_name="outreach_request", payload containing message draft and relationship context
  - [x] 1.3 Implement `async get_pending_outreach(user_id: str) -> list[dict]` that fetches pending network approvals
  - [x] 1.4 Implement `async process_approval(item_id: str, action: str, edited_message: str | None) -> dict` that handles approve/edit_approve/reject
  - [x] 1.5 Enforce hard constraint: always set `requires_approval=True` in AgentOutput when outreach drafts exist

- [x] Task 2: Wire approval into NetworkAgent (AC: #1, #3)
  - [x] 2.1 After generating intro drafts, call NetworkApprovalService.queue_outreach() for each draft
  - [x] 2.2 Set `requires_approval=True` on AgentOutput
  - [x] 2.3 Publish `approval.new` WebSocket event via Redis pub/sub

- [x] Task 3: Write tests (AC: #1-#5)
  - [x] 3.1 Create `backend/tests/unit/test_services/test_network_approval.py`
  - [x] 3.2 Test queue_outreach() creates ApprovalQueueItem with correct fields
  - [x] 3.3 Test get_pending_outreach() returns only network-type pending items
  - [x] 3.4 Test process_approval() with approve action
  - [x] 3.5 Test process_approval() with edit_approve action (message updated)
  - [x] 3.6 Test process_approval() with reject action
  - [x] 3.7 Test hard constraint: requires_approval always True for outreach
  - [x] 3.8 Test approval context includes recipient, message preview, relationship data

## Dev Notes

### Architecture Compliance

- **Service location**: `backend/app/services/network/approval.py`
- **Reuse existing ApprovalQueueItem**: The `approval_queue` table and `ApprovalQueueItem` model already exist from Epic 5 (story 5-8). Do NOT create new tables. Use `agent_type="network"` and `action_name="outreach_request"` to distinguish network approvals.
- **Hard constraint enforcement**: This is a safety constraint — all outreach MUST go through approval regardless of autonomy level. Even at L3 (autonomous), network outreach requires human approval.
- **Redis pub/sub for notifications**: Use `get_redis_client()` from `app.cache.redis_client` to publish `approval.new` events.
- **48-hour expiry**: ApprovalQueueItem has default 48-hour expiry. Network drafts use the same default.

### Existing Utilities to Use

- `ApprovalQueueItem` model from `app.db.models`
- `AsyncSessionLocal` from `app.db.session` for DB operations
- `get_redis_client()` from `app.cache.redis_client` for pub/sub
- `_queue_for_approval()` from BaseAgent — consider using this directly instead of custom service

### Project Structure Notes

- Service file: `backend/app/services/network/approval.py`
- Test file: `backend/tests/unit/test_services/test_network_approval.py`
- Modified file: `backend/app/agents/core/network_agent.py` (wire approval after draft generation)

### References

- [Source: backend/app/agents/base.py — _queue_for_approval() method]
- [Source: backend/app/db/models.py — ApprovalQueueItem model]
- [Source: backend/app/agents/core/network_agent.py — wire approval into execute flow]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Debug Log References
N/A

### Completion Notes List
- 8 tests passing for network approval service
- Uses existing ApprovalQueueItem model with agent_type="network"
- queue_outreach() creates approval item and publishes Redis event
- process_approval() handles approve, edit_approve, reject actions
- Hard constraint: requires_approval always True when drafts exist
- Wired into NetworkAgent via _queue_drafts_for_approval()

### File List
- backend/app/services/network/approval.py (created)
- backend/tests/unit/test_services/test_network_approval.py (created)
- backend/app/agents/core/network_agent.py (modified)
