# PLAN: Story 10-1 — Enterprise Admin Role and Permissions

## Objective
Create role-based permission system with Organization/OrganizationMember/AuditLog models, require_admin FastAPI dependency, RLS org-scoped isolation, and RBAC migration for existing admin routes.

## Acceptance Criteria
- [ ] AC1: Organization + OrganizationMember models with correct fields
- [ ] AC2: require_admin dependency resolves for admin users
- [ ] AC3: require_admin raises 403 for non-admin users
- [ ] AC4: AuditLog records persisted for admin write actions
- [ ] AC5: RLS org-scoped data isolation
- [ ] AC6: Admin cannot see individual application/pipeline data
- [ ] AC7: Existing admin routes migrated to RBAC

---

## RLS Design Decision

**Context variables**: Extend `rls.py` to support `SET LOCAL app.current_org_id` alongside existing `app.current_user_id`.

**Policy design**:
- `organizations`: SELECT/UPDATE for members of that org (via `organization_members` lookup using `app.current_user_id`)
- `organization_members`: SELECT for org members (same org), INSERT/UPDATE/DELETE for org admins only
- `audit_logs`: SELECT for org admins only (scoped by `org_id`)
- **AC6 enforcement**: Existing user-scoped tables (`applications`, `matches`, `user_pipelines`, etc.) already have RLS policies scoped to `app.current_user_id`. The admin dependency sets BOTH `app.current_user_id` (to the admin's own user_id) and `app.current_org_id`. Admin endpoints query org-scoped tables (organizations, organization_members, audit_logs) — they do NOT query individual user tables. This is an architectural boundary, not an RLS bypass. AC6 is satisfied because no admin endpoint exposes individual user data.

**Audit logging**: `log_audit_event()` is called from the `require_admin` dependency as a middleware-style hook for write methods (POST/PUT/DELETE), or explicitly in route handlers. For this story (read-only llm-costs and dlq endpoints), audit logging is wired into the infrastructure but NOT triggered on GET-only endpoints. Future stories (10-2, 10-3, 10-5) will use `log_audit_event()` in their write endpoints.

---

## Task 1: Add OrgRole enum + Organization + OrganizationMember + org_id on User to models.py
- **What**: Add OrgRole enum (ADMIN/MEMBER), Organization model (id UUID PK, name String NOT NULL, logo_url String nullable, settings JSONB default {}, TimestampMixin, SoftDeleteMixin), OrganizationMember model (id UUID PK, org_id FK→Organization, user_id FK→User, role OrgRole default MEMBER, TimestampMixin, UniqueConstraint(org_id, user_id)), org_id nullable FK on User
- **Why**: AC#1
- **Files**: MODIFY `backend/app/db/models.py`
- **Dependencies**: None
- **Verification**: `python -c "from app.db.models import OrgRole, Organization, OrganizationMember"` succeeds
- **Rollback**: Remove added code from models.py

## Task 2: Add AuditLog model + log_audit_event helper
- **What**: AuditLog model (id UUID PK, org_id FK→Organization, actor_id FK→User, action String NOT NULL, resource_type String NOT NULL, resource_id UUID nullable, changes JSONB default {}, created_at DateTime server_default=now). Create `backend/app/services/enterprise/audit.py` with `async def log_audit_event(session, org_id, actor_id, action, resource_type, resource_id=None, changes=None)` that inserts an AuditLog record.
- **Why**: AC#4
- **Files**: MODIFY `backend/app/db/models.py`, CREATE `backend/app/services/enterprise/__init__.py`, CREATE `backend/app/services/enterprise/audit.py`
- **Dependencies**: Task 1 (Organization model for FK)
- **Verification**: `python -c "from app.db.models import AuditLog; from app.services.enterprise.audit import log_audit_event"` succeeds
- **Rollback**: Remove AuditLog from models.py, delete enterprise/ directory

## Task 3: Create migration SQL
- **What**: `supabase/migrations/00002_enterprise_admin.sql` with:
  - CREATE TYPE org_role AS ENUM ('admin', 'member')
  - CREATE TABLE organizations (id, name, logo_url, settings JSONB, created_at, updated_at, deleted_at, deleted_by, deletion_reason)
  - CREATE TABLE organization_members (id, org_id FK, user_id FK, role org_role, created_at, updated_at, UNIQUE(org_id, user_id))
  - CREATE TABLE audit_logs (id, org_id FK, actor_id FK, action TEXT, resource_type TEXT, resource_id UUID, changes JSONB, created_at)
  - ALTER TABLE users ADD COLUMN org_id UUID REFERENCES organizations(id)
  - RLS ENABLE on all 3 new tables
  - RLS policies:
    - organizations: SELECT for members via organization_members join on current_user_id
    - organization_members: SELECT for same-org members, INSERT/UPDATE/DELETE for admins
    - audit_logs: SELECT for org admins only
  - Indexes on org_id FKs
  - updated_at triggers for organizations, organization_members
- **Why**: AC#1, AC#4, AC#5
- **Files**: CREATE `supabase/migrations/00002_enterprise_admin.sql`
- **Dependencies**: Task 1, Task 2 (model definitions inform SQL)
- **Verification**: SQL parses without errors; all tables, constraints, and policies defined
- **Rollback**: CREATE `supabase/migrations/00002_enterprise_admin_rollback.sql` with DROP TABLE statements

## Task 4: Create require_admin dependency + extend RLS
- **What**:
  1. Add `set_org_rls_context(session, org_id)` to `backend/app/db/rls.py` — sets `SET LOCAL app.current_org_id` with same UUID validation pattern
  2. Create `backend/app/auth/admin.py` with:
     - `@dataclass AdminContext: user_id: str, org_id: str, org_name: str`
     - `async def require_admin(user_id=Depends(get_current_user_id))` that:
       a. Queries OrganizationMember WHERE user_id=user_id AND role='admin'
       b. If not found → HTTPException(403, "Admin access required")
       c. Fetches Organization name
       d. Returns AdminContext(user_id, org_id, org_name)
     - Does NOT set RLS context in the dependency itself (route handlers set context as needed)
- **Why**: AC#2, AC#3
- **Files**: CREATE `backend/app/auth/admin.py`, MODIFY `backend/app/db/rls.py`
- **Dependencies**: Task 1 (OrganizationMember model)
- **Verification**: Unit tests for admin/non-admin/no-org cases pass
- **Rollback**: Delete admin.py, revert rls.py changes

## Task 5: Migrate existing admin routes to RBAC
- **What**: Add `admin_ctx: AdminContext = Depends(require_admin)` parameter to both `/llm-costs` and `/dlq` endpoints. These are read-only endpoints so no audit logging needed. Import require_admin and AdminContext from app.auth.admin.
- **Why**: AC#7
- **Files**: MODIFY `backend/app/api/v1/admin.py`
- **Dependencies**: Task 4 (require_admin)
- **Verification**: Endpoints return 403 without admin auth, succeed with admin auth
- **Rollback**: Remove Depends(require_admin) parameter from endpoints

## Task 6: Write comprehensive tests
- **What**: Create test file with these specific test cases:
  - **AC1 tests**: test_organization_model_fields, test_organization_member_model_fields, test_org_role_enum_values, test_organization_member_unique_constraint, test_user_org_id_field
  - **AC2 tests**: test_require_admin_returns_admin_context (mock OrganizationMember query returning admin role → returns AdminContext)
  - **AC3 tests**: test_require_admin_raises_403_for_member_role, test_require_admin_raises_403_for_no_membership
  - **AC4 tests**: test_log_audit_event_creates_record, test_audit_log_model_fields
  - **AC5 tests**: test_set_org_rls_context_sets_variable, test_set_org_rls_context_validates_uuid
  - **AC6 tests**: test_admin_endpoints_do_not_expose_user_applications (verify no endpoint returns individual application/pipeline data)
  - **AC7 tests**: test_llm_costs_requires_admin, test_dlq_requires_admin
- **Why**: AC#1-7
- **Files**: CREATE `backend/tests/unit/test_auth/__init__.py`, CREATE `backend/tests/unit/test_auth/test_admin.py`
- **Dependencies**: All tasks
- **Verification**: `pytest backend/tests/unit/test_auth/test_admin.py -v` — all pass

---

## Dependency Graph / Waves

Wave 1: Task 1 (models) — must come first
Wave 2: Task 2 (audit) + Task 3 (migration) + Task 4 (admin dep) — all depend on Task 1, independent of each other
Wave 3: Task 5 (RBAC migration) + Task 6 (tests) — depend on Tasks 1-4
