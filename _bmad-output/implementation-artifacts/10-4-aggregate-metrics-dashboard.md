# Story 10.4: Aggregate Metrics Dashboard

Status: review

## Story

As an **enterprise administrator**,
I want **an aggregate metrics dashboard showing organization-wide employment outcomes without exposing individual employee data**,
So that **I can measure program effectiveness, justify ROI, and make data-driven decisions about workforce deployment**.

## Acceptance Criteria

1. **AC1: Aggregate metrics calculation** — Given the admin requests organization metrics, when the service queries the database, then it returns aggregate-only metrics: enrolled_count, active_count, jobs_reviewed_count, applications_submitted_count, interviews_scheduled_count, placements_count, placement_rate (percentage), avg_time_to_placement_days. All values are computed via COUNT/AVG/SUM grouped by org, never exposing individual user_id values.
2. **AC2: Date range filtering** — Given the admin provides `start_date` and `end_date` query parameters, when the metrics are calculated, then only activity within that date range is included. Default range is last 30 days if no parameters provided.
3. **AC3: Daily granularity** — Given the admin requests metrics, when the data is returned, then a `daily_breakdown` array is included with per-day counts for key metrics (applications, interviews, placements) to support trend visualization.
4. **AC4: No individual data exposure** — Given the metrics service executes queries, when results are assembled, then no query returns individual `user_id`, `user_name`, or any personally identifiable information. All queries use `GROUP BY org_id` aggregation.
5. **AC5: Export capabilities** — Given the admin clicks export, when export is requested, then the API returns metrics data formatted for CSV download (JSON array with headers). PDF export is deferred to a future story.
6. **AC6: Frontend dashboard component** — Given the admin navigates to the metrics dashboard, when the component renders, then it displays: (a) summary metric cards with current values, (b) date range picker, (c) trend chart placeholder, (d) export button. Component is props-based with mock data (real API integration deferred).
7. **AC7: Admin-only access** — Given the metrics endpoint exists, when a non-admin user attempts to access it, then the request is rejected with HTTP 403.
8. **AC8: Audit logging** — Given an admin views or exports metrics, when the action completes, then an audit log entry is created with action "view_metrics" or "export_metrics".

## Tasks / Subtasks

