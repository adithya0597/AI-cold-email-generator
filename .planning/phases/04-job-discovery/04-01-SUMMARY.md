# Phase 4 Plan 1: Job Scout Agent Implementation Summary

**One-liner:** JSearch + Adzuna aggregator clients with 5-category preference scoring, deal-breaker filtering, and Match record creation via BaseAgent extension.

## What Was Built

### Job Source API Layer (`backend/app/services/job_sources/`)
- **base.py**: `RawJob` dataclass and `BaseJobSource` ABC with async `search()` method
- **jsearch.py**: `JSearchSource` -- RapidAPI JSearch client via httpx async, maps response to RawJob, graceful error handling
- **adzuna.py**: `AdzunaSource` -- Adzuna API client, similar pattern with app_id/app_key auth
- **aggregator.py**: `JobAggregator` -- parallel multi-source search with `asyncio.gather(return_exceptions=True)`, per-source 30s timeout

### Job Deduplication (`backend/app/services/job_dedup.py`)
- `normalize_text()`: lowercase, strip, collapse whitespace
- `compute_dedup_key()`: SHA-256 of URL (if present) or (title + company + location)
- `upsert_jobs()`: batch dedup within input + against DB, insert new, update existing

### Job Scout Agent (`backend/app/agents/core/job_scout.py`)
- `JobScoutAgent(BaseAgent)` with `agent_type = "job_scout"`
- Full `execute()` workflow: context -> queries -> fetch -> dedup -> score -> filter -> match
- 5-category scoring (0-100): title (25), location (20), salary (20), skills (20), seniority (15)
- Deal-breaker checks: excluded companies/industries, salary below minimum
- Rationale builder: "78% match: title (20/25), location (20/20), ..."
- Match record creation with score, rationale, status="new"

### Database Changes
- Job model: added location, salary_min/max, employment_type, remote, source_id, raw_data, posted_at
- Alembic migration 0004 (manual, no DB connection)

### Celery Integration
- `agent_job_scout` task: replaced placeholder with actual `JobScoutAgent().run()` call
- Preserves existing Langfuse tracing and error handling

### Configuration
- Added RAPIDAPI_KEY, ADZUNA_APP_ID, ADZUNA_APP_KEY to Settings

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| SHA-256 for dedup keys | Consistent key length, handles URL or composite content |
| 5-category scoring breakdown | Clear, debuggable rationale; easy to tune weights |
| Deal-breakers skip job entirely | No Match record created for violated jobs (score=0 semantics) |
| Salary unknown = not a deal-breaker | Only reject when salary IS known AND below minimum |
| Neutral scores for missing preferences | Empty prefs get mid-range scores, not zeros |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] pytest-asyncio not installed**
- **Found during:** Task 5
- **Issue:** All async tests were SKIPPED because pytest-asyncio wasn't installed despite being in requirements.txt
- **Fix:** `pip install pytest-asyncio` to unblock test execution
- **Files modified:** None (runtime dependency install)

**2. [Rule 1 - Bug] Fixed test mock paths for lazy imports**
- **Found during:** Task 5
- **Issue:** Patches targeted `app.agents.core.job_scout.get_user_context` but the function is imported lazily inside `execute()`, so the module-level attribute doesn't exist
- **Fix:** Patched at source module `app.agents.orchestrator.get_user_context`; used `sys.modules` dict patching for `app.db.engine`
- **Files modified:** test_job_scout.py

## Test Results

**41 tests, all passing:**
- test_job_sources.py: 13 tests (JSearch, Adzuna, Aggregator)
- test_job_dedup.py: 10 tests (normalize, dedup key, precedence)
- test_job_scout.py: 18 tests (scoring, deal-breakers, rationale, execute, integration)

## Commits

| Hash | Message |
|------|---------|
| db2fad2 | feat(04-01): create job aggregator API client layer |
| d587f8a | feat(04-01): implement job deduplication and storage |
| 0dc5730 | feat(04-01): implement JobScoutAgent with preference matching and scoring |
| 37f1cd7 | feat(04-01): wire JobScoutAgent into Celery task |
| 81ac72d | test(04-01): add comprehensive tests for Job Scout agent |

## Metrics

- **Duration:** ~8 minutes
- **Completed:** 2026-01-31
- **Tasks:** 5/5
