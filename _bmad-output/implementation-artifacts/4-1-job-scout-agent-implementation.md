# Story 4.1: Job Scout Agent Implementation

Status: review

## Story

As a **system**,
I want **a Job Scout Agent that monitors job boards 24/7**,
so that **users receive fresh job matches without manual searching**.

## Acceptance Criteria

1. **AC1 - Job Source Querying:** Given the Job Scout Agent is scheduled to run (nightly batch), when it executes for a user, then it queries configured job aggregator APIs (JSearch primary, Adzuna secondary) for jobs matching user preferences (title, location, salary, work arrangement).

2. **AC2 - Preference Filtering:** Given raw job results from aggregator APIs, when the agent processes them, then it filters jobs based on user preferences from the `user_preferences` table (target_titles, target_locations, salary_minimum, work_arrangement) and excludes jobs from companies in the user's `excluded_companies` list.

3. **AC3 - Deal-Breaker Enforcement:** Given a job that violates any user deal-breaker (excluded_companies, excluded_industries, must_have_benefits, salary below minimum), when scoring occurs, then that job receives a score of 0 and is NOT stored as a match.

4. **AC4 - Job Storage:** Given filtered job results, when storage occurs, then raw job data is persisted in the `jobs` table with proper deduplication (same job URL or same title+company+location = same job), and the `source` field tracks which API provided it.

5. **AC5 - Match Creation:** Given jobs that pass preference filtering and deal-breaker checks, when match records are created, then `matches` records are created linking the user to relevant jobs with a preliminary score (0-100) and status `new`.

6. **AC6 - Match Rationale:** Given each match record created, when the agent produces output, then each match includes a rationale string explaining why the job was selected (e.g., "85% match: skills align, salary in range, remote OK").

7. **AC7 - Agent Output Recording:** Given the agent completes execution, when results are persisted, then an `agent_outputs` record is created with agent_type `job_scout`, the full structured output as JSONB, and the Langfuse trace is completed with cost tracking.

8. **AC8 - Celery Integration:** Given the existing Celery task placeholder `agent_job_scout` in `worker/tasks.py`, when the Job Scout Agent is implemented, then the placeholder is replaced with actual agent instantiation and execution, preserving the existing Langfuse tracing wrapper.

## Tasks / Subtasks

