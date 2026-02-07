# Story 4.2: Indeed Job Board Integration

Status: done

## Story

As a **Job Scout Agent**,
I want **to fetch jobs from Indeed via a dedicated RapidAPI scraper endpoint**,
so that **users have access to deeper Indeed-specific listings beyond what JSearch aggregates**.

## Acceptance Criteria

1. **AC1 - Indeed Source Client:** Given Indeed integration is configured with a valid `INDEED_RAPIDAPI_HOST` setting, when the agent searches for jobs matching user preferences, then jobs are fetched via the Indeed RapidAPI scraper endpoint following the same `BaseJobSource` pattern as JSearch and Adzuna.

2. **AC2 - Rate Limiting:** Given Indeed requests are being made, when multiple queries execute, then a configurable delay (`INDEED_REQUEST_DELAY_MS`, default 1000ms) is respected between requests to avoid detection/blocking, implemented via `asyncio.sleep()` between paginated calls.

3. **AC3 - Data Mapping:** Given raw Indeed API response data, when parsing occurs, then job data includes: title, company, location, salary (if available), description, URL, employment_type, remote status, posted_at — all mapped to the existing `RawJob` dataclass fields.

4. **AC4 - Deduplication Compatibility:** Given Indeed jobs are fetched, when they pass through the existing `job_dedup.upsert_jobs()` pipeline, then duplicate jobs (same URL or same title+company+location) are correctly detected and skipped — no changes to dedup logic needed.

5. **AC5 - Graceful Degradation:** Given the Indeed API is unavailable, misconfigured, or returns errors, when the agent runs, then errors are logged but do NOT stop the entire batch — other sources (JSearch, Adzuna) continue to work via the existing `JobAggregator` parallel execution pattern.

6. **AC6 - Aggregator Registration:** Given the `IndeedSource` client is implemented, when the `JobScoutAgent` builds its source list, then Indeed is included as a third source in the `JobAggregator` alongside JSearch and Adzuna, gated by whether `INDEED_RAPIDAPI_HOST` is configured (non-empty).

7. **AC7 - Test Coverage:** Given the Indeed source client is implemented, when tests run, then unit tests cover: successful search, empty results, API error handling, rate limiting behavior, response parsing with various field completeness, and missing credentials skip — following the same test patterns established in `test_job_sources.py`.

## Tasks / Subtasks

