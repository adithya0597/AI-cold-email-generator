# Story 7.4: USCIS Public Data Integration

Status: review

## Story

As an **H1B data pipeline**,
I want **to incorporate official USCIS H1B employer data**,
So that **sponsor information is verified against government records with official approval/denial statistics**.

## Acceptance Criteria

1. **AC1: USCIS employer data fetching** — Given the USCIS H1B Employer Data Hub is accessible, when the uscis source fetcher executes, then it downloads and parses USCIS public data to extract per-employer: official approval counts, denial counts, petition counts, and fiscal year data.
2. **AC2: Official data prioritization** — Given USCIS data is available alongside other sources, when aggregation occurs, then USCIS approval/denial stats take priority over H1BGrader and MyVisaJobs equivalents (already handled in aggregate_sources from Story 7-1).
3. **AC3: Data attribution** — Given data is fetched from USCIS, when it is stored in h1b_source_records, then raw_data includes `{"attribution": "Source: USCIS H1B Employer Data Hub", "source_url": "..."}`.
4. **AC4: Integration with pipeline** — Given the fetch_uscis stub from Story 7-1 exists, when this story is complete, then the stub is replaced with real USCIS data fetching that returns a fully populated SourceData object.
5. **AC5: Error resilience** — Given a USCIS data fetch fails, when the pipeline continues, then the failure is logged as structured JSON with source="uscis", and the pipeline proceeds with other sources.

## Tasks / Subtasks

- [x] Task 1: Create USCIS data client (AC: #1)
  - [x] 1.1 Create `backend/app/services/research/uscis_client.py` with `USCISClient` class
  - [x] 1.2 Implement `download_employer_data(fiscal_year: int) -> Path` — downloads USCIS H1B employer data CSV, with caching and retry logic (reuse patterns from DOLDisclosureClient)
  - [x] 1.3 Implement `parse_employer_data(path: Path) -> list[dict]` — parses USCIS employer data CSV
  - [x] 1.4 Implement `get_employer_stats(records: list[dict], company_name: str) -> EmployerStats` — extracts approval/denial counts for a specific employer

- [x] Task 2: Replace fetch_uscis stub (AC: #3, #4, #5)
  - [x] 2.1 Replace `fetch_uscis()` in h1b_service.py with real implementation calling USCISClient
  - [x] 2.2 Map EmployerStats to SourceData with total_petitions, approval_rate, avg_wage, wage_source="uscis_lca"
  - [x] 2.3 Include raw_data with attribution and source_url
  - [x] 2.4 Return None on failure with structured error logging

- [x] Task 3: Write tests (AC: #1-#5)
  - [x] 3.1 Unit tests for `parse_employer_data` — valid CSV, empty file
  - [x] 3.2 Unit tests for `get_employer_stats` — found employer, not found, multiple entries
  - [x] 3.3 Unit tests for `download_employer_data` — cache hit, successful download
  - [x] 3.4 Integration test for replaced `fetch_uscis` — returns populated SourceData with attribution
  - [x] 3.5 Test error resilience — failure returns None

## Dev Notes

### Architecture Compliance

- **Data Source**: USCIS H1B Employer Data Hub provides official government data on H1B petitions. Available as downloadable CSV.
- **Service location**: `backend/app/services/research/uscis_client.py`
- **Reuse patterns**: Follow same download/cache/retry patterns from DOLDisclosureClient
- **Priority**: USCIS data already has highest priority in aggregate_sources() from Story 7-1 — no changes needed to aggregation logic

### Technical Requirements

- **USCIS data columns**: Employer, Initial Approvals, Initial Denials, Continuing Approvals, Continuing Denials, Fiscal Year
- **Company matching**: Use normalize_company_name() for matching employer names

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 7, Story 7.4]
- [Source: backend/app/services/research/h1b_service.py — fetch_uscis stub]
- [Source: backend/app/services/research/dol_client.py — download/cache patterns]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Route Taken

SIMPLE (assessed score: 2/16)

### GSD Subagents Used

none (direct execution)

### Debug Log References

No issues encountered.

### Completion Notes List

- Created USCIS H1B Employer Data Hub client with CSV parsing, employer stats extraction
- Implemented download with 24h caching and 3-retry exponential backoff
- Replaced fetch_uscis stub with real USCIS data fetching
- 8 tests: 2 parsing, 3 employer stats, 1 download, 2 integration

### Change Log

- 2026-02-01: Story implemented, all 8 tests passing, no regressions (66 total)

### File List

#### Files to CREATE
- `backend/app/services/research/uscis_client.py`
- `backend/tests/unit/test_services/test_uscis_client.py`

#### Files to MODIFY
- `backend/app/services/research/h1b_service.py` (replace fetch_uscis stub)