- [x] Task 1: Create job aggregator API client layer (AC: #1)
  - [x]1.1: Create `backend/app/services/job_sources/__init__.py` package
  - [x]1.2: Create `backend/app/services/job_sources/base.py` with `BaseJobSource` abstract class defining `search(query, filters) -> list[RawJob]` interface
  - [x]1.3: Create `backend/app/services/job_sources/jsearch.py` implementing JSearch RapidAPI client (primary source)
  - [x]1.4: Create `backend/app/services/job_sources/adzuna.py` implementing Adzuna API client (secondary source)
  - [x]1.5: Create `backend/app/services/job_sources/aggregator.py` that queries all sources in parallel with per-source timeouts and merges results
  - [x]1.6: Add `RAPIDAPI_KEY`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` to `config.py` settings
  - [x]1.7: Add `httpx` to requirements.txt (already present, verify)

- [x] Task 2: Implement job deduplication and storage (AC: #4)
  - [x]2.1: Create `backend/app/services/job_dedup.py` with dedup logic: match on URL exact match OR (normalized title + company + location)
  - [x]2.2: Extend `Job` model with additional columns needed: `location` (Text), `salary_min` (Integer), `salary_max` (Integer), `employment_type` (Text), `remote` (Boolean), `source_id` (Text, external API job ID), `raw_data` (JSONB, full API response), `posted_at` (DateTime)
  - [x]2.3: Create Alembic migration for new Job columns
  - [x]2.4: Implement `upsert_jobs()` function that deduplicates and inserts/updates jobs in bulk

- [x] Task 3: Implement preference matching and scoring (AC: #2, #3, #5, #6)
  - [x]3.1: Create `backend/app/agents/core/__init__.py` package
  - [x]3.2: Create `backend/app/agents/core/job_scout.py` with `JobScoutAgent` extending `BaseAgent`
  - [x]3.3: Implement `_load_user_preferences()` using orchestrator's `get_user_context()`
  - [x]3.4: Implement `_score_job(job, preferences) -> (score: int, rationale: str)` with scoring algorithm:
    - Title match: 0-25 points (fuzzy match against target_titles)
    - Location match: 0-20 points (exact or remote preference)
    - Salary match: 0-20 points (within salary range)
    - Skills overlap: 0-20 points (job description keywords vs user skills)
    - Seniority match: 0-15 points (matching seniority_levels)
  - [x]3.5: Implement deal-breaker check: if `excluded_companies` match, `excluded_industries` match, salary below `salary_minimum`, or missing `must_have_benefits` → score = 0, skip match
  - [x]3.6: Implement `_build_rationale(score_breakdown) -> str` that produces human-readable rationale
  - [x]3.7: Implement `_create_matches(user_id, scored_jobs) -> list[Match]` that bulk-inserts match records

- [x] Task 4: Wire up Celery task and orchestrator integration (AC: #7, #8)
  - [x]4.1: Update `backend/app/worker/tasks.py` — replace `agent_job_scout` placeholder with actual `JobScoutAgent` instantiation and execution
  - [x]4.2: Ensure Langfuse trace is updated with agent output (match count, job sources queried, execution time)
  - [x]4.3: Verify orchestrator `TASK_ROUTING["job_scout"]` correctly routes to the updated task
  - [x]4.4: Add `agent.job_scout.completed` and `agent.job_scout.jobs_matched` events to activity recording

- [x] Task 5: Write tests (AC: #1-#8)
  - [x]5.1: Create `backend/tests/unit/test_agents/test_job_scout.py` — test scoring algorithm with various preference combinations
  - [x]5.2: Create `backend/tests/unit/test_services/test_job_sources.py` — test each API client with mocked responses
  - [x]5.3: Create `backend/tests/unit/test_services/test_job_dedup.py` — test deduplication logic
  - [x]5.4: Test deal-breaker enforcement (score = 0 for blocklisted companies)
  - [x]5.5: Test rationale generation produces meaningful strings
  - [x]5.6: Test Celery task integration (mock agent, verify task runs and records output)
  - [x]5.7: Test empty preferences gracefully returns no matches (not errors)

## Dev Notes

### Architecture Compliance

**CRITICAL - Follow these architecture decisions exactly:**

1. **Agent Extension Pattern:** JobScoutAgent MUST extend `BaseAgent` from `backend/app/agents/base.py`. Override `execute(user_id, task_data) -> AgentOutput`. The `run()` lifecycle (brake check → execute → record → publish) is inherited automatically.
   [Source: backend/app/agents/base.py]

2. **Agent Type Registration:** Set `agent_type = "job_scout"` as class attribute. This value is already registered in the `AgentType` enum in `models.py` and in the orchestrator's `TASK_ROUTING` dict.
   [Source: backend/app/agents/orchestrator.py:32-37]

3. **Tier Enforcement:** Job Scout is a "read" action available to ALL tiers (L0-L3). L0 users get results tagged with `suggest:` prefix. Use `@requires_tier("l0", action_type="read")` on the execute method or handle via `AutonomyGate` inside execute.
   [Source: backend/app/agents/tier_enforcer.py]

4. **Aggregator APIs, NOT Direct Scraping:** Per Phase 4 research adjustments, use aggregator APIs exclusively:
   - **Primary:** JSearch (RapidAPI) — aggregates LinkedIn, Indeed, Glassdoor, ZipRecruiter via Google Jobs
   - **Secondary:** Adzuna — REST API with `app_id` + `app_key` auth
   - Do NOT attempt Indeed API (doesn't exist publicly) or LinkedIn scraping (actively blocked)
   [Source: .planning/ROADMAP.md - Phase 4 Research Adjustments]

5. **Naming Conventions:**
   - File: `job_scout.py` in `backend/app/agents/core/`
   - Class: `JobScoutAgent`
   - Functions: `get_matching_jobs()`, `score_job()`, `build_rationale()`
   - Events: `agent.job_scout.completed`, `agent.job_scout.jobs_matched`
   [Source: architecture.md - Naming Conventions]

6. **Cost Tracking:** All LLM calls (if any for semantic matching) MUST go through Langfuse tracing. The Celery task already has Langfuse trace setup — maintain it. Target: < $0.50/user/day for job matching.
   [Source: .planning/ROADMAP.md - Phase 4 Success Criteria #5]

7. **Database Access:** Use SQLAlchemy async sessions via `AsyncSessionLocal` from `app.db.engine`. Follow the pattern established in `briefing/generator.py` for database queries.
   [Source: backend/app/agents/briefing/generator.py]

8. **Shared User Context:** Use `get_user_context(user_id)` from `orchestrator.py` to load user profile, preferences, and recent outputs. This is Redis-cached with 5-minute TTL.
   [Source: backend/app/agents/orchestrator.py:172-217]

### Technical Requirements

**JSearch API Integration:**
```python
# Base URL: https://jsearch.p.rapidapi.com/search
# Auth: X-RapidAPI-Key header
# Key params: query, page, num_pages, date_posted, employment_types, job_requirements
# Response: { "status": "OK", "data": [ { job_objects with 30+ fields } ] }
```

**Adzuna API Integration:**
```python
# Base URL: https://api.adzuna.com/v1/api/jobs/us/search/{page}
# Auth: app_id + app_key query params
# Key params: what (keywords), where (location), salary_min, salary_max, full_time, results_per_page
# Response: { "results": [ { title, company.display_name, location.display_name, ... } ] }
```

**RawJob Dataclass (intermediate representation):**
```python
@dataclass
class RawJob:
    source: str          # "jsearch" | "adzuna"
    source_id: str       # External API job ID
    title: str
    company: str
    location: str
    description: str
    url: str
    salary_min: int | None
    salary_max: int | None
    employment_type: str | None  # "FULLTIME", "PARTTIME", "CONTRACT"
    remote: bool
    posted_at: datetime | None
    raw_data: dict       # Full API response for this job
```

**Scoring Algorithm (100-point scale):**
```python
# Title match: 0-25 pts (fuzzy string matching against target_titles)
# Location match: 0-20 pts (exact city match or remote preference satisfied)
# Salary match: 0-20 pts (within salary_minimum to salary_target range)
# Skills overlap: 0-20 pts (keyword extraction from description vs user skills[])
# Seniority match: 0-15 pts (job level indicators vs seniority_levels[])
#
# Deal-breaker override: ANY deal-breaker violation → score = 0, skip
```

**Agent Output Structure:**
```python
AgentOutput(
    action="job_scout_batch",
    rationale=f"Found {match_count} matches from {source_count} sources",
    confidence=0.85,  # Based on data quality
    data={
        "matches_created": match_count,
        "jobs_found": total_jobs,
        "jobs_deduplicated": dedup_count,
        "jobs_filtered_dealbreakers": dealbreaker_count,
        "sources_queried": ["jsearch", "adzuna"],
        "execution_time_ms": elapsed_ms,
    },
    requires_approval=False,  # Job scouting is read-only
)
```

### Library/Framework Requirements

**New Dependencies to Add to `requirements.txt`:**
```
# None needed — httpx is already installed for API calls
```

**New Environment Variables in `config.py`:**
```python
RAPIDAPI_KEY: str = ""          # JSearch API key
ADZUNA_APP_ID: str = ""         # Adzuna application ID
ADZUNA_APP_KEY: str = ""        # Adzuna application key
```

**Existing Dependencies Used:**
- `httpx` — async HTTP client for API calls (already in requirements.txt)
- `sqlalchemy` — async DB operations (already installed)
- `redis` — caching (already installed)

### File Structure Requirements

**Files to CREATE:**
```
backend/app/services/job_sources/__init__.py     # Package init, exports aggregator
backend/app/services/job_sources/base.py         # BaseJobSource ABC
backend/app/services/job_sources/jsearch.py      # JSearch RapidAPI client
backend/app/services/job_sources/adzuna.py       # Adzuna API client
backend/app/services/job_sources/aggregator.py   # Multi-source aggregator
backend/app/services/job_dedup.py                # Job deduplication logic
backend/app/agents/core/__init__.py              # Core agents package
backend/app/agents/core/job_scout.py             # JobScoutAgent class
backend/alembic/versions/XXXX_add_job_columns.py # Migration for new Job columns
backend/tests/unit/test_agents/test_job_scout.py # Agent tests
backend/tests/unit/test_services/test_job_sources.py  # API client tests
backend/tests/unit/test_services/test_job_dedup.py    # Dedup tests
```

**Files to MODIFY:**
```
backend/app/db/models.py          # Extend Job model with new columns
backend/app/worker/tasks.py       # Replace job_scout placeholder with real agent
backend/app/config.py             # Add RAPIDAPI_KEY, ADZUNA_APP_ID, ADZUNA_APP_KEY
backend/requirements.txt          # Verify httpx present (should be)
```

**Files to NOT TOUCH:**
```
backend/app/agents/base.py            # BaseAgent is stable, do not modify
backend/app/agents/orchestrator.py    # Already has job_scout routing, no changes needed
backend/app/agents/tier_enforcer.py   # Tier logic is stable
backend/app/agents/brake.py           # Brake logic is stable
backend/app/agents/briefing/*         # Briefing agent is separate concern
frontend/*                            # No frontend changes in this story (UI is Story 4-6)
```

### Project Structure Notes

- Agent file goes in `backend/app/agents/core/job_scout.py` per architecture.md project structure (core agents = all tiers)
- Job source clients go in `backend/app/services/job_sources/` following the service layer pattern established by `resume_parser.py` and `storage_service.py`
- Tests follow existing convention: `backend/tests/unit/test_agents/` for agent tests, `backend/tests/unit/test_services/` for service tests
- The `backend/app/agents/core/` directory is NEW and must be created (first core agent)

### Testing Requirements

- **Coverage Target:** >80% line, >70% branch
- **Framework:** pytest with async support (pytest-asyncio)
- **Mock Strategy:**
  - Mock HTTP responses from JSearch and Adzuna APIs (use `httpx` mock or `respx`)
  - Mock database sessions for storage/query tests
  - Mock Redis for caching tests
  - Do NOT make real API calls in tests
- **Key Test Scenarios:**
  - Happy path: preferences match, jobs found, matches created
  - No results: API returns empty, agent handles gracefully
  - Deal-breaker: blocked company returns score 0
  - Dedup: same job from two sources creates one Job record
  - API failure: one source fails, other still works (graceful degradation)
  - Empty preferences: user has no preferences set, returns empty matches (not error)
  - Scoring edge cases: missing salary data, remote-only preference, multiple title matches

### References

- [Source: _bmad-output/planning-artifacts/epics.md - Epic 4, Story 4.1]
- [Source: _bmad-output/planning-artifacts/architecture.md - Agent Architecture, Naming Conventions]
- [Source: _bmad-output/planning-artifacts/prd.md - F4-SCOUT Job Scout Agent]
- [Source: .planning/ROADMAP.md - Phase 4 Research Adjustments]
- [Source: backend/app/agents/base.py - BaseAgent extension pattern]
- [Source: backend/app/agents/orchestrator.py - Task routing and user context]
- [Source: backend/app/agents/tier_enforcer.py - Tier enforcement decorator]
- [Source: backend/app/agents/briefing/generator.py - Example agent implementation pattern]
- [Source: backend/app/db/models.py - Job, Match, UserPreference, AgentOutput models]
- [Source: backend/app/worker/tasks.py - agent_job_scout Celery task placeholder]
- [JSearch API: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch]
- [Adzuna API: https://developer.adzuna.com/]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Route Taken

MODERATE (score: 8/16)

### GSD Subagents Used

gsd-executor

### Debug Log References

- pytest-asyncio was not installed — auto-installed during test execution
- Test mock paths adjusted for lazy imports inside async functions

### Completion Notes List

- Created job aggregator API client layer with BaseJobSource ABC, JSearch and Adzuna implementations
- JobAggregator queries all sources in parallel with per-source timeout and graceful degradation
- Job deduplication via URL match or content-based hash (normalized title+company+location)
- Extended Job model with 8 new columns: location, salary_min, salary_max, employment_type, remote, source_id, raw_data (JSONB), posted_at
- Alembic migration created for new Job columns
- JobScoutAgent extends BaseAgent with 5-category scoring algorithm (100-point scale)
- Deal-breaker enforcement: excluded companies, excluded industries, salary below minimum → score=0, no match
- Rationale generation produces human-readable breakdown per match
- Celery task placeholder replaced with actual JobScoutAgent instantiation
- Langfuse tracing preserved in Celery task wrapper
- 41 tests passing across 3 test files

### Change Log

- 2026-01-31: Initial implementation of all 5 task groups

### File List

**Created:**
- `backend/app/services/job_sources/__init__.py` — Package init, exports key classes
- `backend/app/services/job_sources/base.py` — RawJob dataclass, BaseJobSource ABC
- `backend/app/services/job_sources/jsearch.py` — JSearch RapidAPI client
- `backend/app/services/job_sources/adzuna.py` — Adzuna API client
- `backend/app/services/job_sources/aggregator.py` — Multi-source parallel aggregator
- `backend/app/services/job_dedup.py` — Deduplication and upsert logic
- `backend/app/agents/core/__init__.py` — Core agents package
- `backend/app/agents/core/job_scout.py` — JobScoutAgent with 5-category scoring
- `backend/alembic/versions/2026_01_31_0004_add_job_metadata_columns.py` — Migration
- `backend/tests/unit/test_services/__init__.py` — Test package init
- `backend/tests/unit/test_services/test_job_sources.py` — API client tests (16 tests)
- `backend/tests/unit/test_services/test_job_dedup.py` — Dedup tests (10 tests)
- `backend/tests/unit/test_agents/test_job_scout.py` — Agent tests (15 tests)

**Modified:**
- `backend/app/db/models.py` — Added 8 columns to Job model
- `backend/app/worker/tasks.py` — Replaced placeholder with real JobScoutAgent execution
- `backend/app/config.py` — Added RAPIDAPI_KEY, ADZUNA_APP_ID, ADZUNA_APP_KEY
