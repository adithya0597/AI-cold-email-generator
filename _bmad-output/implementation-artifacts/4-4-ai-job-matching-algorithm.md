# Story 4.4: AI Job Matching Algorithm

Status: done

## Story

As a **user**,
I want **jobs scored by AI based on my profile and preferences**,
so that **I see the best matches first**.

## Acceptance Criteria

1. **AC1 - Two-Stage Scoring Pipeline:** Given a job has been fetched and stored, when the matching algorithm runs, then it first applies the existing heuristic scoring (title, location, salary, skills, seniority), and jobs passing the heuristic threshold are then scored by an LLM (GPT-3.5) for a refined 0-100 score incorporating all six dimensions: title match, skills overlap, location match, salary range compatibility, company size preference, and seniority level alignment.

2. **AC2 - LLM Scoring Service:** Given a job and user profile+preferences, when the LLM scoring service is called, then it returns a structured JSON response containing: `score` (0-100 integer), `rationale` (brief explanation), and `breakdown` (per-dimension scores) — parsed via `generate_json()` on `OpenAIClient` with the FAST_MODEL (gpt-3.5-turbo).

3. **AC3 - Company Size Scoring:** Given a user has set `min_company_size` in preferences and the job's `raw_data` contains company size information (e.g., LinkedIn's `companySize`, Indeed's employer data), when scoring runs, then company size compatibility is factored into the LLM scoring prompt and the heuristic scoring adds a new company_size dimension (0-10 points).

4. **AC4 - Configurable Threshold:** Given the scoring pipeline runs, when jobs are scored, then only jobs scoring >= 40 (configurable via `MATCH_SCORE_THRESHOLD` setting, default 40) are kept as matches — replacing the current `score > 0` threshold.

5. **AC5 - Performance:** Given the LLM scoring service is called, when scoring a single job, then the entire scoring pipeline (heuristic + LLM) completes within 5 seconds per job. Heuristic-only scoring remains instant (<10ms).

6. **AC6 - Cost Efficiency:** Given LLM scoring runs, when each call completes, then the cost is tracked via the existing `cost_tracker.track_llm_cost()` using model name and token counts. The GPT-3.5 cost for scoring (~$0.00055/job) keeps total monthly LLM cost well under the $6/user/month budget.

7. **AC7 - Graceful Degradation:** Given the LLM API is unavailable or returns an error, when scoring runs, then the system falls back to heuristic-only scoring — the heuristic score is used directly as the match score, logged as a warning, and the pipeline continues without interruption.

8. **AC8 - Test Coverage:** Given the scoring service is implemented, when tests run, then unit tests cover: LLM scoring happy path, error/fallback to heuristic, threshold filtering, company size scoring, score breakdown parsing, and cost tracking integration — with >80% line coverage.

## Tasks / Subtasks

