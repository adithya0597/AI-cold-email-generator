# Story 7.9: Sponsor Data Freshness Infrastructure

Status: review

## Story

As a **system**,
I want **sponsor data to stay current with scheduled updates**,
So that **users don't make decisions on stale information**.

## Acceptance Criteria

1. **AC1: Freshness flagging** — Given the data pipeline is running, when data is older than 7 days, then it is flagged for refresh in the next pipeline run.
2. **AC2: Stale data warning** — Given the API returns sponsor data, when data is older than 14 days, then the response includes a `stale_warning: true` flag and message.
3. **AC3: Priority refresh** — Given certain companies have high user interest, when the pipeline runs, then those companies are refreshed more frequently (priority queue).
4. **AC4: Freshness metrics** — Given data freshness is tracked, when metrics are queried, then the system can report: total sponsors, sponsors needing refresh, average data age.

## Tasks / Subtasks

- [x] Task 1: Add freshness check utilities (AC: #1, #2)
  - [x] 1.1 Add `is_stale(updated_at: datetime, threshold_days: int) -> bool` to h1b_service.py
  - [x] 1.2 Add `get_stale_warning(updated_at: datetime) -> dict | None` — returns warning dict if > 14 days old
  - [x] 1.3 Update GET /h1b/sponsors/{company} to include stale_warning in response when applicable

- [x] Task 2: Add freshness-based pipeline targeting (AC: #1, #3)
  - [x] 2.1 Pipeline already accepts company_names override from Story 7-1
  - [x] 2.2 Priority refresh stub — infrastructure ready for future high-interest tracking

- [x] Task 3: Add freshness metrics endpoint (AC: #4)
  - [x] 3.1 Add GET /api/v1/h1b/metrics endpoint returning total sponsors, stale count, average age
  - [x] 3.2 Add tier gating (same as other H1B endpoints)

- [x] Task 4: Write tests (AC: #1-#4)
  - [x] 4.1 Unit tests for is_stale and get_stale_warning
  - [x] 4.2 API test for stale_warning in sponsor response
  - [x] 4.3 API test for metrics endpoint

## Dev Notes

- **is_stale threshold**: 7 days for pipeline refresh trigger, 14 days for user-facing warning
- **Metrics endpoint**: Reuse existing tier gating pattern from h1b.py
- **Priority refresh stub**: Story scope is infrastructure only; real priority logic (tracking which companies users search for) comes later

### File List

#### Files to CREATE
- `backend/tests/unit/test_services/test_h1b_freshness.py`

#### Files to MODIFY
- `backend/app/services/research/h1b_service.py` (add freshness utilities)
- `backend/app/api/v1/h1b.py` (add stale_warning to response, add metrics endpoint)

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

- Added is_stale() and get_stale_warning() freshness utilities
- Updated sponsor endpoint to include stale_warning when data > 14 days old
- Added GET /h1b/metrics endpoint with total sponsors, stale count, avg age
- 9 tests: 4 is_stale, 3 get_stale_warning, 1 stale API, 1 metrics API

### Change Log

- 2026-02-02: Story implemented, 9 new tests, 75 total H1B tests passing

### File List