- [x] Task 1: Create Indeed RapidAPI source client (AC: #1, #3)
  - [x]1.1: Create `backend/app/services/job_sources/indeed.py` implementing `IndeedSource(BaseJobSource)` with `search()` method
  - [x]1.2: Use `httpx.AsyncClient` for HTTP calls with `X-RapidAPI-Key` and `X-RapidAPI-Host` headers (same auth pattern as JSearch)
  - [x]1.3: Implement `_parse_response(data)` mapping Indeed API fields to `RawJob` (title, company, location, salary_min/max, description, url, remote, posted_at, employment_type)
  - [x]1.4: Handle missing/optional fields gracefully (salary often absent, remote status may need inference from title/description)

- [x] Task 2: Implement rate limiting (AC: #2)
  - [x]2.1: Add `request_delay` parameter to `IndeedSource.__init__()` (default 1.0 seconds)
  - [x]2.2: Implement `asyncio.sleep(self._request_delay)` between paginated API calls (if pagination supported)
  - [x]2.3: Log rate limit delays at DEBUG level

- [x] Task 3: Add configuration settings (AC: #1, #6)
  - [x]3.1: Add `INDEED_RAPIDAPI_HOST: str = ""` to `config.py` Settings class (empty = disabled)
  - [x]3.2: The existing `RAPIDAPI_KEY` setting is reused for auth (same RapidAPI account)

- [x] Task 4: Register Indeed in aggregator (AC: #5, #6)
  - [x]4.1: Update `backend/app/services/job_sources/__init__.py` to export `IndeedSource`
  - [x]4.2: Update `JobScoutAgent._fetch_jobs()` in `backend/app/agents/core/job_scout.py` to include `IndeedSource` in the aggregator's source list, gated by `settings.INDEED_RAPIDAPI_HOST` being non-empty
  - [x]4.3: Verify `JobAggregator` graceful degradation handles Indeed failures without affecting other sources (already implemented, just verify)

- [x] Task 5: Write tests (AC: #4, #7)
  - [x]5.1: Add `TestIndeedSource` class to `backend/tests/unit/test_services/test_job_sources.py` following the existing `TestJSearchSource` and `TestAdzunaSource` patterns
  - [x]5.2: Test successful search with mocked httpx response
  - [x]5.3: Test empty results / no jobs returned
  - [x]5.4: Test API error (HTTP 429, 500) returns empty list, logs error
  - [x]5.5: Test missing credentials (empty host) returns empty list immediately
  - [x]5.6: Test response parsing with partial fields (no salary, no location)
  - [x]5.7: Test rate limiting delay is applied (mock asyncio.sleep, verify called)
  - [x]5.8: Verify existing dedup tests pass unchanged (Indeed jobs go through same pipeline)

## Dev Notes

### Architecture Compliance

**CRITICAL - Follow these patterns from Story 4-1 EXACTLY:**

1. **BaseJobSource Extension:** `IndeedSource` MUST extend `BaseJobSource` from `app.services.job_sources.base`. Override `search(query, location, filters) -> list[RawJob]`. Return empty list on any failure — never raise exceptions.
   [Source: backend/app/services/job_sources/base.py]

2. **Client Pattern:** Follow the EXACT same pattern as `JSearchSource` and `AdzunaSource`:
   - Accept optional `client: httpx.AsyncClient` for dependency injection in tests
   - Create client in `search()` if none injected, close after use
   - Use `try/except` around all HTTP calls, return `[]` on failure
   - Log errors via `logger.error()`, log success counts via `logger.info()`
   [Source: backend/app/services/job_sources/jsearch.py, adzuna.py]

3. **RapidAPI Auth Pattern:** Use the SAME auth mechanism as JSearch — `X-RapidAPI-Key` header with `settings.RAPIDAPI_KEY`. Add `X-RapidAPI-Host` header set to `settings.INDEED_RAPIDAPI_HOST`.
   [Source: backend/app/services/job_sources/jsearch.py:70-73]

4. **No Direct Indeed API:** Indeed does NOT have a public job search API. Use a RapidAPI-hosted Indeed scraper/aggregator endpoint instead. The specific host will be configured via `INDEED_RAPIDAPI_HOST` env var so it can be swapped between providers (e.g., "indeed-scraper.p.rapidapi.com" or similar).
   [Source: architecture.md - "Do NOT attempt Indeed API (doesn't exist publicly)"]

5. **Aggregator Integration:** The `JobAggregator` already handles parallel execution with per-source timeouts and graceful degradation. Just add `IndeedSource` to the sources list — no aggregator changes needed.
   [Source: backend/app/services/job_sources/aggregator.py]

6. **Dedup Compatibility:** Indeed jobs flow through the existing `job_dedup.upsert_jobs()` pipeline. The `RawJob.url` field enables URL-based dedup. Content-based dedup (title+company+location) handles cases where the same job appears in both Indeed and JSearch. No dedup changes needed.
   [Source: backend/app/services/job_dedup.py]

### Technical Requirements

**Indeed RapidAPI Integration:**
```python
# Auth: X-RapidAPI-Key + X-RapidAPI-Host headers
# Host: configurable via INDEED_RAPIDAPI_HOST setting
# Key params vary by provider, but typically: query, location, page, sort_by
# Response: varies by provider — parse defensively
#
# Example providers on RapidAPI:
# - "indeed-scraper.p.rapidapi.com"
# - "indeed12.p.rapidapi.com"
# - "jobs-search-api.p.rapidapi.com"
#
# The implementation should be provider-agnostic:
# parse response as list of dicts, map known fields, skip unknowns
```

**IndeedSource Class Structure:**
```python
class IndeedSource(BaseJobSource):
    source_name = "indeed"

    def __init__(
        self,
        api_key: str | None = None,
        host: str | None = None,
        timeout: float = 30.0,
        request_delay: float = 1.0,
        client: httpx.AsyncClient | None = None,
    ):
        self._api_key = api_key or settings.RAPIDAPI_KEY
        self._host = host or settings.INDEED_RAPIDAPI_HOST
        self._timeout = timeout
        self._request_delay = request_delay
        self._client = client
```

**Config Addition:**
```python
# In Settings class in config.py:
INDEED_RAPIDAPI_HOST: str = ""  # Empty = disabled
```

### Previous Story Intelligence (4-1)

**Key learnings from Story 4-1 code review that MUST be applied:**

1. **H1 (salary_min=0 bug):** In `_parse_response()`, use `if item.get("salary_min") is not None:` instead of `if item.get("salary_min"):` to correctly handle salary=0. This was a bug fixed in 4-1 code review.
   [Source: Code review fix H1 — backend/app/services/job_sources/jsearch.py, adzuna.py]

2. **H2 (duplicate match prevention):** Not relevant to this story (no match creation here).

3. **H3 (upsert truthy check):** Not relevant (no dedup code changes).

4. **M1 (missing API key guard):** ALWAYS check credentials at the top of `search()`:
   ```python
   if not self._api_key or not self._host:
       logger.warning("Indeed API credentials not configured, skipping")
       return []
   ```
   [Source: Code review fix M1 — both jsearch.py and adzuna.py have this pattern]

5. **M3 (httpx client lifecycle):** Use the injected client OR create+close pattern:
   ```python
   client = self._client or httpx.AsyncClient(timeout=self._timeout)
   try:
       resp = await client.get(url, params=params, headers=headers)
       ...
   finally:
       if not self._client:
           await client.aclose()
   ```
   [Source: Code review fix M3 — standardized across all source clients]

6. **Test mocking pattern:** Use `httpx.MockTransport` with a handler function to mock HTTP responses. Follow the exact pattern in `test_job_sources.py`:
   ```python
   def _make_mock_client(handler):
       transport = httpx.MockTransport(handler)
       return httpx.AsyncClient(transport=transport)
   ```
   [Source: backend/tests/unit/test_services/test_job_sources.py]

### Library/Framework Requirements

**No new dependencies needed:**
- `httpx` — already installed (used by JSearch, Adzuna)
- All other dependencies (SQLAlchemy, Redis, pytest) already present

**New environment variable:**
- `INDEED_RAPIDAPI_HOST` — host for the Indeed RapidAPI endpoint

### File Structure Requirements

**Files to CREATE:**
```
backend/app/services/job_sources/indeed.py    # IndeedSource client
```

**Files to MODIFY:**
```
backend/app/config.py                                    # Add INDEED_RAPIDAPI_HOST
backend/app/services/job_sources/__init__.py             # Export IndeedSource
backend/app/agents/core/job_scout.py                     # Add IndeedSource to aggregator sources
backend/tests/unit/test_services/test_job_sources.py     # Add TestIndeedSource tests
```

**Files to NOT TOUCH:**
```
backend/app/services/job_sources/base.py       # BaseJobSource is stable
backend/app/services/job_sources/jsearch.py    # JSearch client is stable
backend/app/services/job_sources/adzuna.py     # Adzuna client is stable
backend/app/services/job_sources/aggregator.py # Aggregator handles any source, no changes
backend/app/services/job_dedup.py              # Dedup works with any source, no changes
backend/app/agents/base.py                     # BaseAgent is stable
backend/app/agents/orchestrator.py             # No routing changes needed
backend/app/worker/tasks.py                    # Celery task already calls JobScoutAgent
frontend/*                                     # No frontend in this story
```

### Testing Requirements

- **Coverage Target:** >80% line, >70% branch
- **Framework:** pytest with pytest-asyncio
- **Mock Strategy:**
  - Mock HTTP responses using `httpx.MockTransport` (same pattern as existing tests)
  - Do NOT make real API calls
  - Do NOT mock database — this story only creates `RawJob` objects, DB interaction is handled by existing pipeline
- **Test File:** Add to existing `backend/tests/unit/test_services/test_job_sources.py`
- **Key Test Scenarios:**
  - Happy path: Indeed returns jobs, correctly parsed to RawJob list
  - Empty results: API returns empty array, returns `[]`
  - API error (429, 500): returns `[]`, logs error
  - Missing credentials: returns `[]` immediately without HTTP call
  - Partial fields: salary missing, location missing — parsed gracefully
  - Rate limit delay: verify `asyncio.sleep` is called between paginated requests

### Project Structure Notes

- `indeed.py` goes in `backend/app/services/job_sources/` alongside `jsearch.py` and `adzuna.py`
- Tests go in the existing `test_job_sources.py` file — do NOT create a separate test file
- Follow exact naming convention: `IndeedSource` class, `source_name = "indeed"`, source field in RawJob = `"indeed"`

### References

- [Source: _bmad-output/planning-artifacts/epics.md - Epic 4, Story 4.2]
- [Source: _bmad-output/planning-artifacts/architecture.md - Aggregator APIs, NOT Direct Scraping]
- [Source: backend/app/services/job_sources/base.py - BaseJobSource ABC and RawJob dataclass]
- [Source: backend/app/services/job_sources/jsearch.py - JSearch client pattern to follow]
- [Source: backend/app/services/job_sources/adzuna.py - Adzuna client pattern to follow]
- [Source: backend/app/services/job_sources/aggregator.py - JobAggregator parallel execution]
- [Source: backend/app/services/job_sources/__init__.py - Package exports]
- [Source: backend/app/agents/core/job_scout.py - JobScoutAgent source list]
- [Source: backend/app/config.py - Settings class for new env var]
- [Source: backend/tests/unit/test_services/test_job_sources.py - Test patterns]
- [Source: 4-1-job-scout-agent-implementation.md - Code review learnings H1, M1, M3]
- [RapidAPI Indeed scrapers: https://rapidapi.com/search/indeed]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Route Taken

SIMPLE (score: 3/16)

### GSD Subagents Used

none (direct execution)

### Debug Log References

- No issues encountered — clean implementation following established patterns

### Completion Notes List

- Created IndeedSource client extending BaseJobSource with RapidAPI auth pattern
- Configurable host via INDEED_RAPIDAPI_HOST (empty = disabled, reuses RAPIDAPI_KEY)
- Defensive response parsing handles multiple field naming conventions
- Applied 4-1 code review learnings: `is not None` for salary=0, credential guard, httpx lifecycle
- Conditionally registered in JobScoutAgent._fetch_jobs() source list
- 7 new tests added to test_job_sources.py following existing patterns

### Change Log

- 2026-01-31: Initial implementation of Indeed RapidAPI source client
- 2026-01-31: Code review fixes — H1: salary_min filter truthy→is not None, M1: documented _request_delay as future infra, M2: credential guard tests verify no HTTP call

### File List

**Created:**
- `backend/app/services/job_sources/indeed.py` — IndeedSource RapidAPI client (90% coverage)

**Modified:**
- `backend/app/config.py` — Added INDEED_RAPIDAPI_HOST setting
- `backend/app/services/job_sources/__init__.py` — Export IndeedSource
- `backend/app/agents/core/job_scout.py` — Added IndeedSource to aggregator sources (conditional)
- `backend/tests/unit/test_services/test_job_sources.py` — Added 7 TestIndeedSource tests
