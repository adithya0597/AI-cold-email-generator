# Story 7.3: MyVisaJobs Integration

Status: review

## Story

As an **H1B data pipeline**,
I want **to fetch LCA wage and job title data from DOL disclosure files (the same underlying data MyVisaJobs uses)**,
So that **users see average wages, commonly sponsored job titles, and office locations with H1B activity per company**.

## Acceptance Criteria

1. **AC1: LCA wage and job data extraction** — Given the H1B data pipeline runs, when the myvisajobs source fetcher executes, then it parses DOL LCA disclosure data to extract per-company: average wages for sponsored positions, job titles commonly sponsored, and office locations with H1B activity.
2. **AC2: Per-company job title aggregation** — Given LCA data is parsed, when records are grouped by company, then the top 5 most commonly sponsored job titles are captured with counts.
3. **AC3: Per-company location aggregation** — Given LCA data is parsed, when records are grouped by company, then unique worksite states are captured with petition counts per state.
4. **AC4: Data attribution** — Given data is fetched from DOL LCA files, when it is stored in h1b_source_records, then raw_data includes `{"attribution": "Source: DOL LCA Data (MyVisaJobs equivalent)", "source_url": "..."}`.
5. **AC5: Integration with pipeline** — Given the fetch_myvisajobs stub from Story 7-1 exists, when this story is complete, then the stub is replaced with real DOL LCA data fetching that returns a fully populated SourceData object including avg_wage, wage_source, and domain.
6. **AC6: Error resilience** — Given a DOL LCA data fetch fails, when the pipeline continues, then the failure is logged as structured JSON with source="myvisajobs", and the pipeline proceeds with other sources.

## Tasks / Subtasks

- [x] Task 1: Create MyVisaJobs-equivalent data extractor (AC: #1, #2, #3)
  - [x] 1.1 Create `backend/app/services/research/myvisajobs_client.py` with `MyVisaJobsClient` class
  - [x] 1.2 Implement `extract_company_details(records: list[dict], company_key: str) -> CompanyDetails` — extracts wage, job title, and location data for a specific normalized company
  - [x] 1.3 Implement `get_top_job_titles(records: list[dict], limit: int = 5) -> list[tuple[str, int]]` — returns top job titles with counts
  - [x] 1.4 Implement `get_worksite_locations(records: list[dict]) -> dict[str, int]` — returns state → petition count mapping
  - [x] 1.5 Reuse `DOLDisclosureClient.download_disclosure_file()` from Story 7-2 for data download (no duplicate download logic)

- [x] Task 2: Replace fetch_myvisajobs stub (AC: #4, #5, #6)
  - [x] 2.1 Replace `fetch_myvisajobs()` in h1b_service.py with real implementation that calls MyVisaJobsClient
  - [x] 2.2 Map company details to SourceData with avg_wage, wage_source="dol_lca", domain (derive from company name)
  - [x] 2.3 Include raw_data with attribution, source_url, top_job_titles, and worksite_locations
  - [x] 2.4 Add structured JSON error logging on failures
  - [x] 2.5 Return None on failure (pipeline continues)

- [x] Task 3: Write tests (AC: #1-#6)
  - [x] 3.1 Unit tests for `extract_company_details` — wage averaging, job title counting, location counting
  - [x] 3.2 Unit tests for `get_top_job_titles` — top 5 limit, empty records
  - [x] 3.3 Unit tests for `get_worksite_locations` — multiple states, single state
  - [x] 3.4 Integration test for replaced `fetch_myvisajobs` — returns populated SourceData with attribution
  - [x] 3.5 Test error resilience — failure returns None, logs structured error

## Dev Notes

### Architecture Compliance

- **Data Source**: MyVisaJobs.com compiles data from DOL LCA disclosure files. No public API available. This story uses the same DOL LCA data directly, focusing on wage/job title/location fields that MyVisaJobs specializes in.
- **Service location**: New client at `backend/app/services/research/myvisajobs_client.py`, replaces stub in `backend/app/services/research/h1b_service.py`
- **Reuse DOL download**: Reuse `DOLDisclosureClient.download_disclosure_file()` from Story 7-2 — do NOT duplicate download/caching logic
- **CSV columns for MyVisaJobs-equivalent data**: SOC_TITLE (job title), WORKSITE_STATE, WAGE_RATE_OF_PAY_FROM, WAGE_UNIT_OF_PAY, EMPLOYER_NAME

### Existing Patterns to Follow

- **dol_client.py pattern**: `aggregate_by_company()`, `_parse_wage()`, `normalize_company_name()` from h1b_service.py
- **Error handling**: Return None from fetcher on failure (same pattern as fetch_h1bgrader)

### Project Structure Notes

- `backend/app/services/research/myvisajobs_client.py` — NEW file
- `backend/app/services/research/h1b_service.py` — MODIFY to replace fetch_myvisajobs stub
- `backend/tests/unit/test_services/test_myvisajobs_client.py` — NEW test file

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 7, Story 7.3]
- [Source: backend/app/services/research/h1b_service.py — fetch_myvisajobs stub]
- [Source: backend/app/services/research/dol_client.py — DOLDisclosureClient reuse]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Route Taken

SIMPLE (assessed score: 2/16)

### GSD Subagents Used

none (direct execution)

### Debug Log References

- Fixed patch path for MyVisaJobsClient (lazy import requires patching at source module)

### Completion Notes List

- Created MyVisaJobs-equivalent data extractor with company details, job title aggregation, worksite locations
- Reuses DOLDisclosureClient from Story 7-2 for file download
- Replaced fetch_myvisajobs stub with real DOL LCA data fetching
- 11 tests: 3 company details, 3 job titles, 3 locations, 2 integration

### Change Log

- 2026-02-01: Story implemented, all 11 tests passing, no regressions

### File List

#### Files to CREATE
- `backend/app/services/research/myvisajobs_client.py`
- `backend/tests/unit/test_services/test_myvisajobs_client.py`

#### Files to MODIFY
- `backend/app/services/research/h1b_service.py` (replace fetch_myvisajobs stub)
