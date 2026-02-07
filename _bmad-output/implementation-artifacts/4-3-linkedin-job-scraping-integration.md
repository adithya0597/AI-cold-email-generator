# Story 4.3: LinkedIn Job Scraping Integration

Status: done

## Story

As a **Job Scout Agent**,
I want **to fetch jobs from LinkedIn via a RapidAPI-hosted LinkedIn job scraper endpoint**,
so that **users see opportunities from the world's largest professional network**.

## Acceptance Criteria

1. **AC1 - LinkedIn Source Client:** Given LinkedIn integration is configured with a valid `LINKEDIN_RAPIDAPI_HOST` setting, when the agent searches for jobs matching user preferences, then jobs are fetched via the LinkedIn RapidAPI scraper endpoint following the same `BaseJobSource` pattern as JSearch, Adzuna, and Indeed.

2. **AC2 - Rate Limiting:** Given LinkedIn requests are being made, when multiple queries execute, then a configurable delay (`request_delay`, default 2.0 seconds — higher than Indeed's 1.0s due to stricter LinkedIn anti-scraping) is respected between paginated API calls, implemented via `asyncio.sleep()`.

3. **AC3 - Data Mapping:** Given raw LinkedIn API response data, when parsing occurs, then job data includes: title, company, location, description, posted date, URL — all mapped to existing `RawJob` dataclass fields. LinkedIn-specific fields (applicant_count, company_size) are preserved in `raw_data`.

4. **AC4 - Deduplication Compatibility:** Given LinkedIn jobs are fetched, when they pass through the existing `job_dedup.upsert_jobs()` pipeline, then duplicate jobs (same URL or same title+company+location) are correctly detected and skipped — no changes to dedup logic needed.

5. **AC5 - Graceful Degradation:** Given the LinkedIn API is unavailable, misconfigured, or returns errors, when the agent runs, then errors are logged but do NOT stop the entire batch — other sources (JSearch, Adzuna, Indeed) continue to work via the existing `JobAggregator` parallel execution pattern.

6. **AC6 - Aggregator Registration:** Given the `LinkedInSource` client is implemented, when the `JobScoutAgent` builds its source list, then LinkedIn is included as a fourth source in the `JobAggregator`, gated by whether `LINKEDIN_RAPIDAPI_HOST` is configured (non-empty).

7. **AC7 - Test Coverage:** Given the LinkedIn source client is implemented, when tests run, then unit tests cover: successful search, empty results, API error handling, rate limiting behavior, response parsing with various field completeness, and missing credentials skip — following the same test patterns established in `test_job_sources.py`.

## Tasks / Subtasks

- [x] Task 1: Create LinkedIn RapidAPI source client (AC: #1, #3)
  - [x]1.1: Create `backend/app/services/job_sources/linkedin.py` implementing `LinkedInSource(BaseJobSource)` with `search()` method
  - [x]1.2: Use `httpx.AsyncClient` for HTTP calls with `X-RapidAPI-Key` and `X-RapidAPI-Host` headers (same auth pattern as JSearch/Indeed)
  - [x]1.3: Implement `_parse_response(data)` mapping LinkedIn API fields to `RawJob` (title, company, location, description, url, posted_at). Preserve LinkedIn-specific fields (applicant_count, company_size, company_url) in `raw_data`
  - [x]1.4: Handle missing/optional fields gracefully (salary rarely available on LinkedIn, remote status may need inference)

- [x] Task 2: Implement rate limiting (AC: #2)
  - [x]2.1: Add `request_delay` parameter to `LinkedInSource.__init__()` (default 2.0 seconds — more conservative than Indeed)
  - [x]2.2: Store `_request_delay` for future pagination support (same pattern as IndeedSource)

- [x] Task 3: Add configuration settings (AC: #1, #6)
  - [x]3.1: Add `LINKEDIN_RAPIDAPI_HOST: str = ""` to `config.py` Settings class (empty = disabled)
  - [x]3.2: The existing `RAPIDAPI_KEY` setting is reused for auth (same RapidAPI account)

- [x] Task 4: Register LinkedIn in aggregator (AC: #5, #6)
  - [x]4.1: Update `backend/app/services/job_sources/__init__.py` to export `LinkedInSource`
  - [x]4.2: Update `JobScoutAgent._fetch_jobs()` in `backend/app/agents/core/job_scout.py` to include `LinkedInSource` in the aggregator's source list, gated by `settings.LINKEDIN_RAPIDAPI_HOST` being non-empty
  - [x]4.3: Verify `JobAggregator` graceful degradation handles LinkedIn failures without affecting other sources (already implemented, just verify)

- [x] Task 5: Write tests (AC: #4, #7)
  - [x]5.1: Add `TestLinkedInSource` class to `backend/tests/unit/test_services/test_job_sources.py` following the existing `TestIndeedSource` pattern
  - [x]5.2: Test successful search with mocked httpx response
  - [x]5.3: Test empty results / no jobs returned
  - [x]5.4: Test API error (HTTP 429, 500) returns empty list, logs error
  - [x]5.5: Test missing credentials (empty host) returns empty list immediately — verify no HTTP call made
  - [x]5.6: Test response parsing with partial fields (no salary, no location, no date)
  - [x]5.7: Verify existing dedup tests pass unchanged (LinkedIn jobs go through same pipeline)

## Dev Notes

### Architecture Compliance

**CRITICAL - Follow these patterns from Stories 4-1 and 4-2 EXACTLY:**

1. **BaseJobSource Extension:** `LinkedInSource` MUST extend `BaseJobSource` from `app.services.job_sources.base`. Override `search(query, location, filters) -> list[RawJob]`. Return empty list on any failure — never raise exceptions.
   [Source: backend/app/services/job_sources/base.py]

2. **Client Pattern:** Follow the EXACT same pattern as `IndeedSource` (newest, most refined):
   - Accept optional `client: httpx.AsyncClient` for dependency injection in tests
   - Create client in `search()` if none injected, close after use
   - Use `try/except` around all HTTP calls, return `[]` on failure
   - Log errors via `logger.error()`, log success counts via `logger.info()`
   [Source: backend/app/services/job_sources/indeed.py]

3. **RapidAPI Auth Pattern:** Use the SAME auth mechanism as JSearch/Indeed — `X-RapidAPI-Key` header with `settings.RAPIDAPI_KEY`. Add `X-RapidAPI-Host` header set to `settings.LINKEDIN_RAPIDAPI_HOST`.
   [Source: backend/app/services/job_sources/indeed.py:70-73]

4. **No Direct LinkedIn Scraping:** LinkedIn does NOT have a free public job search API. LinkedIn's official API requires partner-level approval. Use a RapidAPI-hosted LinkedIn job scraper endpoint instead. The specific host will be configured via `LINKEDIN_RAPIDAPI_HOST` env var so it can be swapped between providers.
   [Source: architecture.md line 71 — "LinkedIn ToS: No automation on LinkedIn platform"]
   [Note: RapidAPI providers handle LinkedIn scraping compliance — we consume their API, not scrape directly]

5. **Aggregator Integration:** The `JobAggregator` already handles parallel execution with per-source timeouts and graceful degradation. Just add `LinkedInSource` to the sources list — no aggregator changes needed.
   [Source: backend/app/services/job_sources/aggregator.py]

6. **Dedup Compatibility:** LinkedIn jobs flow through the existing `job_dedup.upsert_jobs()` pipeline. The `RawJob.url` field enables URL-based dedup. Content-based dedup (title+company+location) handles cross-source duplicates. No dedup changes needed.
   [Source: backend/app/services/job_dedup.py]

### Technical Requirements

**LinkedIn RapidAPI Integration:**
```python
# Auth: X-RapidAPI-Key + X-RapidAPI-Host headers
# Host: configurable via LINKEDIN_RAPIDAPI_HOST setting
# Key params typically: keywords, location_id/geo_id, date_posted, sort_by
# Response: varies by provider — parse defensively
#
# Example providers on RapidAPI:
# - "linkedin-jobs-scraper-api1.p.rapidapi.com"
# - "linkedin-data-api.p.rapidapi.com"
# - "linkedin-api8.p.rapidapi.com"
#
# The implementation should be provider-agnostic:
# parse response as list of dicts, map known fields, skip unknowns
```

**LinkedInSource Class Structure:**
```python
class LinkedInSource(BaseJobSource):
    source_name = "linkedin"

    def __init__(
        self,
        api_key: str | None = None,
        host: str | None = None,
        timeout: float = 30.0,
        request_delay: float = 2.0,  # More conservative than Indeed
        client: httpx.AsyncClient | None = None,
    ):
        self._api_key = api_key or settings.RAPIDAPI_KEY
        self._host = host or settings.LINKEDIN_RAPIDAPI_HOST
        self._timeout = timeout
        self._request_delay = request_delay  # Reserved for future pagination support
        self._client = client
```

**Config Addition:**
```python
# In Settings class in config.py:
LINKEDIN_RAPIDAPI_HOST: str = ""  # Empty = disabled
```

**LinkedIn-Specific Response Parsing Notes:**
- LinkedIn responses often include `applicantCount`, `companySize`, `companyUrl` — store these in `raw_data`
- Salary is RARELY included on LinkedIn job postings — leave `salary_min`/`salary_max` as None when absent
- Remote status: check for `workplaceType` or `remoteAllowed` fields, fallback to inferring from title/location
- Posted date: LinkedIn often uses relative strings ("2 days ago") or ISO dates — handle both
- URLs: LinkedIn job URLs typically follow `https://www.linkedin.com/jobs/view/{id}` pattern
- Field naming varies across RapidAPI providers — use defensive multi-name lookups (same pattern as IndeedSource)

### Previous Story Intelligence (4-2)

**Key learnings from Story 4-2 implementation and code review that MUST be applied:**

1. **H1 (salary_min filter truthy check):** In search() filter handling, use `if salary_min is not None:` instead of `if salary_min:` to correctly handle salary=0. This was caught in 4-2 code review.
   [Source: Code review fix H1 — backend/app/services/job_sources/indeed.py:67]

2. **H1 from 4-1 (salary_min=0 parse bug):** In `_parse_response()`, use `if item.get("salary_min") is not None:` instead of `if item.get("salary_min"):` to correctly handle salary=0.
   [Source: Code review fix H1 from 4-1]

3. **M1 (missing API key guard):** ALWAYS check credentials at the top of `search()`:
   ```python
   if not self._api_key or not self._host:
       logger.warning("LinkedIn API credentials not configured, skipping")
       return []
   ```
   [Source: Code review fix M1 — all source clients have this pattern]

4. **M3 (httpx client lifecycle):** Use the injected client OR create+close pattern:
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

5. **M2 (credential guard tests):** Tests for missing credentials MUST verify no HTTP call is made (use `patch` + `assert_not_called()`).
   [Source: Code review fix M2 — backend/tests/unit/test_services/test_job_sources.py]

6. **Test mocking pattern:** Use `patch("app.services.job_sources.linkedin.httpx.AsyncClient")` with `AsyncMock` — follow the exact pattern in `TestIndeedSource`.
   [Source: backend/tests/unit/test_services/test_job_sources.py]

### Library/Framework Requirements

**No new dependencies needed:**
- `httpx` — already installed (used by JSearch, Adzuna, Indeed)
- All other dependencies (SQLAlchemy, Redis, pytest) already present

**New environment variable:**
- `LINKEDIN_RAPIDAPI_HOST` — host for the LinkedIn RapidAPI endpoint

### File Structure Requirements

**Files to CREATE:**
```
backend/app/services/job_sources/linkedin.py    # LinkedInSource client
```

**Files to MODIFY:**
```
backend/app/config.py                                    # Add LINKEDIN_RAPIDAPI_HOST
backend/app/services/job_sources/__init__.py             # Export LinkedInSource
backend/app/agents/core/job_scout.py                     # Add LinkedInSource to aggregator sources
backend/tests/unit/test_services/test_job_sources.py     # Add TestLinkedInSource tests
```

**Files to NOT TOUCH:**
```
backend/app/services/job_sources/base.py       # BaseJobSource is stable
backend/app/services/job_sources/jsearch.py    # JSearch client is stable
backend/app/services/job_sources/adzuna.py     # Adzuna client is stable
backend/app/services/job_sources/indeed.py     # Indeed client is stable
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
  - Mock HTTP responses using `AsyncMock` with `patch` (same pattern as existing Indeed tests)
  - Do NOT make real API calls
  - Do NOT mock database — this story only creates `RawJob` objects, DB interaction is handled by existing pipeline
- **Test File:** Add to existing `backend/tests/unit/test_services/test_job_sources.py`
- **Key Test Scenarios:**
  - Happy path: LinkedIn returns jobs, correctly parsed to RawJob list
  - Empty results: API returns empty array, returns `[]`
  - API error (429, 500): returns `[]`, logs error
  - Missing credentials: returns `[]` immediately without HTTP call (verified via mock assert)
  - Partial fields: salary missing, location missing — parsed gracefully
  - LinkedIn-specific: applicant_count and company_size stored in raw_data

### Project Structure Notes

- `linkedin.py` goes in `backend/app/services/job_sources/` alongside `jsearch.py`, `adzuna.py`, `indeed.py`
- Tests go in the existing `test_job_sources.py` file — do NOT create a separate test file
- Follow exact naming convention: `LinkedInSource` class, `source_name = "linkedin"`, source field in RawJob = `"linkedin"`

### References

- [Source: _bmad-output/planning-artifacts/epics.md - Epic 4, Story 4.3]
- [Source: _bmad-output/planning-artifacts/architecture.md - LinkedIn ToS constraints (line 71)]
- [Source: backend/app/services/job_sources/base.py - BaseJobSource ABC and RawJob dataclass]
- [Source: backend/app/services/job_sources/indeed.py - IndeedSource client pattern to follow (most recent)]
- [Source: backend/app/services/job_sources/jsearch.py - JSearch client pattern reference]
- [Source: backend/app/services/job_sources/aggregator.py - JobAggregator parallel execution]
- [Source: backend/app/services/job_sources/__init__.py - Package exports]
- [Source: backend/app/agents/core/job_scout.py - JobScoutAgent source list]
- [Source: backend/app/config.py - Settings class for new env var]
- [Source: backend/tests/unit/test_services/test_job_sources.py - Test patterns]
- [Source: 4-2-indeed-job-board-integration.md - Code review learnings H1, M1, M2, M3]
- [RapidAPI LinkedIn scrapers: https://rapidapi.com/search/linkedin]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Route Taken

SIMPLE (score: 3/16)

### GSD Subagents Used

none (direct execution)

### Debug Log References

- No issues encountered — clean implementation following established patterns from 4-2

### Completion Notes List

- Created LinkedInSource client extending BaseJobSource with RapidAPI auth pattern
- Configurable host via LINKEDIN_RAPIDAPI_HOST (empty = disabled, reuses RAPIDAPI_KEY)
- Defensive response parsing handles multiple field naming conventions and LinkedIn-specific fields
- Applied all code review learnings from 4-1 and 4-2: `is not None` for salary=0, credential guard, httpx lifecycle, credential guard test assertions
- LinkedIn-specific fields (applicantCount, companyUrl, workplaceType) preserved in raw_data
- Remote status inferred from workplaceType field
- Conditionally registered in JobScoutAgent._fetch_jobs() source list
- 7 new tests added to test_job_sources.py following IndeedSource patterns

### Change Log

- 2026-01-31: Initial implementation of LinkedIn RapidAPI source client
- 2026-01-31: Code review fix — H1: hybrid workplace should not be classified as remote

### File List

**Created:**
- `backend/app/services/job_sources/linkedin.py` — LinkedInSource RapidAPI client (84% coverage)

**Modified:**
- `backend/app/config.py` — Added LINKEDIN_RAPIDAPI_HOST setting
- `backend/app/services/job_sources/__init__.py` — Export LinkedInSource
- `backend/app/agents/core/job_scout.py` — Added LinkedInSource to aggregator sources (conditional)
- `backend/tests/unit/test_services/test_job_sources.py` — Added 7 TestLinkedInSource tests
