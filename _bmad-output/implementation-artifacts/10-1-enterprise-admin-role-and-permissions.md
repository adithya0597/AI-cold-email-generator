# Story 10.1: Enterprise Admin Role and Permissions

Status: ready-for-dev

## Story

As an **enterprise administrator**,
I want **a role-based permission system that grants me organization-level management capabilities while enforcing strict data isolation**,
So that **I can manage my organization's workforce deployment without accessing individual employee applications or pipeline data**.

## Acceptance Criteria

1. **AC1: Organization model and membership** — Given the enterprise admin system is deployed, when an organization is created, then an `Organization` record exists with `id`, `name`, `logo_url`, and `settings` (JSONB), and an `OrganizationMember` record links users to organizations with a `role` field (admin/member).
2. **AC2: Admin role dependency** — Given a user has the admin role for their organization, when they call an admin-protected endpoint, then the `require_admin` dependency resolves successfully and injects both the user and organization context.
3. **AC3: Non-admin rejection** — Given a user does NOT have the admin role, when they call an admin-protected endpoint, then the request is rejected with HTTP 403 Forbidden and a clear error message.
4. **AC4: Audit log creation** — Given an admin performs any write action (create, update, delete) through admin endpoints, when the action completes, then an `AuditLog` record is persisted with `org_id`, `actor_id`, `action`, `resource_type`, `resource_id`, `changes` (JSONB), and `created_at`.
5. **AC5: RLS org-scoped data isolation** — Given RLS policies are applied, when an admin queries organization data, then only aggregate org-level data is returned and individual user application/pipeline records are never exposed to the admin.
6. **AC6: Admin cannot see individual data** — Given an admin is authenticated, when they attempt to access individual employee applications, resumes, or pipeline data, then the system returns HTTP 403 with a message indicating admin access is limited to aggregate metrics.
7. **AC7: Existing admin routes migrate to RBAC** — Given the existing `/admin/llm-costs` and `/admin/dlq` endpoints exist without RBAC, when this story is complete, then those endpoints require the `require_admin` dependency.

## Tasks / Subtasks