- [x] Task 1: Create EnterpriseMetricsService (AC: #1, #2, #3, #4)
  - [x] 1.1 Create `backend/app/services/enterprise/metrics.py` with `EnterpriseMetricsService` class
  - [x] 1.2 Implement `get_aggregate_metrics(session, org_id, start_date, end_date) -> OrgMetrics` — execute aggregate queries against org member activity
  - [x] 1.3 Implement `_count_enrolled(session, org_id) -> int` — count OrganizationMembers with status accepted
  - [x] 1.4 Implement `_count_active(session, org_id, start_date, end_date) -> int` — count members with any activity in date range
  - [x] 1.5 Implement `_count_jobs_reviewed(session, org_id, start_date, end_date) -> int` — aggregate job review activity across org
  - [x] 1.6 Implement `_count_applications(session, org_id, start_date, end_date) -> int` — aggregate application count
  - [x] 1.7 Implement `_count_interviews(session, org_id, start_date, end_date) -> int` — aggregate interview count
  - [x] 1.8 Implement `_count_placements(session, org_id, start_date, end_date) -> int` and `_calc_placement_rate()` — placement metrics
  - [x] 1.9 Implement `_calc_avg_time_to_placement(session, org_id, start_date, end_date) -> float | None` — average days from enrollment to placement
  - [x] 1.10 Implement `get_daily_breakdown(session, org_id, start_date, end_date) -> list[DailyMetrics]` — per-day counts for trend data
  - [x] 1.11 Verify ALL queries use `GROUP BY` and never return `user_id` in SELECT

- [x] Task 2: Create metrics API endpoint (AC: #1, #2, #5, #7, #8)
  - [x] 2.1 Add `GET /api/v1/admin/metrics` to `backend/app/api/v1/admin.py` — requires `require_admin`
  - [x] 2.2 Accept query params: `start_date` (date, optional), `end_date` (date, optional), `export_format` (str, optional: "csv")
  - [x] 2.3 Default date range: last 30 days if not specified
  - [x] 2.4 If `export_format=csv`, return `StreamingResponse` with CSV content-type and attachment header
  - [x] 2.5 Otherwise return JSON `MetricsResponse` with summary and daily breakdown
  - [x] 2.6 Call `log_audit_event()` with "view_metrics" or "export_metrics" action

- [x] Task 3: Create response schemas (AC: #1, #3)
  - [x] 3.1 Create `OrgMetrics` dataclass/Pydantic model: `enrolled_count`, `active_count`, `jobs_reviewed_count`, `applications_submitted_count`, `interviews_scheduled_count`, `placements_count`, `placement_rate`, `avg_time_to_placement_days`
  - [x] 3.2 Create `DailyMetrics` Pydantic model: `date`, `applications`, `interviews`, `placements`
  - [x] 3.3 Create `MetricsResponse` Pydantic model: `summary` (OrgMetrics), `daily_breakdown` (list of DailyMetrics), `date_range` (start, end)

- [x] Task 4: Create frontend dashboard component (AC: #6)
  - [x] 4.1 Create `frontend/src/components/enterprise/EnterpriseMetricsDashboard.tsx` — props-based component
  - [x] 4.2 Implement metric summary cards displaying all 8 aggregate values with labels and formatting (counts as integers, rate as percentage, time as days)
  - [x] 4.3 Implement date range picker (two date inputs with start/end)
  - [x] 4.4 Implement export button (CSV) that calls `onExport` prop callback
  - [x] 4.5 Add placeholder for trend chart area (div with "Chart coming soon" or simple bar representation)
  - [x] 4.6 Create mock data file `frontend/src/components/enterprise/__fixtures__/mockMetrics.ts` for Storybook/testing

- [x] Task 5: Write tests (AC: #1-#8)
  - [x] 5.1 Create `backend/tests/unit/test_services/test_enterprise_metrics.py`
  - [x] 5.2 Test aggregate metrics returns correct counts with known data
  - [x] 5.3 Test date range filtering excludes out-of-range activity
  - [x] 5.4 Test default date range is last 30 days
  - [x] 5.5 Test no individual user_id appears in any query result
  - [x] 5.6 Test daily breakdown returns correct per-day counts
  - [x] 5.7 Test CSV export format contains correct headers and data
  - [x] 5.8 Test API endpoint requires admin auth
  - [x] 5.9 Test placement_rate calculation (placements / applications * 100)
  - [x] 5.10 Create `frontend/src/components/enterprise/__tests__/EnterpriseMetricsDashboard.test.tsx`
  - [x] 5.11 Test component renders all 8 metric cards with values
  - [x] 5.12 Test date range picker renders and accepts input
  - [x] 5.13 Test export button calls onExport callback

## Dev Notes

### Architecture Compliance

- **Service location**: `backend/app/services/enterprise/metrics.py` — enterprise services directory
- **Query safety**: ALL database queries MUST use `GROUP BY org_id` aggregation. No query may include `user_id` in its SELECT clause. This is the critical privacy requirement for enterprise admin access.
- **API pattern**: Endpoint added to `backend/app/api/v1/admin.py` with `require_admin` dependency
- **CSV export**: Use `StreamingResponse` from FastAPI with `text/csv` content type — no external PDF library needed (PDF deferred)
- **Frontend pattern**: Props-based component following the NetworkDashboard pattern. No direct API calls in the component — data fetching handled by parent page or hook (deferred).
- **Frontend location**: `frontend/src/components/enterprise/` — new enterprise directory for admin components
- **Dependency on 10-1**: Requires `require_admin`, `Organization`, `OrganizationMember`, `log_audit_event()` from story 10-1

### Existing Utilities to Use

- `require_admin` from `app.auth.admin` (story 10-1) — admin authentication
- `log_audit_event()` from `app.services.enterprise.audit` (story 10-1) — audit trail
- `AsyncSessionLocal` from `app.db.engine` — database session
- `AgentActivity` model from `app.db.models` — may be useful as data source for activity counts
- React component patterns from existing dashboard components in `frontend/src/components/`

### Project Structure Notes

- Service: `backend/app/services/enterprise/metrics.py`
- Endpoint: added to `backend/app/api/v1/admin.py`
- Frontend: `frontend/src/components/enterprise/EnterpriseMetricsDashboard.tsx`
- Frontend fixtures: `frontend/src/components/enterprise/__fixtures__/mockMetrics.ts`
- Backend tests: `backend/tests/unit/test_services/test_enterprise_metrics.py`
- Frontend tests: `frontend/src/components/enterprise/__tests__/EnterpriseMetricsDashboard.test.tsx`

### References

- [Source: backend/app/db/models.py — AgentActivity model for activity data source]
- [Source: backend/app/api/v1/admin.py — admin route pattern]
- [Source: backend/app/services/transactional_email.py — service class pattern]
- [Source: frontend/src/components/ — existing React component patterns]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
MODERATE (score: 6/16)

### GSD Subagents Used
- gsd-executor ×1

### Debug Log References
N/A

### Completion Notes List
- EnterpriseMetricsService with aggregate-only queries (GROUP BY org_id, no user_id in SELECT)
- OrgMetrics/DailyMetrics dataclasses with 8 aggregate metrics
- GET /admin/metrics endpoint with date range filtering and CSV export
- EnterpriseMetricsDashboard React component with 8 metric cards, date picker, export button
- Mock data fixtures for testing
- 16 backend + 7 frontend = 23 tests total

### Change Log
- 2026-02-02: Story implemented via MODERATE route

### File List

#### Files to CREATE
- `backend/app/services/enterprise/metrics.py`
- `frontend/src/components/enterprise/EnterpriseMetricsDashboard.tsx`
- `frontend/src/components/enterprise/__fixtures__/mockMetrics.ts`
- `frontend/src/components/enterprise/__tests__/EnterpriseMetricsDashboard.test.tsx`
- `backend/tests/unit/test_services/test_enterprise_metrics.py`

#### Files to MODIFY
- `backend/app/api/v1/admin.py`