- [x] Task 1: Create LLM job scoring service (AC: #2, #5, #6)
  - [x] 1.1: Create `backend/app/services/job_scoring.py` with `score_job_with_llm(job, preferences, profile) -> ScoringResult` async function
  - [x] 1.2: Define `ScoringResult` dataclass: `score: int`, `rationale: str`, `breakdown: dict[str, int]`, `model_used: str`, `used_llm: bool`
  - [x] 1.3: Build scoring prompt that includes job details + user preferences + profile skills, requesting structured JSON output with score (0-100), rationale, and per-dimension breakdown
  - [x] 1.4: Use `OpenAIClient().generate_json()` with FAST_MODEL (gpt-3.5-turbo), temperature=0.3, max_tokens=300
  - [x] 1.5: Parse LLM response defensively — validate score is 0-100, fallback to heuristic on parse failure
  - [x] 1.6: Integrate `cost_tracker.track_llm_cost()` after each LLM call with model name and token counts

- [x] Task 2: Add company size to heuristic scoring (AC: #3)
  - [x] 2.1: Add `_score_company_size(job, preferences) -> int` method to `JobScoutAgent` (0-10 points)
  - [x] 2.2: Extract company size from `job.raw_data` (check `companySize`, `company_size`, `employerSize` fields)
  - [x] 2.3: Compare against `preferences.get("min_company_size")` — exact match or exceeding = 10, below = 0, unknown = 5 (neutral)
  - [x] 2.4: Update `_score_job()` to include company_size dimension in breakdown, adjusting max total to 110 and normalizing to 0-100

- [x] Task 3: Integrate LLM scoring into pipeline (AC: #1, #4, #7)
  - [x] 3.1: Add `MATCH_SCORE_THRESHOLD: int = 40` to `config.py` Settings class
  - [x] 3.2: Update `JobScoutAgent.execute()` scoring loop: heuristic score first, if >= threshold * 0.5 (pre-filter at 20), call LLM scoring for refinement
  - [x] 3.3: Use LLM score as final score when available, fall back to heuristic score on LLM failure
  - [x] 3.4: Filter matches at `MATCH_SCORE_THRESHOLD` (default 40) instead of current `score > 0`
  - [x] 3.5: Pass `user_id` to scoring service for cost tracking

- [x] Task 4: Add configuration settings (AC: #4)
  - [x] 4.1: Add `MATCH_SCORE_THRESHOLD: int = 40` to Settings class in `config.py`
  - [x] 4.2: Add `LLM_SCORING_ENABLED: bool = True` to Settings class (feature flag for LLM scoring)

- [x] Task 5: Write tests (AC: #8)
  - [x] 5.1: Create `backend/tests/unit/test_services/test_job_scoring.py` with `TestScoreJobWithLLM` class
  - [x] 5.2: Test happy path: mock `OpenAIClient.generate_json()` returning valid score JSON, verify ScoringResult
  - [x] 5.3: Test LLM failure fallback: mock generate_json raising exception, verify heuristic fallback
  - [x] 5.4: Test invalid LLM response: score out of range, missing fields — verify fallback
  - [x] 5.5: Test cost tracking integration: verify `track_llm_cost` called with correct args
  - [x] 5.6: Update `test_job_scout.py` — update TestScoreJob to account for company_size dimension and new max score normalization
  - [x] 5.7: Test threshold filtering: verify jobs below 40 are excluded from matches
  - [x] 5.8: Test company size scoring: known size, unknown size, no preference

## Dev Notes

### Architecture Compliance

**CRITICAL — Follow these patterns EXACTLY:**

1. **LLM Client Pattern:** Use the existing `OpenAIClient` from `app.core.llm_clients` — do NOT create a new LLM client or use langchain. The codebase uses raw httpx-based clients.
   [Source: backend/app/core/llm_clients.py — OpenAIClient class]

2. **LLM Model Selection:** Use `LLMConfig.FAST_MODEL` (gpt-3.5-turbo) for scoring — the architecture mandates GPT-3.5 for cost efficiency. Use `LLMConfig.TEMPERATURE_ANALYSIS` (0.3) for consistency.
   [Source: backend/app/core/llm_config.py — LLMConfig class]

3. **Cost Tracking:** Every LLM call MUST be tracked via `cost_tracker.track_llm_cost(user_id, model, input_tokens, output_tokens)`. The cost tracker uses Redis and has a $6/month budget with 80% alert threshold.
   [Source: backend/app/observability/cost_tracker.py — track_llm_cost()]

4. **Token Estimation:** Since the raw httpx client doesn't return token counts directly, estimate tokens: `input_tokens ≈ len(prompt) // 4`, `output_tokens ≈ len(response) // 4`. This is a rough but acceptable heuristic for cost tracking.
   [Source: OpenAI tokenizer approximation — 1 token ≈ 4 characters for English]

5. **Scoring Integration:** The scoring service is a standalone module called FROM `JobScoutAgent.execute()`. It does NOT modify the agent's structure — it enhances the scoring step only.
   [Source: backend/app/agents/core/job_scout.py:86-93 — scoring loop]

6. **Match Model:** The `Match` model stores `score` as `Numeric(5,2)` and `rationale` as `Text`. The LLM-generated rationale replaces the current heuristic breakdown string.
   [Source: backend/app/db/models.py:289-309 — Match class]

7. **Preferences Access:** User preferences are loaded via `get_user_context()` and include `min_company_size` (Integer, nullable), `target_titles`, `target_locations`, `salary_minimum`, `salary_target`, `seniority_levels`, `excluded_companies`, `excluded_industries`.
   [Source: backend/app/db/models.py:458-527 — UserPreference class]

### Previous Story Intelligence (4-3)

**Key learnings from Stories 4-1 through 4-3 that MUST be applied:**

1. **H1 (salary=0 check):** Always use `if value is not None:` instead of `if value:` for numeric fields (salary, score, company_size). This was caught in 4-1 and 4-2 code reviews.
   [Source: Code review fix H1 — all source clients]

2. **Defensive parsing:** Parse LLM response defensively — use `.get()` with defaults, wrap in try/except, fallback gracefully. Same pattern as RapidAPI response parsing in job sources.
   [Source: backend/app/services/job_sources/linkedin.py:97-173 — _parse_response()]

3. **Test mocking pattern:** Mock at the module level using `patch("app.services.job_scoring.OpenAIClient")` with `AsyncMock`. Use `SimpleNamespace` for mock job objects (established in test_job_scout.py).
   [Source: backend/tests/unit/test_agents/test_job_scout.py:23-40 — _make_job helper]

4. **No direct imports in module scope for heavy deps:** The scoring service should lazy-import `OpenAIClient` inside the scoring function, not at module scope — matches the pattern in `job_scout.py` where sources are imported inside `_fetch_jobs()`.
   [Source: backend/app/agents/core/job_scout.py:165-170 — lazy imports]

### Technical Requirements

**LLM Scoring Prompt Design:**
```python
# The prompt should be concise to minimize tokens (cost) while being specific enough for accurate scoring.
# Target: ~400-500 input tokens, ~200 output tokens
# Cost per call: (500/1000 * $0.0005) + (200/1000 * $0.0015) = $0.00055

SCORING_PROMPT = """Score this job match (0-100) for a candidate.

JOB:
Title: {title}
Company: {company}
Location: {location}
Salary: {salary_range}
Description (first 500 chars): {description_truncated}

CANDIDATE PREFERENCES:
Target roles: {target_titles}
Target locations: {target_locations}
Salary range: {salary_min}-{salary_target}
Seniority: {seniority_levels}
Min company size: {min_company_size}
Skills: {skills}

Score breakdown (each 0-100):
- title_match: how well job title matches target roles
- skills_overlap: how many candidate skills appear in job
- location_match: location compatibility (remote bonus)
- salary_match: salary range compatibility
- company_size: company size vs preference
- seniority_match: seniority level alignment

Respond with JSON only:
{"score": <0-100>, "rationale": "<1-2 sentences>", "breakdown": {"title_match": <n>, "skills_overlap": <n>, "location_match": <n>, "salary_match": <n>, "company_size": <n>, "seniority_match": <n>}}"""
```

**ScoringResult Dataclass:**
```python
@dataclass
class ScoringResult:
    score: int                    # 0-100 final score
    rationale: str                # Human-readable explanation
    breakdown: dict[str, int]     # Per-dimension scores
    model_used: str               # e.g. "gpt-3.5-turbo"
    used_llm: bool                # True if LLM was used, False if heuristic fallback
```

**Two-Stage Pipeline Flow:**
```
Jobs from sources
    ↓
Heuristic pre-filter (existing _score_job + company_size)
    ↓
Jobs with heuristic score >= 20 (half of threshold)
    ↓
LLM scoring (GPT-3.5) for refined score + rationale
    ↓
Final score >= MATCH_SCORE_THRESHOLD (40)
    ↓
Create Match records
```

### Library/Framework Requirements

**No new dependencies needed:**
- `httpx` — already used by OpenAIClient
- `json` — stdlib, used for LLM response parsing
- All other dependencies already present

**New environment variables:**
- `MATCH_SCORE_THRESHOLD` — minimum score for match creation (default: 40)
- `LLM_SCORING_ENABLED` — feature flag (default: true)

### File Structure Requirements

**Files to CREATE:**
```
backend/app/services/job_scoring.py              # LLM scoring service
backend/tests/unit/test_services/test_job_scoring.py  # Scoring service tests
```

**Files to MODIFY:**
```
backend/app/config.py                              # Add MATCH_SCORE_THRESHOLD, LLM_SCORING_ENABLED
backend/app/agents/core/job_scout.py               # Integrate LLM scoring, add company_size, update threshold
backend/app/core/llm_config.py                     # Add job_scoring task type to get_model_for_task()
backend/tests/unit/test_agents/test_job_scout.py   # Update scoring tests for new dimensions/threshold
```

**Files to NOT TOUCH:**
```
backend/app/core/llm_clients.py           # LLM client is stable — use as-is
backend/app/observability/cost_tracker.py  # Cost tracker is stable — call existing API
backend/app/services/job_sources/*.py      # Job sources are stable
backend/app/services/job_dedup.py          # Dedup is stable
backend/app/db/models.py                   # Match model already has score + rationale fields
backend/app/agents/base.py                 # BaseAgent is stable
backend/app/agents/orchestrator.py         # No routing changes needed
frontend/*                                 # No frontend in this story
```

### Testing Requirements

- **Coverage Target:** >80% line, >70% branch
- **Framework:** pytest with pytest-asyncio
- **Mock Strategy:**
  - Mock `OpenAIClient.generate_json()` using `AsyncMock` with `patch`
  - Mock `cost_tracker.track_llm_cost()` using `AsyncMock` with `patch`
  - Do NOT make real API calls
  - Do NOT mock database — scoring returns dataclasses, DB interaction is in existing pipeline
- **Test Files:**
  - NEW: `backend/tests/unit/test_services/test_job_scoring.py` — LLM scoring service tests
  - MODIFY: `backend/tests/unit/test_agents/test_job_scout.py` — update for new dimensions
- **Key Test Scenarios:**
  - Happy path: LLM returns valid score JSON, parsed to ScoringResult
  - LLM error: API fails, falls back to heuristic score
  - Invalid response: score out of range (>100, <0), missing fields — fallback
  - Cost tracking: verify `track_llm_cost` called with model and token estimates
  - Company size: known size >= min → 10, known < min → 0, unknown → 5, no preference → 5
  - Threshold: job with score 39 excluded, job with score 40 included
  - Feature flag: LLM_SCORING_ENABLED=False → heuristic only

### Project Structure Notes

- `job_scoring.py` goes in `backend/app/services/` alongside `job_dedup.py`
- Test file goes in `backend/tests/unit/test_services/` (directory already exists from test_job_sources.py)
- Follow exact naming: `score_job_with_llm()` function, `ScoringResult` dataclass
- The scoring service is stateless — no class needed, just async functions

### References

- [Source: _bmad-output/planning-artifacts/epics.md - Epic 4, Story 4.4 (lines 1504-1524)]
- [Source: _bmad-output/planning-artifacts/architecture.md - LLM cost constraint (<$6/user/month)]
- [Source: _bmad-output/planning-artifacts/architecture.md - Agent architecture, custom orchestrator (ADR-1)]
- [Source: backend/app/agents/core/job_scout.py - Existing scoring algorithm (lines 195-418)]
- [Source: backend/app/core/llm_clients.py - OpenAIClient with generate_json()]
- [Source: backend/app/core/llm_config.py - FAST_MODEL=gpt-3.5-turbo, get_model_for_task()]
- [Source: backend/app/observability/cost_tracker.py - track_llm_cost(), MODEL_PRICING]
- [Source: backend/app/db/models.py - Match model (score Numeric 5,2, rationale Text)]
- [Source: backend/app/db/models.py - UserPreference model (min_company_size Integer)]
- [Source: backend/tests/unit/test_agents/test_job_scout.py - Existing test patterns]
- [Source: 4-3-linkedin-job-scraping-integration.md - Code review learnings]
- [Source: 4-2-indeed-job-board-integration.md - Code review learnings H1, M1, M2, M3]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Route Taken

MODERATE (score: 6/16)

### GSD Subagents Used

gsd-executor

### Debug Log References

- No issues encountered — clean implementation following established patterns from 4-1/4-2/4-3

### Completion Notes List

- Created LLM job scoring service (job_scoring.py) with ScoringResult dataclass and score_job_with_llm() async function
- Two-stage scoring pipeline: heuristic pre-filter at threshold*0.5, then GPT-3.5 LLM refinement
- Company size scoring dimension added to heuristic (0-10 pts), total normalized from 110 to 0-100
- Configurable threshold via MATCH_SCORE_THRESHOLD (default 40), feature flag via LLM_SCORING_ENABLED
- Cost tracking integrated via existing cost_tracker.track_llm_cost() with token estimation
- Graceful degradation: LLM failures fall back to heuristic score without interrupting pipeline
- Defensive LLM response parsing: score clamped 0-100, missing fields get neutral defaults
- 36 tests passing (7 new scoring service tests + 10 new agent tests + 19 existing)
- Story-specific coverage: job_scoring.py 86%, job_scout.py 81%, config.py 100%

### Code Review

**Reviewer:** Claude Opus 4.5 (adversarial code review)

**Issues Found: 7 (2 HIGH, 3 MEDIUM, 2 LOW)**

| # | Severity | File | Issue | Resolution |
|---|----------|------|-------|------------|
| 1 | HIGH | job_scoring.py:197 | Token estimation `len(prompt)//4` is unreliable for non-ASCII | Acknowledged — acceptable heuristic per Dev Notes; tracked for future tiktoken integration |
| 2 | HIGH | job_scout.py:104-121 | Sequential LLM calls — no concurrency | **FIXED** — Added `asyncio.gather` with `Semaphore(5)` for bounded concurrent scoring |
| 3 | MEDIUM | job_scoring.py:177 | OpenAIClient instantiated per call | Acknowledged — client is lightweight (no persistent session); fix deferred |
| 4 | MEDIUM | job_scout.py:279 | Magic number `1.1` for normalization | **FIXED** — Derived from `sum(m for _, m in breakdown.values()) / 100` |
| 5 | MEDIUM | job_scoring.py:65 | Description truncation at 500 chars loses context | Acknowledged — per Dev Notes prompt design (~400-500 input tokens target) |
| 6 | LOW | job_scoring.py:34-60 | Prompt injection surface from external job data | Low risk — output is parsed/clamped to 0-100; no action needed |
| 7 | LOW | job_scout.py:500-501 | `_build_rationale` duplicated normalization logic | **FIXED** — Both now use same derived formula |

**Fixes Applied:** 3 of 7 issues fixed (issues 2, 4, 7). Remaining 4 are acknowledged with rationale.

### Change Log

- 2026-01-31: Initial implementation of AI job matching algorithm with two-stage pipeline
- 2026-01-31: Code review fixes — concurrent LLM scoring, derived normalization, DRY rationale

### File List

**Created:**
- `backend/app/services/job_scoring.py` — LLM scoring service (86% coverage)
- `backend/tests/unit/test_services/test_job_scoring.py` — 7 LLM scoring tests

**Modified:**
- `backend/app/config.py` — Added MATCH_SCORE_THRESHOLD, LLM_SCORING_ENABLED settings
- `backend/app/agents/core/job_scout.py` — Company size scoring, LLM integration, threshold filtering
- `backend/app/core/llm_config.py` — Added job_scoring to fast_tasks
- `backend/tests/unit/test_agents/test_job_scout.py` — 10 new tests (company size, threshold, rationale)
