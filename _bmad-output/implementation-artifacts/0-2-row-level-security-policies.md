# Story 0.2: Row-Level Security Policies

Status: ready-for-dev

## Story

As a **user**,
I want **my data protected so only I can access my own records**,
so that **my career information remains private and isolated from other users**.

## Acceptance Criteria

1. **AC1 - RLS Enabled:** Given the Supabase PostgreSQL database, when I examine all user-scoped tables (profiles, applications, matches, documents, agent_actions, agent_outputs), then RLS is enabled on each table via `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`.

2. **AC2 - User Isolation Policy:** Given RLS is enabled, when a user queries any user-scoped table, then only rows where `user_id` matches the authenticated user are returned — enforced via `CREATE POLICY ... USING (user_id = current_setting('app.current_user_id')::uuid)`.

3. **AC3 - Development Bypass:** Given the development environment, when `app.environment = 'development'` AND `app.rls_bypass = 'true'` PostgreSQL settings are set, then a bypass policy allows unrestricted access for development/testing.

4. **AC4 - Service Role Bypass:** Given the backend connects as a service role via SQLAlchemy, when the session sets `app.current_user_id` before queries, then RLS enforces isolation at the database level as defense-in-depth alongside application-layer filtering.

5. **AC5 - Migration Rollback:** Given the RLS migration is applied, when a rollback is executed, then all policies and RLS settings are cleanly removed without affecting table data.

6. **AC6 - Tests Verify Isolation:** Given RLS policies exist, when tests simulate different user contexts, then user A cannot see user B's data, and policy presence is verified for all 6 tables.

## Tasks / Subtasks

- [x] Task 1: Create RLS migration SQL (AC: #1, #2, #3, #5)
  - [x] 1.1: Create `supabase/migrations/00003_row_level_security.sql` with: ALTER TABLE ENABLE ROW LEVEL SECURITY for all 8 user-scoped tables
  - [x] 1.2: Add user isolation policy on each table: `user_id = current_setting('app.current_user_id', true)::uuid`
  - [x] 1.3: Add development bypass policy on each table with environment safeguards
  - [x] 1.4: Create matching rollback file `supabase/migrations/00003_row_level_security_rollback.sql`

- [x] Task 2: Update database session to set user context (AC: #4)
  - [x] 2.1: Create `backend/app/db/rls.py` with a dependency that sets `app.current_user_id` on the database session via `SET LOCAL`
  - [x] 2.2: Ensure the setting is session-scoped (SET LOCAL) so it's automatically cleared on transaction end

- [x] Task 3: Write backend tests for RLS (AC: #6)
  - [x] 3.1: Create `backend/tests/unit/test_db/test_rls.py` with tests verifying: policy existence on all 8 tables, RLS enabled on all 8 tables, user isolation logic, development bypass logic
  - [x] 3.2: Test that rollback migration cleanly removes all policies

## Dev Notes

### Architecture Compliance

**CRITICAL — Follow these patterns EXACTLY:**

1. **SQLAlchemy + RLS Integration:** The backend uses SQLAlchemy `AsyncSession` (NOT Supabase JS client). The backend connects as a **service role** that has full access. RLS provides **defense-in-depth** alongside the application-layer `WHERE user_id = ...` filtering already in place.
   [Source: backend/app/db/session.py — get_db dependency]
   [Source: backend/app/auth/clerk.py — get_current_user_id dependency]

2. **User context via PostgreSQL settings:** Since we don't use Supabase's `auth.uid()` (that's for PostgREST/JS client), use `current_setting('app.current_user_id')::uuid` in policies. The backend sets this per-transaction via `SET LOCAL app.current_user_id = '{user_id}'`.
   [Source: architecture.md — Auth & Security Architecture section]

3. **Migration numbering:** Next migration is `00003` (after `00001_initial_schema.sql` and `00002_swipe_events_learned_preferences.sql`).
   [Source: supabase/migrations/ directory]

4. **Tables requiring RLS (user-scoped):** profiles, applications, matches, documents, agent_actions, agent_outputs. The `users` table itself does NOT get RLS (users query their own record by clerk_id). The `jobs` table does NOT get RLS (jobs are shared/public data). The `swipe_events` and `learned_preferences` tables (from migration 00002) also need RLS since they have `user_id`.
   [Source: supabase/migrations/00001_initial_schema.sql, 00002_swipe_events_learned_preferences.sql]

5. **Soft-delete awareness:** Policies should use `user_id` check only — soft-delete filtering (`deleted_at IS NULL`) is handled at the application layer, not in RLS policies.
   [Source: backend/app/db/models.py — SoftDeleteMixin pattern]

6. **Do NOT modify existing migration files.** Create a NEW migration file (00003).

### Previous Story Intelligence (0-1)

- Story 0-1 created 8 core tables with proper constraints, triggers, indexes
- Migration pattern: forward file + rollback file naming convention
- Tests in `backend/tests/unit/test_db/test_schema.py` verify table structure — there's a known import path issue (`from backend.app.db.models` instead of `from app.db.models`) that pre-exists
- ORM models defined in `backend/app/db/models.py` with mixins (TimestampMixin, SoftDeleteMixin)
- All user-scoped tables have `user_id UUID FK` with CASCADE

### Technical Requirements

**RLS Policy Pattern (per table):**
```sql
-- Enable RLS
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;

-- User isolation: only own data
CREATE POLICY user_isolation_policy ON {table_name}
    FOR ALL
    USING (user_id = current_setting('app.current_user_id', true)::uuid);

-- Development bypass with safeguards
CREATE POLICY dev_bypass_policy ON {table_name}
    FOR ALL
    USING (
        current_setting('app.environment', true) = 'development'
        AND current_setting('app.rls_bypass', true) = 'true'
    );
```

**Backend RLS Context Setter:**
```python
# backend/app/db/rls.py
async def set_rls_context(session: AsyncSession, user_id: str):
    """Set the current user ID for RLS policies via SET LOCAL."""
    await session.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))
```

**Tables needing RLS (8 total):**
1. profiles
2. applications
3. matches
4. documents
5. agent_actions
6. agent_outputs
7. swipe_events
8. learned_preferences

### Library/Framework Requirements

**No new dependencies needed.**
- SQLAlchemy `text()` for raw SQL `SET LOCAL` — already available
- All PostgreSQL RLS features are built-in

### File Structure Requirements

**Files to CREATE:**
```
supabase/migrations/00003_row_level_security.sql
supabase/migrations/00003_row_level_security_rollback.sql
backend/app/db/rls.py
backend/tests/unit/test_db/test_rls.py
```

**Files to MODIFY:**
```
(none — RLS context setting is a new dependency, not wired into existing routes yet)
```

**Files to NOT TOUCH:**
```
supabase/migrations/00001_initial_schema.sql
supabase/migrations/00002_swipe_events_learned_preferences.sql
backend/app/db/session.py
backend/app/db/models.py
backend/app/auth/clerk.py
```

### Testing Requirements

- **Backend Framework:** Pytest
- **Tests to write:**
  - RLS is enabled on all 8 user-scoped tables (query pg_class.relrowsecurity)
  - User isolation policies exist on all 8 tables (query pg_policies)
  - Dev bypass policies exist on all 8 tables
  - Rollback migration removes all policies and disables RLS
  - `set_rls_context` helper correctly issues SET LOCAL statement
  - Verify policy names follow convention: `user_isolation_policy`, `dev_bypass_policy`

## Dev Agent Record

### Agent Model Used

### Route Taken

### GSD Subagents Used

### Debug Log References

### Completion Notes List

### Change Log

### File List
