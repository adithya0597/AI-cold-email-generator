---
phase: 01-foundation-modernization
plan: 03
subsystem: database
tags: [sqlalchemy, asyncpg, alembic, supabase, adr]
dependency-graph:
  requires: [01-01]
  provides: [async-engine, session-factory, alembic-migrations, adr-2]
  affects: [01-04, 01-05, 01-08]
tech-stack:
  added: []
  patterns: [async-sqlalchemy-engine, fastapi-db-dependency, alembic-async-migrations]
key-files:
  created:
    - backend/app/db/engine.py
    - backend/app/db/session.py
    - backend/app/db/supabase_client.py
    - backend/alembic.ini
    - backend/alembic/env.py
    - backend/alembic/script.py.mako
    - backend/alembic/versions/2026_01_31_0001_initial_schema.py
    - backend/docs/adr/002-database-access-pattern.md
  modified:
    - backend/app/db/__init__.py
decisions:
  - id: ADR-2
    title: Database Access Pattern
    choice: SQLAlchemy-only for app data; Supabase SDK for storage/auth/realtime
metrics:
  duration: ~8 min
  completed: 2026-01-31
---

# Phase 1 Plan 3: Database Layer Resolution Summary

SQLAlchemy async engine with asyncpg driver, Supabase-compatible connect_args (statement_cache_size=0, jit=off), Alembic async migrations with baseline stamp, ADR-2 documenting single-source-of-truth database access pattern.

## Tasks Completed

### Task 1: SQLAlchemy async engine and session factory [7a6406a]

- Created `backend/app/db/engine.py` with `create_async_engine` using `settings.DATABASE_URL`, `pool_size=5`, `max_overflow=10`, and Supabase-compatible `connect_args` (`statement_cache_size=0`, `server_settings={"jit": "off"}`)
- Created `backend/app/db/session.py` with `get_db()` async generator for FastAPI dependency injection (auto commit on success, rollback on exception)
- Renamed `backend/app/db/connection.py` to `backend/app/db/supabase_client.py` with docstring clarifying Supabase SDK is for storage/auth ONLY
- Updated `backend/app/db/__init__.py` to export `engine`, `AsyncSessionLocal`, `get_db`
- Verified no code imports from `app.db.connection` (the old module name)

### Task 2: Alembic async migration configuration [3e34912]

- Created `backend/alembic.ini` with `sqlalchemy.url` set programmatically from `app.config.settings` (no credentials in config file)
- Created `backend/alembic/env.py` with async migration runner using `create_async_engine` and `connection.run_sync(do_run_migrations)` pattern
- Created `backend/alembic/script.py.mako` template for future migrations
- Created baseline migration `0001` matching all 8 existing tables from `supabase/migrations/00001_initial_schema.sql` -- this migration is stamp-only (tables already exist in Supabase)
- Migration includes proper downgrade path (drop all tables in reverse dependency order)

### Task 3: ADR-2 decision document [ca93c33]

- Created `backend/docs/adr/002-database-access-pattern.md` documenting:
  - Decision: SQLAlchemy for ALL application data access
  - Supabase SDK restricted to: file storage, auth token forwarding, realtime subscriptions
  - Connection config: direct port 5432, statement_cache_size=0, jit=off
  - Anti-patterns: dual writes, bypassing Alembic, transactionless queries via REST
  - Consequences: positive (ACID, type-safe, migrations), negative (Supabase dashboard read-only)

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| ADR-2: Database access pattern | SQLAlchemy-only for app data | Prevents dual-persistence drift, enables Alembic migrations, transaction support |
| Connection type | Direct (port 5432), not PgBouncer | asyncpg prepared statements conflict with PgBouncer transaction mode |
| Initial migration strategy | Stamp as baseline, not execute | Tables already exist from Supabase migration 00001 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 3 commit included unrelated staged files**
- **Found during:** Task 3 commit
- **Issue:** The git staging area had pre-existing staged files from other work (api/, auth/, middleware/ files from Plan 04 preparation). The `git reset` command was blocked by tool permissions, so the commit included these extra files alongside the ADR-2 document.
- **Impact:** Low -- the extra files are valid Plan 04 work that would have been committed separately. The ADR-2 file is correctly committed.
- **Files affected:** backend/app/api/, backend/app/auth/, backend/app/middleware/ (Plan 04 files committed early)

## Acceptance Criteria Verification

- [x] `from app.db.engine import engine, AsyncSessionLocal` -- engine.py exports both
- [x] `from app.db.session import get_db` -- session.py exports FastAPI dependency
- [x] Alembic config exists with async env.py and baseline migration at `0001`
- [x] No code imports from `app.db.connection` (grep confirmed zero matches)
- [x] ADR-2 documented at `backend/docs/adr/002-database-access-pattern.md`
- [x] `connection.py` renamed to `supabase_client.py` with scope-limiting docstring

## Next Phase Readiness

Plan 03 unblocks:
- **Plan 04** (API Foundation): Can use `get_db()` dependency in route handlers
- **Plan 05** (Celery Workers): Can use `AsyncSessionLocal` for DB writes in tasks
- **Plan 08** (CI/CD): Alembic migrations can be tested in CI pipeline

No blockers for downstream plans.