- [x] Task 1: Create Organization and OrganizationMember models (AC: #1)
  - [x] 1.1 Add `Organization` model to `backend/app/db/models.py` with fields: `id` (UUID, PK), `name` (String, not null), `logo_url` (String, nullable), `settings` (JSONB, default `{}`), plus `TimestampMixin` and `SoftDeleteMixin`
  - [x] 1.2 Add `OrganizationMember` model to `backend/app/db/models.py` with fields: `id` (UUID, PK), `org_id` (FK to Organization), `user_id` (FK to User), `role` (Enum: admin/member, default member), plus `TimestampMixin`
  - [x] 1.3 Add `OrgRole` enum to `backend/app/db/models.py` with values `ADMIN = "admin"`, `MEMBER = "member"`
  - [x] 1.4 Add `org_id` nullable FK field to the `User` model for quick org lookup (denormalized from OrganizationMember for convenience)

- [ ] Task 2: Create AuditLog model (AC: #4)
  - [ ] 2.1 Add `AuditLog` model to `backend/app/db/models.py` with fields: `id` (UUID, PK), `org_id` (FK to Organization), `actor_id` (FK to User), `action` (String, not null — e.g., "invite_employee", "update_autonomy"), `resource_type` (String — e.g., "organization_member", "invitation"), `resource_id` (UUID, nullable), `changes` (JSONB, default `{}`), `created_at` (DateTime, server_default=now)
  - [ ] 2.2 Create `log_audit_event()` async helper function in `backend/app/services/enterprise/audit.py` that accepts session, org_id, actor_id, action, resource_type, resource_id, changes and inserts an AuditLog record

- [x] Task 3: Create database migration (AC: #1, #4, #5)
  - [x] 3.1 Create migration file `supabase/migrations/00002_enterprise_admin.sql` with CREATE TABLE for `organizations`, `organization_members`, `audit_logs`
  - [x] 3.2 Add unique constraint on `organization_members(org_id, user_id)`
  - [x] 3.3 Add RLS policies: `organization_members` scoped by org_id, admin sees all org members, member sees only self; `audit_logs` readable only by org admins
  - [x] 3.4 Add RLS policy preventing admin from accessing `user_applications`, `user_pipelines`, or similar individual-level tables via org membership

- [ ] Task 4: Create require_admin dependency (AC: #2, #3)
  - [ ] 4.1 Create `backend/app/auth/admin.py` with `require_admin` FastAPI dependency
  - [ ] 4.2 `require_admin` calls `get_current_user_id()` to get user, then queries `OrganizationMember` for user where `role = "admin"`
  - [ ] 4.3 Return a dataclass/NamedTuple `AdminContext(user_id, org_id, org_name)` on success
  - [ ] 4.4 Raise `HTTPException(403)` if user is not an admin of any organization
  - [ ] 4.5 Set RLS variable `SET LOCAL app.current_org_id` alongside existing `app.current_user_id`

- [ ] Task 5: Migrate existing admin routes to RBAC (AC: #7)
  - [ ] 5.1 Update `backend/app/api/v1/admin.py` — add `require_admin` dependency to `/llm-costs` endpoint
  - [ ] 5.2 Update `backend/app/api/v1/admin.py` — add `require_admin` dependency to `/dlq` endpoint
  - [ ] 5.3 Ensure backward compatibility: if no org exists yet, existing endpoints still function for superadmin-type users

- [ ] Task 6: Write tests (AC: #1-#7)
  - [ ] 6.1 Create `backend/tests/unit/test_auth/test_admin.py`
  - [ ] 6.2 Test `require_admin` returns AdminContext for user with admin role
  - [ ] 6.3 Test `require_admin` raises 403 for user with member role
  - [ ] 6.4 Test `require_admin` raises 403 for user with no organization membership
  - [ ] 6.5 Test `log_audit_event()` creates AuditLog record with correct fields
  - [ ] 6.6 Test Organization model creation with settings JSONB
  - [ ] 6.7 Test OrganizationMember unique constraint on (org_id, user_id)
  - [ ] 6.8 Test existing admin endpoints now require admin role

## Dev Notes

### Architecture Compliance

- **Model location**: All new models (`Organization`, `OrganizationMember`, `AuditLog`, `OrgRole` enum) added to `backend/app/db/models.py` — single source of truth for all models
- **Mixin usage**: Organization uses both `TimestampMixin` and `SoftDeleteMixin`; AuditLog uses only `created_at` (immutable records); OrganizationMember uses `TimestampMixin`
- **Auth pattern**: `require_admin` dependency in `backend/app/auth/admin.py` follows the same pattern as `get_current_user_id()` in `backend/app/auth/clerk.py` — FastAPI Depends() injection
- **RLS pattern**: Extend `backend/app/db/rls.py` pattern with `SET LOCAL app.current_org_id` for org-scoped isolation
- **Migration location**: `supabase/migrations/00002_enterprise_admin.sql` follows sequential naming from `00001_initial_schema.sql`
- **Service location**: Audit helper at `backend/app/services/enterprise/audit.py` — new `enterprise/` subdirectory for enterprise-specific services

### Existing Utilities to Use

- `get_current_user_id()` from `app.auth.clerk` — base user authentication
- `SET LOCAL app.current_user_id` from `app.db.rls` — existing RLS variable pattern
- `AsyncSessionLocal` from `app.db.engine` — database session creation
- `TimestampMixin`, `SoftDeleteMixin` from `app.db.models` — model mixins

### Project Structure Notes

- Auth dependency: `backend/app/auth/admin.py`
- Audit service: `backend/app/services/enterprise/audit.py`
- Migration: `supabase/migrations/00002_enterprise_admin.sql`
- Test file: `backend/tests/unit/test_auth/test_admin.py`

### References

- [Source: backend/app/db/models.py — User model with tier enum, TimestampMixin, SoftDeleteMixin]
- [Source: backend/app/auth/clerk.py — get_current_user_id() Clerk JWT dependency pattern]
- [Source: backend/app/db/rls.py — SET LOCAL app.current_user_id RLS pattern]
- [Source: backend/app/api/v1/admin.py — existing admin routes (llm-costs, dlq) without RBAC]
- [Source: supabase/migrations/00001_initial_schema.sql — migration naming pattern]

## Dev Agent Record

### Agent Model Used

*(to be filled by dev agent)*

### Route Taken

*(to be filled by dev agent)*

### GSD Subagents Used

*(to be filled by dev agent)*

### Debug Log References

*(to be filled by dev agent)*

### Completion Notes List

*(to be filled by dev agent)*

### Change Log

*(to be filled by dev agent)*

### File List

#### Files to CREATE
- `backend/app/auth/admin.py`
- `backend/app/services/enterprise/__init__.py`
- `backend/app/services/enterprise/audit.py`
- `supabase/migrations/00002_enterprise_admin.sql`
- `backend/tests/unit/test_auth/__init__.py`
- `backend/tests/unit/test_auth/test_admin.py`

#### Files to MODIFY
- `backend/app/db/models.py`
- `backend/app/api/v1/admin.py`
- `backend/app/db/rls.py`
