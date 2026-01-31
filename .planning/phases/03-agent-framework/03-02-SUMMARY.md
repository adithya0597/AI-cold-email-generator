---
phase: "03"
plan: "02"
subsystem: agent-database
tags: [sqlalchemy, alembic, agent-models, approval-queue, briefings, agent-activity]
depends_on:
  requires: ["03-01"]  # ADR-1 decision (no langgraph columns)
  provides: ["agent-output-model", "approval-queue-model", "briefing-model", "agent-activity-model", "briefing-user-prefs"]
  affects: ["03-03", "03-04", "03-05", "03-06", "03-07", "03-08"]
tech_stack:
  added: []
  patterns: ["text-constants-over-pg-enum", "manual-alembic-migration"]
key_files:
  created:
    - backend/alembic/versions/2026_01_31_0003_agent_framework_tables.py
  modified:
    - backend/app/db/models.py
decisions:
  - id: "03-02-01"
    title: "Text constant classes for new status types"
    choice: "Plain Python classes with string constants (ApprovalStatus, BrakeState, ActivitySeverity, BriefingType)"
    reason: "Phase 2 convention -- avoids ALTER TYPE migrations for string-typed columns"
  - id: "03-02-02"
    title: "No langgraph columns in approval_queue"
    choice: "Omit langgraph_thread_id and langgraph_checkpoint_ns"
    reason: "ADR-1 decided custom orchestrator; no LangGraph state to persist"
  - id: "03-02-03"
    title: "Existing AgentType enum extended"
    choice: "Added BRIEFING to existing PG enum via ALTER TYPE ADD VALUE"
    reason: "AgentType already uses PG enum; adding a value is safe and backward-compatible"
metrics:
  duration: "~5 min"
  completed: "2026-01-31"
---

# Phase 3 Plan 02: Database Schema + Agent Models Summary

**SQLAlchemy models and Alembic migration for agent framework tables -- approval queue, briefings, agent activities, and extended agent outputs with briefing user preferences.**

## What Was Done

### Task 1: SQLAlchemy Models (commit 1b912f1)

Added/extended models in `backend/app/db/models.py`:

- **AgentOutput** -- Extended with `task_id` (Celery task ID), `rationale`, `confidence` columns and composite index on (user_id, created_at)
- **ApprovalQueueItem** -- New table `approval_queue` with JSONB payload, text status (pending/approved/rejected/expired/paused), expires_at, indexes on (user_id, status) and expires_at
- **Briefing** -- New table `briefings` with JSONB content, briefing_type (full/lite), delivery tracking (generated_at, delivered_at, read_at, delivery_channels), index on (user_id, generated_at)
- **AgentActivity** -- New table `agent_activities` for activity feed with event_type, severity (info/warning/action_required), JSONB data, index on (user_id, created_at)
- **UserPreference** -- Added briefing_hour (default 8), briefing_minute (default 0), briefing_timezone (default UTC), briefing_channels (default [in_app, email])
- **Text constant classes** -- ApprovalStatus, BrakeState, ActivitySeverity, BriefingType (not PG Enums, per Phase 2 convention)
- **AgentType enum** -- Added BRIEFING value

### Task 2: Alembic Migration 0003 (commit f203183)

Created `backend/alembic/versions/2026_01_31_0003_agent_framework_tables.py`:

- ALTER TYPE agent_type ADD VALUE 'briefing'
- Add columns to agent_outputs (task_id, rationale, confidence) + index
- Create approval_queue table with all columns, indexes, and soft delete/timestamp mixins
- Create briefings table with all columns and index
- Create agent_activities table with all columns and index
- Add briefing config columns to user_preferences
- Complete downgrade function (drops in reverse order; notes enum value cannot be removed)
- Marked as "review when first applied" (manual migration, no DB connection)

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

1. **Text constant classes over PG Enum** for ApprovalStatus, BrakeState, ActivitySeverity, BriefingType. These are plain Python classes with string attributes, stored as Text columns. Avoids ALTER TYPE migrations that Phase 2 established as problematic.

2. **No langgraph columns** in approval_queue. ADR-1 resolved in Plan 01: custom orchestrator wins. The RESEARCH.md schema included langgraph_thread_id and langgraph_checkpoint_ns as "if LangGraph" columns -- these are omitted.

3. **Extended existing AgentType PG enum** with BRIEFING value rather than switching to text constants. The enum already exists in the database; adding a value via ALTER TYPE ADD VALUE IF NOT EXISTS is safe and keeps consistency with existing agent_type usage in agent_outputs and agent_actions tables.

## Next Phase Readiness

- All 4 new models are importable and ready for use by Plans 03-08
- Migration is ready for review and application when database is connected
- No blockers for Wave 1 continuation (Plan 03: BaseAgent + Tier Enforcement)
