# Story 10.6: At-Risk Employee Alerts

Status: done

## Story

As an **enterprise admin**,
I want **to see which employees are at risk of disengaging and send them re-engagement nudges**,
So that **I can proactively support employees through their career transition without violating their privacy**.

## Acceptance Criteria

1. **AC1: At-risk detection criteria** — Given the AtRiskDetectionService runs, when it evaluates employees, then it flags users as at-risk based on: (a) not logged in for 14+ days, (b) no applications submitted in 30+ days, (c) stalled pipeline (no status changes in 21+ days). Users matching any criterion are marked at-risk.

2. **AC2: Privacy-safe at-risk listing** — Given an admin requests the at-risk employee list, when the API returns results, then each record contains ONLY user_id, name, email, and engagement_status (at_risk, active, placed, opted_out). The response NEVER includes application titles, pipeline details, job matches, or any individual activity data.

3. **AC3: Employee status filtering** — Given the at-risk endpoint is called, when a status filter query parameter is provided, then results are filtered to show only employees matching the specified status: at_risk, active, placed, or opted_out.

4. **AC4: Re-engagement nudge sending** — Given an admin triggers a nudge for an at-risk employee, when the nudge endpoint is called, then a generic re-engagement email is sent via Resend using the transactional email pattern. The email content is NOT personalized with any pipeline or application data.

5. **AC5: Daily automated detection** — Given the Celery beat schedule includes the at-risk detection task, when the task runs daily, then it evaluates all employees in the organization and updates their engagement_status accordingly.

6. **AC6: Audit trail for nudges** — Given an admin sends a nudge, when the action completes, then an AuditLog entry is created recording the admin user_id, target employee user_id, action type "nudge_sent", and timestamp.

7. **AC7: RBAC enforcement** — Given a non-admin user calls the at-risk endpoints, when the request is processed, then it returns 403 Forbidden.

## Tasks / Subtasks

