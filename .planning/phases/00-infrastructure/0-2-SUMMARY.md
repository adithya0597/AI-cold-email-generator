# Story 0-2: Row-Level Security Policies Summary

**One-liner:** RLS policies on 8 user-scoped tables using current_setting('app.current_user_id', true)::uuid with dev bypass and transaction-scoped context helper.

## What Was Built

### Migration (00003_row_level_security.sql)
- **ENABLE ROW LEVEL SECURITY** on all 8 user-scoped tables: profiles, applications, matches, documents, agent_actions, agent_outputs, swipe_events, learned_preferences
- **user_isolation_policy** on each table: `FOR ALL USING (user_id = current_setting('app.current_user_id', true)::uuid)`
- **dev_bypass_policy** on each table: requires both `app.environment = 'development'` AND `app.rls_bypass = 'true'`
- Rollback migration drops all 16 policies and disables RLS on all 8 tables

### Backend Helper (rls.py)
- `set_rls_context(session, user_id)` executes `SET LOCAL app.current_user_id` per transaction
- UUID validation via regex + stdlib UUID to prevent SQL injection
- Transaction-scoped (SET LOCAL) -- auto-cleared on commit/rollback

### Tests (85 total)
- Migration file existence and parseability
- RLS enabled verification for all 8 tables
- User isolation policy existence and content (current_setting, FOR ALL)
- Dev bypass policy with dual safeguards
- set_rls_context helper: valid UUID, SQL injection prevention, edge cases
- Rollback completeness: policy drops, RLS disable, ordering
- Policy naming conventions and table exclusion (users, jobs excluded)

## Acceptance Criteria Status

| AC | Description | Status |
|----|-------------|--------|
| AC1 | RLS enabled on all 8 user-scoped tables | Done |
| AC2 | User isolation policy using current_setting | Done |
| AC3 | Development bypass with environment safeguards | Done |
| AC4 | Backend rls.py helper for SET LOCAL | Done |
| AC5 | Rollback migration cleanly removes all | Done |
| AC6 | Tests verify policies and isolation | Done (85 tests) |

## Files Created

| File | Purpose |
|------|---------|
| `supabase/migrations/00003_row_level_security.sql` | Forward migration: enable RLS + 16 policies |
| `supabase/migrations/00003_row_level_security_rollback.sql` | Rollback: drop policies + disable RLS |
| `backend/app/db/rls.py` | Transaction-scoped RLS context setter |
| `backend/tests/unit/test_db/test_rls.py` | 85 unit tests |

## Commits

| Hash | Message |
|------|---------|
| aa6e80a | feat(0-2): add RLS migration and rollback for 8 user-scoped tables |
| c8ec94a | feat(0-2): add RLS context helper for SQLAlchemy sessions |
| a22c299 | test(0-2): add 85 tests for RLS policies, helper, and rollback |

## Decisions Made

- **UUID validation over bind params:** SET LOCAL does not reliably support bind parameters across async PG drivers; validated UUID via regex + stdlib before string formatting
- **No WITH CHECK clause:** Policies use USING only (FOR ALL), which PostgreSQL applies for both read and write operations. WITH CHECK would add redundant validation since user_id must match for both.
- **Tables excluded from RLS:** `users` (queried by clerk_id, not user_id) and `jobs` (shared/public data) -- per architecture requirements

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed import path in tests**
- **Found during:** Task 3 test execution
- **Issue:** Tests used `from backend.app.db.rls import ...` but pytest runs from within `backend/` directory, so the correct path is `from app.db.rls import ...`
- **Fix:** Changed all imports to `from app.db.rls import set_rls_context`
- **Files modified:** `backend/tests/unit/test_db/test_rls.py`

## Duration

~4 minutes
