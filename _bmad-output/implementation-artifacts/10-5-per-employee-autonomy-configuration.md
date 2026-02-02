# Story 10.5: Per-Employee Autonomy Configuration

Status: done

## Story

As an **enterprise administrator**,
I want **to set organization-wide default autonomy levels and per-employee overrides with ceiling enforcement**,
So that **I can control the degree of AI automation across my workforce while allowing employees flexibility within approved boundaries**.

## Acceptance Criteria

1. **AC1: Organization default autonomy** — Given an admin configures organization autonomy settings, when the config is saved, then the Organization record stores `default_autonomy` (L1/L2/L3) and `max_autonomy` (L1/L2/L3) in the settings JSONB field, and all new employees inherit the default.
2. **AC2: Max autonomy ceiling enforcement** — Given an organization has `max_autonomy = L2`, when an employee attempts to set their personal autonomy to L3, then the system rejects the change with a clear error message indicating L2 is the maximum allowed by their organization.
3. **AC3: Per-employee autonomy override** — Given an admin sets a specific autonomy level for an employee, when the override is saved, then the employee's effective autonomy is the admin-set value, capped at `max_autonomy`.
4. **AC4: Employee autonomy self-service** — Given an employee has no admin override, when they adjust their autonomy level, then the change is allowed if it does not exceed `max_autonomy`. The employee sees their allowed range (L0 through max_autonomy) in the UI.
5. **AC5: Special restrictions** — Given an admin configures restrictions, when restrictions are saved, then the Organization settings JSONB stores `restrictions` object with optional keys: `blocked_companies` (list of company names/domains), `blocked_industries` (list of industries), `require_approval_industries` (list of industries requiring L2-style approval regardless of autonomy level).
6. **AC6: Restriction enforcement in agents** — Given restrictions are configured, when an agent processes a job or company, then it checks against org restrictions: blocked companies/industries are skipped, require_approval industries force approval queue regardless of autonomy level.
7. **AC7: Audit logging** — Given an admin changes autonomy config or restrictions, when the change completes, then an audit log entry is created with action "update_autonomy_config" or "update_restrictions" and the before/after values in changes JSONB.

## Tasks / Subtasks

