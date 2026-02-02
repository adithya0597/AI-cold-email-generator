# Story 7.2: H1BGrader Integration

Status: review

## Story

As an **H1B data pipeline**,
I want **to fetch sponsor data from the DOL H1B public disclosure files (the same underlying data that H1BGrader uses)**,
So that **users see approval rates, petition history, and sponsorship trends per company**.

## Acceptance Criteria

1. **AC1: DOL disclosure data fetching** — Given the H1B data pipeline runs, when the h1bgrader source fetcher executes, then it downloads and parses the DOL H1B public disclosure CSV files (LCA data) to extract per-company petition counts, approval/denial rates, and wage data.
2. **AC2: Rate limiting and caching** — Given the DOL data source is accessed, when fetching occurs, then downloads are cached locally (one download per pipeline run max), and the fetcher implements retry logic with exponential backoff for transient failures.
3. **AC3: Data attribution** — Given data is fetched from DOL disclosure files, when it is stored in h1b_source_records, then raw_data includes `{"attribution": "Source: DOL H1B Disclosure Data (H1BGrader equivalent)", "source_url": "..."}` and schema_version is set appropriately.
4. **AC4: Historical trend calculation** — Given multi-year DOL data is available, when processing a company's records, then the fetcher calculates a historical trend (increasing/decreasing/stable) based on year-over-year petition counts.
5. **AC5: Integration with pipeline** — Given the fetch_h1bgrader stub from Story 7-1 exists, when this story is complete, then the stub is replaced with real DOL data fetching that returns a fully populated SourceData object.
6. **AC6: Error resilience** — Given a DOL data fetch fails, when the pipeline continues, then the failure is logged as structured JSON with source="h1bgrader", and the pipeline proceeds with other sources.

## Tasks / Subtasks

