---
phase: 02-onboarding-preferences
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, postgresql, preferences, onboarding]
dependency-graph:
  requires: [01-03]
  provides: [user-preferences-schema, onboarding-state-tracking, profile-extraction-columns]
  affects: [02-03, 02-04, 02-05, 02-06]
tech-stack:
  added: []
  patterns: [hybrid-relational-jsonb, server-default-enums]
key-files:
  created:
    - backend/alembic/versions/2026_01_31_0002_phase2_onboarding_preferences.py
  modified:
    - backend/app/db/models.py
decisions:
  - "Use Text columns (not PG Enum) for onboarding_status, work_arrangement, autonomy_level -- avoids ALTER TYPE migrations"
  - "ARRAY server_default uses '{}' (PG literal) not '[]' -- PostgreSQL array syntax"
  - "Indexes on user_id, requires_h1b_sponsorship, autonomy_level for agent query performance"
metrics:
  duration: ~5 min
  completed: 2026-01-31
---

# Phase 2 Plan 01: Database Schema + Backend Models Summary

Hybrid relational + JSONB preference schema with onboarding state tracking on User model and extraction metadata on Profile model.

## What Was Done

### Task 1: Add enums and update SQLAlchemy models
- Added 3 new enums: `OnboardingStatus`, `WorkArrangement`, `AutonomyLevel`
- Added 4 columns to `User` model: `onboarding_status` (Text, server_default "not_started"), `onboarding_started_at`, `onboarding_completed_at`, `display_name`
- Added `User.preferences` relationship to `UserPreference` (one-to-one)
- Added 5 columns to `Profile` model: `headline`, `phone`, `resume_storage_path`, `extraction_source`, `extraction_confidence`
- Created `UserPreference` model with 25+ columns across 6 sections: job type, location, salary, deal-breakers, H1B/visa, autonomy, plus JSONB `extra_preferences`
- Added 3 indexes via `__table_args__`: user_id, requires_h1b_sponsorship, autonomy_level
- Commit: `3cb4ff3`

### Task 2: Create Alembic migration
- Hand-wrote migration `0002` (down_revision: `0001`) since no DB connection available
- Migration covers: ALTER TABLE users (4 columns), ALTER TABLE profiles (5 columns), CREATE TABLE user_preferences (25+ columns), 3 indexes
- Full downgrade support included
- Commit: `93d5491`

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

1. **Text over PG Enum for status/arrangement/autonomy columns**: The plan specified `Column(Text, ...)` instead of `Column(Enum(...))` for `onboarding_status`, `work_arrangement`, and `autonomy_level`. This avoids the need for ALTER TYPE migrations when adding new values, at the cost of no DB-level constraint. Application-level validation (via Python enums) provides the safety net.

2. **ARRAY server_default syntax**: Used `server_default="{}"` (PostgreSQL array literal) for all ARRAY columns, consistent with the baseline migration pattern.

3. **Manual migration instead of autogenerate**: No database connection available, so the migration was written by hand matching the model definitions exactly. Should be reviewed when first applied.

## Next Phase Readiness

Plan 01 is complete. Plans 02 (Analytics), 03 (Resume Upload), and 04 (Preferences Backend) can now proceed -- they all depend on the models and schema created here.