- [x] Task 1: Create AtRiskDetectionService (AC: #1, #2, #5)
  - [x] 1.1 Create `backend/app/services/enterprise/at_risk.py` with `AtRiskDetectionService` class
  - [x] 1.2 Implement `detect_at_risk(org_id: str)` — query users by last_login (14+ days ago), application count (0 in 30 days), pipeline activity (no status changes in 21 days)
  - [x] 1.3 Implement `get_employee_summaries(org_id: str, status_filter: Optional[str])` — return list of dicts with ONLY user_id, name, email, engagement_status
  - [x] 1.4 Implement `update_engagement_statuses(org_id: str)` — batch update engagement_status field on OrganizationMember records
  - [x] 1.5 Create `backend/app/services/enterprise/__init__.py` if it does not exist

- [x] Task 2: Create API endpoints (AC: #2, #3, #4, #6, #7)
  - [x] 2.1 Create `backend/app/api/v1/admin_enterprise.py` with router prefix `/admin`
  - [x] 2.2 Implement `GET /api/v1/admin/employees/at-risk` — accepts `status` query param (at_risk, active, placed, opted_out), returns privacy-safe employee list with pagination
  - [x] 2.3 Implement `POST /api/v1/admin/employees/{user_id}/nudge` — sends generic re-engagement email, creates AuditLog entry
  - [x] 2.4 Add RBAC dependency that checks current user has admin role in their organization
  - [x] 2.5 Register routes in `backend/app/api/v1/router.py`

- [x] Task 3: Create Celery task for daily detection (AC: #5)
  - [x] 3.1 Add `detect_at_risk_employees` task to `backend/app/worker/tasks.py` on the `"default"` queue
  - [x] 3.2 Follow established pattern: lazy imports, `_run_async()` wrapper, Langfuse trace
  - [x] 3.3 Task iterates all organizations and calls `AtRiskDetectionService.update_engagement_statuses(org_id)`

- [x] Task 4: Create nudge email template (AC: #4)
  - [x] 4.1 Create generic re-engagement email template following `transactional_email.py` pattern
  - [x] 4.2 Email content must be generic: "Your career transition tools are ready when you are" — no personalized data

- [x] Task 5: Write tests (AC: #1-#7)
  - [x] 5.1 Create `backend/tests/unit/test_services/test_at_risk.py`
  - [x] 5.2 Test detection criteria: user not logged in 14+ days is flagged at-risk
  - [x] 5.3 Test detection criteria: user with no applications in 30+ days is flagged at-risk
  - [x] 5.4 Test detection criteria: user with stalled pipeline (21+ days) is flagged at-risk
  - [x] 5.5 Test detection criteria: active user is NOT flagged at-risk
  - [x] 5.6 Test privacy enforcement: API response contains ONLY user_id, name, email, engagement_status — no application titles, pipeline details, or job matches
  - [x] 5.7 Test status filtering returns only matching employees
  - [x] 5.8 Test nudge sends generic email via Resend (mock)
  - [x] 5.9 Test nudge creates AuditLog entry
  - [x] 5.10 Test non-admin user receives 403 Forbidden
  - [x] 5.11 Test Celery task follows standard pattern

## Dev Notes

### Architecture Compliance

- **Service location**: `backend/app/services/enterprise/at_risk.py` — enterprise services in `enterprise/` subdirectory
- **API location**: `backend/app/api/v1/admin_enterprise.py` — enterprise admin routes separated from existing `admin.py`
- **Celery task pattern**: Follow established pattern in `tasks.py` — `@celery_app.task(bind=True, ...)`, lazy imports inside `async def _execute()`, `_run_async()` wrapper, Langfuse trace
- **CRITICAL privacy constraint**: Admin sees user_id, name, email, engagement_status ONLY. Never application titles, pipeline details, job matches, or any individual activity data. This must be enforced at the service layer, not just the API layer.
- **Email pattern**: Use Resend via `transactional_email.py` pattern. Nudge emails are generic — no personalized content from user's pipeline or applications.
- **Audit logging**: Use AuditLog model (created by story 10-3) with action_type="nudge_sent"
- **RBAC**: Enterprise admin check via Organization membership with admin role

### Existing Utilities to Use

- `get_current_user_id()` from `app/auth/clerk.py` — JWT authentication
- `transactional_email.py` — Resend email sending pattern
- `_run_async()` from `app/worker/tasks.py` — Celery async wrapper
- `create_agent_trace()`, `flush_traces()` from `app/observability/langfuse_client` — observability
- `TimestampMixin`, `SoftDeleteMixin` from `app/db/models.py` — model mixins
- `AuditLog` model from story 10-3 — audit trail recording

### Project Structure Notes

- Service file: `backend/app/services/enterprise/at_risk.py`
- API file: `backend/app/api/v1/admin_enterprise.py`
- Test file: `backend/tests/unit/test_services/test_at_risk.py`
- Celery task: added to existing `backend/app/worker/tasks.py`

### References

- [Source: backend/app/services/transactional_email.py — Email sending pattern with Resend]
- [Source: backend/app/worker/tasks.py — Celery task pattern with lazy imports and Langfuse]
- [Source: backend/app/auth/clerk.py — get_current_user_id() authentication dependency]
- [Source: backend/app/api/v1/admin.py — Existing admin routes (no RBAC yet)]
- [Source: backend/app/db/models.py — User model with tier enum, AgentActivity model]
- [Dependency: Story 10-1 — Organization, OrganizationMember models]
- [Dependency: Story 10-3 — AuditLog model]

## Dev Agent Record

### Agent Model Used

(to be filled by dev agent)

### Route Taken

(to be filled by dev agent)

### GSD Subagents Used

(to be filled by dev agent)

### Debug Log References

(to be filled by dev agent)

### Completion Notes List

(to be filled by dev agent)

### Change Log

(to be filled by dev agent)

### File List

#### Files to CREATE
- `backend/app/services/enterprise/__init__.py`
- `backend/app/services/enterprise/at_risk.py`
- `backend/app/api/v1/admin_enterprise.py`
- `backend/tests/unit/test_services/test_at_risk.py`

#### Files to MODIFY
- `backend/app/worker/tasks.py`
- `backend/app/api/v1/router.py`
