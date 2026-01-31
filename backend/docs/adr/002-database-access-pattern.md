# ADR-2: Database Access Pattern

**Status:** Accepted
**Date:** 2026-01-31
**Decision makers:** Architecture review
**Tags:** database, sqlalchemy, supabase, asyncpg

## Context

The JobPilot codebase has two database layers:

1. **Supabase SDK** (`supabase-py`) -- a REST client that talks to the PostgREST proxy on the Supabase project. Used by `author_styles_service.py` for CRUD operations.

2. **SQLAlchemy ORM** -- full model definitions exist in `app/db/models.py` (8 tables: users, profiles, jobs, applications, matches, documents, agent_actions, agent_outputs) but with **no engine or session factory configured**. These models are completely non-functional.

The Supabase PostgreSQL database already has tables created via `supabase/migrations/00001_initial_schema.sql`, applied directly through the Supabase dashboard.

This dual-layer situation creates risk:
- Two different abstractions can read/write the same tables, causing data drift.
- Supabase SDK uses REST (PostgREST), which cannot participate in database transactions.
- No migration tooling -- schema changes are applied manually via Supabase SQL editor.
- ORM models exist but are dead code with no engine to power them.

## Decision

**SQLAlchemy is the ONLY application data access layer.**

All reads and writes to application tables (users, profiles, jobs, applications, matches, documents, agent_actions, agent_outputs) MUST go through SQLAlchemy using the async engine configured in `app/db/engine.py`.

**Supabase SDK is restricted to three use cases:**
1. **File storage** -- Supabase Storage for resume uploads, signed download URLs
2. **Auth token forwarding** -- If/when Supabase Auth is used alongside Clerk for RLS
3. **Realtime subscriptions** -- Supabase Realtime for WebSocket-based change notifications (future)

## Connection Configuration

Use the **direct PostgreSQL connection** (port 5432), not the PgBouncer pooler (port 6543):

```
DATABASE_URL=postgresql+asyncpg://user:pass@db.project.supabase.co:5432/postgres
```

Required connection arguments for Supabase compatibility:
- `statement_cache_size=0` -- prevents `DuplicatePreparedStatementError` when asyncpg prepared statements conflict with Supabase's connection pooler
- `server_settings={"jit": "off"}` -- avoids JIT compilation overhead on shared infrastructure

## Migration Strategy

- **Alembic** manages all schema migrations going forward.
- The initial Alembic migration (`0001`) is a baseline that matches the existing Supabase schema. It is stamped as applied (`alembic stamp head`), not executed.
- All future schema changes go through `alembic revision --autogenerate`.
- Raw SQL via Supabase dashboard is prohibited for application tables.

## Anti-Patterns to Avoid

### Never use both Supabase SDK and SQLAlchemy for the same table

```python
# BAD -- dual writes cause drift
supabase.table("users").insert({"email": "a@b.com"}).execute()
session.add(User(email="a@b.com"))
await session.commit()

# GOOD -- SQLAlchemy only for application data
session.add(User(email="a@b.com"))
await session.commit()
```

### Never bypass Alembic for schema changes

```sql
-- BAD -- manual DDL in Supabase SQL editor
ALTER TABLE users ADD COLUMN avatar_url TEXT;

-- GOOD -- Alembic migration
-- alembic revision --autogenerate -m "add avatar_url to users"
```

### Never use Supabase SDK for queries that need transactions

```python
# BAD -- PostgREST has no transaction support
supabase.table("applications").insert({...}).execute()
supabase.table("agent_actions").insert({...}).execute()  # If this fails, app is inserted

# GOOD -- SQLAlchemy transaction
async with AsyncSessionLocal() as session:
    session.add(Application(...))
    session.add(AgentAction(...))
    await session.commit()  # Atomic
```

## Consequences

### Positive
- Single source of truth for all application data
- Full transaction support (ACID guarantees)
- Type-safe queries via ORM
- Automated migration tracking via Alembic
- Compatible with FastAPI dependency injection (`get_db()`)

### Negative
- Supabase dashboard data explorer becomes read-only for debugging
- Cannot use Supabase client libraries' built-in query builder for app data
- Must maintain SQLAlchemy models in sync with database (enforced by Alembic autogenerate)

### Neutral
- Supabase Storage and Realtime remain viable via the SDK
- Row-Level Security (RLS) policies in Supabase still apply at the database level, regardless of which client connects

## References

- `backend/app/db/engine.py` -- async engine configuration
- `backend/app/db/session.py` -- FastAPI dependency for session injection
- `backend/app/db/supabase_client.py` -- restricted Supabase SDK client
- `backend/app/db/models.py` -- ORM model definitions
- `backend/alembic/` -- migration configuration and versions
- `supabase/migrations/00001_initial_schema.sql` -- original schema (now managed by Alembic)