- [x] Task 1: Create DOL disclosure data client (AC: #1, #2)
  - [x] 1.1 Create `backend/app/services/research/dol_client.py` with `DOLDisclosureClient` class
  - [x] 1.2 Implement `download_disclosure_file(fiscal_year: int) -> Path` — downloads CSV from DOL public URL, caches in temp dir, returns local path
  - [x] 1.3 Implement retry logic with exponential backoff (3 retries, 1s/2s/4s delays) using httpx
  - [x] 1.4 Implement `parse_disclosure_csv(path: Path) -> list[dict]` — reads CSV, extracts relevant columns (employer_name, case_status, wage_rate_of_pay, etc.)
  - [x] 1.5 Implement local file caching: skip download if cached file is < 24h old

- [x] Task 2: Create company aggregator for DOL data (AC: #1, #4)
  - [x] 2.1 Implement `aggregate_by_company(records: list[dict]) -> dict[str, CompanyStats]` — groups DOL records by normalized company name
  - [x] 2.2 Calculate per-company: total_petitions, approved_count, denied_count, withdrawn_count, approval_rate
  - [x] 2.3 Calculate avg_wage from wage_rate_of_pay fields (handle hourly vs annual conversion)
  - [x] 2.4 Implement `calculate_trend(current_year_petitions: int, prev_year_petitions: int) -> str` — returns "increasing"/"decreasing"/"stable" (±10% threshold)

- [x] Task 3: Replace fetch_h1bgrader stub (AC: #3, #5, #6)
  - [x] 3.1 Replace `fetch_h1bgrader()` in h1b_service.py with real implementation that calls DOLDisclosureClient
  - [x] 3.2 Map DOL CompanyStats to SourceData with proper fields (total_petitions, approval_rate, avg_wage)
  - [x] 3.3 Include full raw_data with attribution, source_url, and trend data
  - [x] 3.4 Add structured JSON error logging on fetch/parse failures
  - [x] 3.5 Ensure function returns None on failure (pipeline continues)

- [x] Task 4: Write tests (AC: #1-#6)
  - [x] 4.1 Unit tests for `parse_disclosure_csv` — valid CSV, malformed rows, empty file
  - [x] 4.2 Unit tests for `aggregate_by_company` — multiple companies, single company, normalization dedup
  - [x] 4.3 Unit tests for `calculate_trend` — increasing (>10%), decreasing (<-10%), stable
  - [x] 4.4 Unit tests for `download_disclosure_file` — mocked httpx responses (success, retry on failure, cache hit)
  - [x] 4.5 Integration test for replaced `fetch_h1bgrader` — returns populated SourceData with attribution
  - [x] 4.6 Test error resilience — DOL fetch failure returns None, logs structured error

## Dev Notes

### Architecture Compliance

- **DOL Data Source**: H1BGrader.com explicitly prohibits scraping in their Terms of Service and has no public API. However, H1BGrader's data comes from the same DOL/USCIS public disclosure files that are freely available. This story uses the DOL H1B disclosure data directly — the same underlying data source.
- **DOL Public Data URL**: `https://www.dol.gov/agencies/eta/foreign-labor/performance` — CSV files available by fiscal year
- **Service location**: New client at `backend/app/services/research/dol_client.py`, replaces stub in `backend/app/services/research/h1b_service.py`
- **No scraping**: This integration uses publicly available CSV downloads, not web scraping
- **Cache location**: Use system temp dir for downloaded CSVs (not in project directory)
- **Existing patterns**: Follow the same async/await pattern used in h1b_service.py, lazy imports for heavy deps

### Technical Requirements

- **CSV columns of interest**: EMPLOYER_NAME, CASE_STATUS (Certified/Denied/Withdrawn), WAGE_RATE_OF_PAY_FROM, WAGE_UNIT_OF_PAY (Year/Hour), SOC_TITLE, WORKSITE_STATE
- **Wage normalization**: Convert hourly wages to annual (hourly × 2080), handle comma-formatted numbers
- **Company name matching**: Use `normalize_company_name()` from h1b_service.py for grouping
- **httpx for downloads**: Use httpx (already in project deps) with async streaming for large CSV files
- **File size consideration**: DOL disclosure files can be 100-200MB — use streaming CSV reader, do NOT load entire file into memory

### Existing Patterns to Follow

- **h1b_service.py pattern**: SourceData dataclass, normalize_company_name(), structured logging
- **Error handling**: Return None from fetcher on failure (same pattern as other source fetchers in h1b_service.py)
- **Celery task integration**: fetch_h1bgrader is called from run_h1b_pipeline() — no changes needed to the pipeline orchestration

### Project Structure Notes

- `backend/app/services/research/dol_client.py` — NEW file for DOL data client
- `backend/app/services/research/h1b_service.py` — MODIFY to replace fetch_h1bgrader stub
- `backend/tests/unit/test_services/test_dol_client.py` — NEW test file
- `backend/tests/unit/test_services/test_h1b_service.py` — MODIFY to update fetch_h1bgrader tests

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 7, Story 7.2]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 1843-1852 (H1BGrader integration)]
- [Source: backend/app/services/research/h1b_service.py — fetch_h1bgrader stub]
- [Source: DOL public disclosure data — https://www.dol.gov/agencies/eta/foreign-labor/performance]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Route Taken

SIMPLE (assessed score: 2/16)

### GSD Subagents Used

none (direct execution)

### Debug Log References

- Fixed mock setup for async streaming in download tests (aiter_bytes needed async generator)
- Fixed patch path for DOLDisclosureClient (lazy import requires patching at source module)

### Completion Notes List

- Created DOL disclosure data client with CSV parsing, company aggregation, trend calculation
- Implemented download with 24h caching and 3-retry exponential backoff
- Replaced fetch_h1bgrader stub with real DOL data fetching
- Attribution included in raw_data for all records
- 18 tests: 3 CSV parsing, 5 aggregation, 5 trend, 3 download, 2 integration

### Change Log

- 2026-02-01: Story implemented, all 18 tests passing, no regressions (29 existing tests still pass)

### File List

#### Files to CREATE
- `backend/app/services/research/dol_client.py`
- `backend/tests/unit/test_services/test_dol_client.py`

#### Files to MODIFY
- `backend/app/services/research/h1b_service.py` (replace fetch_h1bgrader stub)
- `backend/tests/unit/test_services/test_h1b_service.py` (update fetch_h1bgrader tests)