- [x] Task 1: Add autonomy fields to Organization settings (AC: #1)
  - [x] 1.1 Define the Organization settings JSONB schema to include `default_autonomy` (string: "L1"/"L2"/"L3", default "L1"), `max_autonomy` (string: "L1"/"L2"/"L3", default "L3"), `restrictions` (object, default `{}`)
  - [x] 1.2 Create Pydantic model `OrgAutonomySettings` for validating the settings structure: `default_autonomy`, `max_autonomy`, `restrictions` (OrgRestrictions)
  - [x] 1.3 Create Pydantic model `OrgRestrictions`: `blocked_companies` (list[str], default []), `blocked_industries` (list[str], default []), `require_approval_industries` (list[str], default [])
  - [x] 1.4 Add migration `supabase/migrations/00004_org_autonomy_defaults.sql` to set default values for existing organizations (if any)

- [x] Task 2: Create AutonomyConfigService (AC: #1, #2, #3, #4, #5)
  - [x] 2.1 Create `backend/app/services/enterprise/autonomy_config.py` with `AutonomyConfigService` class
  - [x] 2.2 Implement `get_org_autonomy_config(session, org_id) -> OrgAutonomySettings` — read from Organization.settings JSONB
  - [x] 2.3 Implement `update_org_autonomy_config(session, org_id, config: OrgAutonomySettings) -> OrgAutonomySettings` — validate max >= default, persist to settings JSONB
  - [x] 2.4 Implement `validate_employee_autonomy(session, org_id, requested_level: str) -> bool` — check requested level does not exceed org max_autonomy
  - [x] 2.5 Implement `set_employee_autonomy(session, org_id, user_id, level: str) -> None` — admin override for specific employee, stored on OrganizationMember or user preference, capped at max_autonomy
  - [x] 2.6 Implement `get_effective_autonomy(session, user_id) -> str` — resolve effective autonomy: admin override > org default > user preference, all capped at max_autonomy
  - [x] 2.7 Implement `update_restrictions(session, org_id, restrictions: OrgRestrictions) -> OrgRestrictions` — persist restrictions to Organization.settings JSONB
  - [x] 2.8 Implement `check_restrictions(session, org_id, company: str = None, industry: str = None) -> RestrictionResult` — returns dataclass with `blocked: bool`, `requires_approval: bool`, `reason: str`

- [x] Task 3: Create API endpoints (AC: #1, #2, #3, #5, #7)
  - [x] 3.1 Add `GET /api/v1/admin/autonomy-config` to `backend/app/api/v1/admin.py` — requires `require_admin`, returns current org autonomy config and restrictions
  - [x] 3.2 Add `PUT /api/v1/admin/autonomy-config` to `backend/app/api/v1/admin.py` — requires `require_admin`, accepts `OrgAutonomySettings`, validates, persists, logs audit event
  - [x] 3.3 Add `PUT /api/v1/admin/users/{user_id}/autonomy` to `backend/app/api/v1/admin.py` — requires `require_admin`, accepts `EmployeeAutonomyRequest(level: str)`, validates against max_autonomy, persists override, logs audit event
  - [x] 3.4 Add `GET /api/v1/admin/autonomy-config/restrictions` to `backend/app/api/v1/admin.py` — requires `require_admin`, returns current restrictions
  - [x] 3.5 Add `PUT /api/v1/admin/autonomy-config/restrictions` to `backend/app/api/v1/admin.py` — requires `require_admin`, accepts `OrgRestrictions`, persists, logs audit event

- [x] Task 4: Integrate restriction checking into agent framework (AC: #6)
  - [x] 4.1 Add `check_org_restrictions()` method to tier_enforcer or create utility in `backend/app/agents/org_restrictions.py`
  - [x] 4.2 The method accepts `user_id`, `company`, `industry` and returns restriction result
  - [x] 4.3 If user belongs to an org, fetch org restrictions and evaluate; if no org, return no restrictions
  - [x] 4.4 Document integration point for agents to call before processing jobs (actual agent integration deferred to agent stories)

- [x] Task 5: Create request/response schemas (AC: #1, #3, #5)
  - [x] 5.1 Create `OrgAutonomyConfigResponse` Pydantic model: `default_autonomy`, `max_autonomy`, `restrictions` (OrgRestrictions)
  - [x] 5.2 Create `EmployeeAutonomyRequest` Pydantic model: `level` (str, validated against AutonomyLevel enum values)
  - [x] 5.3 Create `RestrictionResult` dataclass: `blocked` (bool), `requires_approval` (bool), `reason` (str)

- [x] Task 6: Write tests (AC: #1-#7)
  - [x] 6.1 Create `backend/tests/unit/test_services/test_autonomy_config.py`
  - [x] 6.2 Test get_org_autonomy_config returns defaults for new org
  - [x] 6.3 Test update_org_autonomy_config persists values to settings JSONB
  - [x] 6.4 Test update rejects config where default > max (e.g., default=L3, max=L1)
  - [x] 6.5 Test validate_employee_autonomy returns False when requested > max
  - [x] 6.6 Test validate_employee_autonomy returns True when requested <= max
  - [x] 6.7 Test set_employee_autonomy caps at max_autonomy
  - [x] 6.8 Test get_effective_autonomy resolution order: override > org default > user pref
  - [x] 6.9 Test check_restrictions blocks company in blocked_companies list
  - [x] 6.10 Test check_restrictions requires approval for industry in require_approval_industries
  - [x] 6.11 Test check_restrictions returns no restrictions for non-org user
  - [x] 6.12 Test API endpoints require admin auth
  - [x] 6.13 Test audit log created for config and restriction changes

## Dev Notes

### Architecture Compliance

- **Service location**: `backend/app/services/enterprise/autonomy_config.py` — enterprise services directory
- **Settings storage**: Autonomy config and restrictions stored in `Organization.settings` JSONB field — no new columns needed. Use Pydantic models for validation before persisting.
- **Autonomy levels**: Validate against existing `AutonomyLevel` enum values (L0, L1, L2, L3) from `backend/app/agents/tier_enforcer.py`. L0 is always available (read-only). Admin configures default/max from L1-L3.
- **Restriction checking**: Create as standalone utility so agents can call it. Follows the same pattern as `check_brake()` — a quick check before agent execution.
- **API pattern**: Endpoints added to existing `backend/app/api/v1/admin.py` with `require_admin` dependency
- **Migration**: Minimal migration — only sets defaults on existing org records if any exist
- **Dependency on 10-1**: Requires `Organization`, `OrganizationMember`, `require_admin`, `log_audit_event()` from story 10-1

### Existing Utilities to Use

- `require_admin` from `app.auth.admin` (story 10-1) — admin authentication
- `log_audit_event()` from `app.services.enterprise.audit` (story 10-1) — audit trail
- `AutonomyLevel` enum from `app.agents.tier_enforcer` — L0/L1/L2/L3 level definitions
- `check_brake()` from `app.agents.brake` — pattern reference for agent pre-checks
- `AsyncSessionLocal` from `app.db.engine` — database session

### Project Structure Notes

- Service: `backend/app/services/enterprise/autonomy_config.py`
- Restriction utility: `backend/app/agents/org_restrictions.py`
- Endpoints: added to `backend/app/api/v1/admin.py`
- Migration: `supabase/migrations/00004_org_autonomy_defaults.sql`
- Test file: `backend/tests/unit/test_services/test_autonomy_config.py`

### References

- [Source: backend/app/agents/tier_enforcer.py — AutonomyLevel enum (L0-L3), tier enforcement pattern]
- [Source: backend/app/db/models.py — Organization model with settings JSONB (from story 10-1)]
- [Source: backend/app/api/v1/admin.py — admin route pattern]
- [Source: backend/app/agents/brake.py — check_brake() pattern for agent pre-flight checks]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Route Taken

Tasks 1+2+5 combined (models, schemas, service in single file) -> Task 3 (API endpoints) -> Task 4 (org_restrictions utility) -> Task 6 (29 unit tests). Two test failures fixed on retry (mock pattern for settings dict, lazy import patch target).

### GSD Subagents Used

None -- single-agent execution.

### Debug Log References

None.

### Completion Notes List

- All models, service, schemas colocated in `autonomy_config.py` for cohesion
- Restriction matching is case-insensitive for both companies and industries
- Company matching uses substring containment (e.g., "EvilCorp" matches "EvilCorp Inc")
- `set_employee_autonomy` caps silently rather than rejecting (admin override path)
- `validate_employee_autonomy` rejects explicitly (employee self-service path)
- API body schemas defined inline in admin.py to avoid circular imports

### Change Log

- 28cfda8: feat(10-5): add autonomy config models, schemas, and migration
- aaf3464: feat(10-5): add autonomy config API endpoints to admin router
- cf0c789: feat(10-5): add org restriction checker for agent framework
- 51899c6: test(10-5): add 29 unit tests for autonomy config service

### File List

#### Files to CREATE
- `backend/app/services/enterprise/autonomy_config.py`
- `backend/app/agents/org_restrictions.py`
- `supabase/migrations/00004_org_autonomy_defaults.sql`
- `backend/tests/unit/test_services/test_autonomy_config.py`

#### Files to MODIFY
- `backend/app/api/v1/admin.py`
