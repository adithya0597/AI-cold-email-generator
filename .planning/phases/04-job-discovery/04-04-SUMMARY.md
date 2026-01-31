# Phase 4 Plan 4: AI Job Matching Algorithm Summary

**One-liner:** Two-stage scoring pipeline -- heuristic pre-filter + GPT-3.5-turbo LLM refinement with cost tracking, company size scoring, and configurable threshold

## What Was Done

### Task 1: Create LLM Job Scoring Service
- Created `backend/app/services/job_scoring.py` with `ScoringResult` dataclass and `score_job_with_llm()` async function
- Scoring prompt includes 6 dimensions: title_match, skills_overlap, location_match, salary_match, company_size, seniority_match
- Uses `OpenAIClient().generate_json()` with FAST_MODEL (gpt-3.5-turbo), temperature=0.3, max_tokens=300
- Defensive parsing: score clamped 0-100, missing fields get neutral defaults, full try/except fallback
- Cost tracking via `cost_tracker.track_llm_cost()` with token estimation (len//4)
- Lazy imports for OpenAIClient and cost_tracker inside function body
- Commit: `8fdeb63`

### Task 2: Add Company Size to Heuristic Scoring
- Added `_score_company_size()` method (0-10 points) to JobScoutAgent
- Extracts company size from raw_data checking keys: companySize, company_size, employerSize, employer_size
- Uses `is not None` for numeric comparisons (H1 pattern)
- Scoring max now 110 (was 100), normalized via `int(raw/1.1)` to maintain 0-100 range
- `_build_rationale()` updated to accept pre-computed normalized total
- Commit: `d698dff`

### Task 3: Integrate LLM Scoring into Pipeline
- Two-stage pipeline in `execute()`: heuristic pre-filter (>= threshold*0.5) then LLM refinement
- LLM scoring gated behind `settings.LLM_SCORING_ENABLED` feature flag
- Graceful fallback: any LLM exception preserves heuristic score
- Final filter at `settings.MATCH_SCORE_THRESHOLD` (default 40) replaces `score > 0`
- user_id passed through for cost tracking
- Commit: `d13cd74`

### Task 4: Add Configuration Settings
- `MATCH_SCORE_THRESHOLD: int = 40` and `LLM_SCORING_ENABLED: bool = True` added to Settings
- `job_scoring` added to fast_tasks list in `LLMConfig.get_model_for_task()`
- Commit: `9d09ee0`

### Task 5: Write Tests
- Created `test_job_scoring.py` with 7 tests: happy path, LLM failure fallback, invalid score range, missing fields, cost tracking, no-user-id skips tracking, negative score clamping
- Updated `test_job_scout.py`: 8 new company size tests, 2 threshold tests, rationale tests updated for normalization
- All 36 tests passing
- Commit: `339f369`

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Patch `app.core.llm_clients.OpenAIClient` (source module) in tests | Lazy import inside function means module-level attribute doesn't exist on job_scoring |
| Use `sys.modules` mock for cost_tracker in tests | `app.observability.__init__` imports tracing which needs opentelemetry (not in test deps) |
| Score normalization via `int(raw/1.1)` | Simple integer division keeps scores in 0-100 range when adding company_size (0-10) to existing 0-100 breakdown |
| Disable LLM scoring in execute() happy path test | Avoids needing to mock entire LLM + cost tracking chain in integration-style test |

## Deviations from Plan

None -- plan executed exactly as written.

## Files Changed

### Created
- `backend/app/services/job_scoring.py` -- LLM scoring service (209 lines)
- `backend/tests/unit/test_services/test_job_scoring.py` -- LLM scoring tests (7 tests)

### Modified
- `backend/app/agents/core/job_scout.py` -- company_size scoring, LLM integration, threshold filtering
- `backend/app/config.py` -- MATCH_SCORE_THRESHOLD, LLM_SCORING_ENABLED settings
- `backend/app/core/llm_config.py` -- job_scoring in fast_tasks list
- `backend/tests/unit/test_agents/test_job_scout.py` -- company size tests, threshold tests, rationale updates

## Test Results

```
36 passed in 0.44s
```

## Duration

~6 minutes
