# Story 10.3: Employee Invitation Flow

Status: done

## Story

As an **enterprise administrator**,
I want **to send branded invitation emails to employees with accept/decline functionality**,
So that **employees receive a professional onboarding experience and I can track who has joined the organization**.

## Acceptance Criteria

1. **AC1: Invitation record creation** — Given an admin invites an employee, when the invitation is created, then an `Invitation` record is persisted with `id` (UUID), `org_id`, `email`, `token` (UUID), `status` (pending), `invited_by` (admin user_id), `first_name`, `last_name`, `created_at`, and `expires_at` (7 days from creation).
2. **AC2: Branded invitation email** — Given an invitation is created, when the email is sent, then the recipient receives an email containing: company logo, admin name, company name, benefit explanation text, and prominent Accept/Decline buttons linking to the appropriate endpoints.
3. **AC3: Accept invitation flow** — Given a valid pending invitation token, when the recipient clicks Accept, then: (a) if they have no account, they are redirected to signup with org context pre-filled; (b) if they have an existing account, their `OrganizationMember` record is created with `role=member`, their tier is upgraded to ENTERPRISE, and the invitation status becomes "accepted".
4. **AC4: Decline invitation flow** — Given a valid pending invitation token, when the recipient clicks Decline, then the invitation status is updated to "declined" and the admin can see "declined" status in the employee list.
5. **AC5: Token expiry** — Given an invitation token is older than 7 days, when the recipient attempts to accept or decline, then the request returns HTTP 410 Gone with message "Invitation has expired" and the invitation status is updated to "expired".
6. **AC6: Duplicate invitation prevention** — Given an invitation already exists for an email in the same org with status "pending", when the admin sends another invitation to the same email, then the old invitation is revoked (status="revoked") and a new invitation is created.
7. **AC7: Audit logging** — Given any invitation action occurs (create, accept, decline, expire, revoke), when the action completes, then an audit log entry is created with the appropriate action and details.

## Tasks / Subtasks

