# CLAUDE.md - Supabase / Database Reference

> For project overview and tech stack, see root `/CLAUDE.md`

## Overview

Supabase PostgreSQL database with SQL migrations and Row-Level Security (RLS) for multi-tenant data isolation. Backend connects via SQLAlchemy async with asyncpg driver.

## Migration Convention

### File Naming
```
NNNNN_description.sql           # Forward migration
NNNNN_description_rollback.sql  # Rollback (optional but recommended)
```

Example: `00003_row_level_security.sql`, `00003_row_level_security_rollback.sql`

### Header Comments
Every migration should include:
```sql
-- Migration NNNNN: Brief description
-- Story/Epic: Reference to planning document
--
-- Detailed explanation of what this migration does and why.
```

## Schema Conventions

### Primary Keys
```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```

### Timestamps
```sql
created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

Add auto-update trigger:
```sql
CREATE TRIGGER update_tablename_updated_at
    BEFORE UPDATE ON tablename
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### Soft Deletes
```sql
deleted_at TIMESTAMPTZ  -- NULL = active, non-NULL = deleted
```

Use conditional unique indexes to exclude soft-deleted rows:
```sql
CREATE UNIQUE INDEX idx_profiles_email_active
    ON profiles(email) WHERE deleted_at IS NULL;
```

### Settings/Metadata
Use JSONB for flexible settings:
```sql
settings JSONB NOT NULL DEFAULT '{}'::jsonb
```

### Index Naming
```
idx_<table>_<column>           -- Single column
idx_<table>_<col1>_<col2>      -- Composite
idx_<table>_<column>_active    -- Conditional (WHERE deleted_at IS NULL)
```

## Row-Level Security (RLS)

### Policy Pattern
RLS is enabled on all user-scoped tables. Each table has a policy using:
```sql
current_setting('app.current_user_id', true)::uuid
```

The second argument `true` returns NULL instead of error when not set.

### Example Policy
```sql
ALTER TABLE matches ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_isolation_policy ON matches
    FOR ALL
    USING (user_id = current_setting('app.current_user_id', true)::uuid);
```

### Backend Integration
Backend sets the user context per-transaction via SQLAlchemy:
```python
async with session.begin():
    await session.execute(
        text("SET LOCAL app.current_user_id = :user_id"),
        {"user_id": str(user_id)}
    )
    # All queries in this transaction are now scoped to user_id
```

### RLS-Enabled Tables
- `profiles`
- `applications`
- `matches`
- `documents`
- `agent_actions`
- `agent_outputs`
- `swipe_events`
- `learned_preferences`

### Development Bypass
For local development only (requires BOTH conditions):
```sql
CREATE POLICY dev_bypass_policy ON tablename
    FOR ALL
    USING (
        current_setting('app.environment', true) = 'development'
        AND current_setting('app.rls_bypass', true) = 'true'
    );
```

## Writing a New Migration

### Checklist

1. **Choose sequence number** — Check existing migrations, use next number (e.g., `00005`)
2. **Create forward migration** — `supabase/migrations/00005_description.sql`
3. **Create rollback** — `supabase/migrations/00005_description_rollback.sql`
4. **Add RLS if user-scoped** — Any table with `user_id` column needs RLS policy
5. **Use NOT NULL with defaults** — Avoid nullable columns unless necessary
6. **Add updated_at trigger** — For tables that will be updated

### Template
```sql
-- Migration 00005: Add feature_x table
-- Story: Story reference from planning docs
--
-- Description of the table and its purpose

-- Create table
CREATE TABLE IF NOT EXISTS feature_x (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_feature_x_user_id ON feature_x(user_id);
CREATE UNIQUE INDEX idx_feature_x_name_active ON feature_x(user_id, name) WHERE deleted_at IS NULL;

-- Updated_at trigger
CREATE TRIGGER update_feature_x_updated_at
    BEFORE UPDATE ON feature_x
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- RLS
ALTER TABLE feature_x ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_isolation_policy ON feature_x
    FOR ALL
    USING (user_id = current_setting('app.current_user_id', true)::uuid);

CREATE POLICY dev_bypass_policy ON feature_x
    FOR ALL
    USING (
        current_setting('app.environment', true) = 'development'
        AND current_setting('app.rls_bypass', true) = 'true'
    );
```

### Rollback Template
```sql
-- Rollback 00005: Remove feature_x table

DROP POLICY IF EXISTS dev_bypass_policy ON feature_x;
DROP POLICY IF EXISTS user_isolation_policy ON feature_x;
DROP TRIGGER IF EXISTS update_feature_x_updated_at ON feature_x;
DROP INDEX IF EXISTS idx_feature_x_name_active;
DROP INDEX IF EXISTS idx_feature_x_user_id;
DROP TABLE IF EXISTS feature_x;
```

## Commands

```bash
# Push migrations to Supabase (hosted)
supabase db push

# Local migration runner (uses DATABASE_URL from .env)
python backend/scripts/run_migrations.py

# Generate types from schema (if using supabase-js)
supabase gen types typescript --local > src/types/database.ts
```

## Current Migrations

| File | Purpose |
|------|---------|
| `00001_initial_schema.sql` | Core tables (profiles, applications, matches, documents, agents) |
| `00002_swipe_events_learned_preferences.sql` | Swipe tracking for preference learning |
| `00002_pipeline_tables.sql` | Application pipeline stages |
| `00002_enterprise_admin.sql` | Multi-tenant org administration |
| `00003_row_level_security.sql` | RLS policies for all user tables |
| `00003_invitations.sql` | Org invitation system |
| `00004_storage_rls_policies.sql` | Supabase Storage bucket policies |
| `00004_org_autonomy_defaults.sql` | Org-level autonomy settings |