- [x] Task 1: Create Invitation model (AC: #1)
  - [x] 1.1 Add `InvitationStatus` enum to `backend/app/db/models.py` with values: `PENDING = "pending"`, `ACCEPTED = "accepted"`, `DECLINED = "declined"`, `EXPIRED = "expired"`, `REVOKED = "revoked"`
  - [x] 1.2 Add `Invitation` model to `backend/app/db/models.py` with fields: `id` (UUID, PK), `org_id` (FK to Organization), `email` (String, not null), `token` (UUID, unique, default uuid4), `status` (InvitationStatus, default pending), `invited_by` (FK to User), `first_name` (String, nullable), `last_name` (String, nullable), `created_at` (DateTime, server_default=now), `expires_at` (DateTime, default now+7days)
  - [x] 1.3 Add index on `Invitation.token` for fast lookup
  - [x] 1.4 Add composite index on `Invitation(org_id, email, status)` for duplicate detection

- [x] Task 2: Create database migration (AC: #1)
  - [x] 2.1 Create migration file `supabase/migrations/00003_invitations.sql` with CREATE TABLE for `invitations`
  - [x] 2.2 Add RLS policy: invitations readable by org admins, writable by org admins, accept/decline via token (public with token validation)

- [x] Task 3: Create InvitationService (AC: #1, #3, #4, #5, #6, #7)
  - [x] 3.1 Create `backend/app/services/enterprise/invitation.py` with `InvitationService` class
  - [x] 3.2 Implement `create_invitation(session, org_id, email, invited_by, first_name=None, last_name=None) -> Invitation` — revoke existing pending invitations for same email+org, create new invitation, return it
  - [x] 3.3 Implement `accept_invitation(session, token: UUID) -> Invitation` — validate token exists, check not expired, check status is pending, create OrganizationMember record, update user tier to ENTERPRISE, set status to accepted
  - [x] 3.4 Implement `decline_invitation(session, token: UUID) -> Invitation` — validate token, check not expired, set status to declined
  - [x] 3.5 Implement `get_invitation_by_token(session, token: UUID) -> Invitation | None` — fetch invitation with org data for email template
  - [x] 3.6 Implement `_check_expiry(invitation: Invitation) -> bool` — return True if expired, auto-update status to "expired" if past expires_at
  - [x] 3.7 Call `log_audit_event()` in each mutation method

- [x] Task 4: Create invitation email template (AC: #2)
  - [x] 4.1 Add `send_invitation_email()` function to `backend/app/services/transactional_email.py` following existing template pattern
  - [x] 4.2 Email includes: company logo (from Organization.logo_url), admin display name, company name, benefit explanation paragraph, Accept button (links to `/invitations/{token}/accept`), Decline link (links to `/invitations/{token}/decline`)
  - [x] 4.3 Use Resend API client consistent with existing email sending pattern

- [x] Task 5: Create API endpoints (AC: #1, #2, #3, #4, #5, #6)
  - [x] 5.1 Add `POST /api/v1/admin/employees/invite` to `backend/app/api/v1/admin.py` — requires `require_admin`, accepts `InviteRequest(email, first_name?, last_name?)`, creates invitation, sends email, returns invitation summary
  - [x] 5.2 Create `backend/app/api/v1/invitations.py` with public invitation endpoints (no admin auth required, token-based)
  - [x] 5.3 Add `POST /api/v1/invitations/{token}/accept` — validates token, processes acceptance, returns success message with redirect info
  - [x] 5.4 Add `POST /api/v1/invitations/{token}/decline` — validates token, processes decline, returns confirmation
  - [x] 5.5 Register invitation routes in `backend/app/api/v1/router.py`

- [x] Task 6: Create request/response schemas (AC: #1, #2)
  - [x] 6.1 Create `InviteRequest` Pydantic model: `email` (EmailStr), `first_name` (str, optional), `last_name` (str, optional)
  - [x] 6.2 Create `InvitationResponse` Pydantic model: `id`, `email`, `status`, `created_at`, `expires_at`
  - [x] 6.3 Create `InvitationActionResponse` Pydantic model: `message`, `status`, `redirect_url` (optional)

- [x] Task 7: Write tests (AC: #1-#7)
  - [x] 7.1 Create `backend/tests/unit/test_services/test_invitation.py`
  - [x] 7.2 Test invitation creation stores correct fields and generates UUID token
  - [x] 7.3 Test duplicate invitation revokes old pending invitation
  - [x] 7.4 Test accept_invitation creates OrganizationMember and sets tier to ENTERPRISE
  - [x] 7.5 Test accept_invitation with expired token returns 410
  - [x] 7.6 Test accept_invitation with already-accepted token returns error
  - [x] 7.7 Test decline_invitation sets status to declined
  - [x] 7.8 Test decline_invitation with expired token returns 410
  - [x] 7.9 Test send_invitation_email called with correct template data
  - [x] 7.10 Test audit log created for each invitation action
  - [x] 7.11 Test API endpoint requires admin auth for invite
  - [x] 7.12 Test API accept/decline endpoints are publicly accessible (token-based auth)

## Dev Notes

### Architecture Compliance

- **Model location**: `Invitation` model and `InvitationStatus` enum added to `backend/app/db/models.py`
- **Service location**: `backend/app/services/enterprise/invitation.py` — enterprise services directory
- **Email pattern**: `send_invitation_email()` added to existing `backend/app/services/transactional_email.py` following the established Resend template pattern
- **API pattern**: Admin-protected invite endpoint in `backend/app/api/v1/admin.py`; public accept/decline endpoints in new `backend/app/api/v1/invitations.py` (token-based auth, no Clerk JWT required)
- **Token security**: UUID v4 tokens are sufficiently random for invitation links (122 bits of entropy). Tokens are single-use (status changes on accept/decline).
- **Migration location**: `supabase/migrations/00003_invitations.sql`
- **Dependency on 10-1**: Requires `Organization`, `OrganizationMember`, `require_admin`, `log_audit_event()` from story 10-1

### Existing Utilities to Use

- `require_admin` from `app.auth.admin` (story 10-1) — admin authentication for invite endpoint
- `log_audit_event()` from `app.services.enterprise.audit` (story 10-1) — audit trail
- `send_email()` pattern from `app.services.transactional_email` — Resend email sending
- `AsyncSessionLocal` from `app.db.engine` — database session
- `TimestampMixin` from `app.db.models` — model timestamps

### Project Structure Notes

- Model: added to `backend/app/db/models.py`
- Service: `backend/app/services/enterprise/invitation.py`
- Email: added to `backend/app/services/transactional_email.py`
- Admin endpoint: added to `backend/app/api/v1/admin.py`
- Public endpoints: `backend/app/api/v1/invitations.py`
- Migration: `supabase/migrations/00003_invitations.sql`
- Test file: `backend/tests/unit/test_services/test_invitation.py`

### References

- [Source: backend/app/db/models.py — User model with tier enum, model patterns]
- [Source: backend/app/services/transactional_email.py — Resend email template pattern]
- [Source: backend/app/api/v1/admin.py — admin route pattern]
- [Source: backend/app/api/v1/router.py — route registration pattern]
- [Source: backend/app/auth/clerk.py — authentication dependency pattern]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Route Taken

Sequential task execution: model -> migration -> service -> email -> API + schemas -> tests. All 7 tasks completed in single pass with test fixes for mock session behavior.

### GSD Subagents Used

None (single agent execution)

### Debug Log References

- Test attempt 1: 3 failures due to mock session not populating `invitation.id` for `log_audit_event(resource_id=str(invitation.id))` -- UUID("None") error
- Test attempt 2: 2 failures -- `status` and `token` Column defaults not applied by mock session
- Test attempt 3: 1 failure -- `token` Column default not applied
- Test attempt 4: 24/24 passed

### Completion Notes List

- Explicitly set `status=InvitationStatus.PENDING` in `create_invitation()` instead of relying on Column default (needed for unit tests with mock sessions, also more explicit)
- Email normalization: `email.lower().strip()` applied consistently
- Accept flow handles no-account case by returning redirect_url to signup with invitation context
- Invitation email send is fire-and-forget (logged warning on failure, invitation still created)

### Change Log

- `backend/app/db/models.py`: Added `InvitationStatus` enum and `Invitation` model
- `supabase/migrations/00003_invitations.sql`: Created invitations table with RLS
- `backend/app/services/enterprise/invitation.py`: Created `InvitationService` class
- `backend/app/services/transactional_email.py`: Added invitation template and `send_invitation_email()`
- `backend/app/api/v1/admin.py`: Added `InviteRequest`, `InvitationResponse`, `POST /admin/employees/invite`
- `backend/app/api/v1/invitations.py`: Created public accept/decline endpoints
- `backend/app/api/v1/router.py`: Registered invitations router
- `backend/tests/unit/test_services/test_invitation.py`: 24 tests covering full lifecycle

### File List

#### Files to CREATE
- `backend/app/services/enterprise/invitation.py`
- `backend/app/api/v1/invitations.py`
- `supabase/migrations/00003_invitations.sql`
- `backend/tests/unit/test_services/test_invitation.py`

#### Files to MODIFY
- `backend/app/db/models.py`
- `backend/app/services/transactional_email.py`
- `backend/app/api/v1/admin.py`
- `backend/app/api/v1/router.py`
