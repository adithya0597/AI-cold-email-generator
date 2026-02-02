# Story 10.7: ROI Reporting

Status: done

## Story

As an **enterprise admin**,
I want **to view ROI metrics for my organization's career transition program and schedule automated monthly reports**,
So that **I can demonstrate program value to executives and justify continued investment**.

## Acceptance Criteria

1. **AC1: ROI metric computation** — Given the ROIReportService is called, when it computes metrics for a date range, then it returns: cost per placement, time-to-placement (average days from enrollment to placed status), engagement rate (active users / total enrolled), and employee satisfaction score (aggregate from feedback). All metrics use aggregate queries only — no individual user data exposed.

2. **AC2: Benchmark comparison** — Given ROI metrics are computed, when time-to-placement is returned, then it includes a comparison against configurable benchmarks (default: industry average 90 days for traditional outplacement). Engagement rate is compared against traditional outplacement benchmark (default: 35%).

3. **AC3: Date range filtering** — Given the ROI report endpoint is called, when `start_date` and `end_date` query parameters are provided, then metrics are computed for that date range only. Defaults to current calendar month if not specified.

4. **AC4: Monthly report scheduling** — Given an admin configures a monthly report schedule, when the schedule is saved, then the report configuration (recipients, date range type, enabled flag) is stored in Organization.settings JSONB under the key `roi_report_schedule`.

5. **AC5: Report dashboard rendering** — Given the ROIReportDashboard component receives report data, when it renders, then it displays: cost per placement card, time-to-placement with benchmark bar, engagement rate with benchmark comparison, satisfaction score, and an export button placeholder.

6. **AC6: Privacy-safe aggregation** — Given ROI metrics are computed, when queries run, then they use only COUNT, AVG, and SUM aggregations. No individual user records are returned or logged.

7. **AC7: RBAC enforcement** — Given a non-admin user calls the ROI report endpoints, when the request is processed, then it returns 403 Forbidden.

## Tasks / Subtasks

- [x] Task 1: Create ROIReportService (AC: #1, #2, #3, #6)
  - [x] 1.1 Create `backend/app/services/enterprise/roi_report.py` with `ROIReportService` class
  - [x] 1.2 Implement `compute_metrics(org_id: str, start_date: date, end_date: date)` — returns dict with cost_per_placement, time_to_placement_days, engagement_rate, satisfaction_score
  - [x] 1.3 Implement `_compute_cost_per_placement(org_id, start_date, end_date)` — total program cost (seats * price) / number of placements in period
  - [x] 1.4 Implement `_compute_time_to_placement(org_id, start_date, end_date)` — AVG days between user enrollment_date and placed_date for users placed in period
  - [x] 1.5 Implement `_compute_engagement_rate(org_id, start_date, end_date)` — COUNT(users with login in period) / COUNT(total enrolled users)
  - [x] 1.6 Implement `_compute_satisfaction_score(org_id, start_date, end_date)` — AVG of satisfaction ratings from feedback (stub returning placeholder if no feedback table exists yet)
  - [x] 1.7 Implement `add_benchmarks(metrics: dict)` — add benchmark comparisons (industry defaults stored as class constants, org overrides from Organization.settings)

- [x] Task 2: Create API endpoints (AC: #3, #4, #7)
  - [x] 2.1 Add ROI report routes to `backend/app/api/v1/admin_enterprise.py` (or create if not yet created by 10-6)
  - [x] 2.2 Implement `GET /api/v1/admin/reports/roi` — accepts `start_date`, `end_date` query params, returns computed metrics with benchmarks
  - [x] 2.3 Implement `POST /api/v1/admin/reports/roi/schedule` — accepts schedule config (recipients list, enabled boolean), stores in Organization.settings["roi_report_schedule"]
  - [x] 2.4 Implement `GET /api/v1/admin/reports/roi/schedule` — returns current schedule config
  - [x] 2.5 Add RBAC dependency (reuse from 10-6 if available)

- [x] Task 3: Create ROIReportDashboard frontend component (AC: #5)
  - [x] 3.1 Create `frontend/src/components/enterprise/ROIReportDashboard.tsx` with TypeScript + Tailwind
  - [x] 3.2 Implement metric cards: cost per placement, time-to-placement, engagement rate, satisfaction score
  - [x] 3.3 Implement benchmark comparison bars (colored: green if better than benchmark, amber if within 10%, red if worse)
  - [x] 3.4 Implement date range selector (start/end date inputs)
  - [x] 3.5 Implement export button placeholder (prints to PDF via browser `window.print()`)
  - [x] 3.6 Implement schedule configuration toggle with recipient email inputs

- [x] Task 4: Write tests (AC: #1-#7)
  - [x] 4.1 Create `backend/tests/unit/test_services/test_roi_report.py`
  - [x] 4.2 Test cost_per_placement computation with known data
  - [x] 4.3 Test time_to_placement computation returns average days
  - [x] 4.4 Test engagement_rate computation with active and inactive users
  - [x] 4.5 Test benchmark comparison adds correct comparison data
  - [x] 4.6 Test date range filtering limits query scope
  - [x] 4.7 Test schedule creation stores config in Organization.settings
  - [x] 4.8 Test non-admin user receives 403 Forbidden
  - [x] 4.9 Create `frontend/src/__tests__/ROIReportDashboard.test.tsx`
  - [x] 4.10 Test dashboard renders all four metric cards
  - [x] 4.11 Test benchmark bars show correct color coding
  - [x] 4.12 Test export button is present

## Dev Notes

### Architecture Compliance

- **Service location**: `backend/app/services/enterprise/roi_report.py` — enterprise services in `enterprise/` subdirectory
- **API location**: Routes added to `backend/app/api/v1/admin_enterprise.py` alongside other enterprise admin routes
- **Frontend location**: `frontend/src/components/enterprise/ROIReportDashboard.tsx` — enterprise components in `enterprise/` subdirectory
- **No PDF library**: V1 generates HTML report that can be printed to PDF via browser's `window.print()`. No server-side PDF generation.
- **Privacy-safe aggregation**: All queries use COUNT, AVG, SUM only. No individual user data in report responses.
- **Schedule storage**: Store schedule config in Organization.settings JSONB field under key `roi_report_schedule` — avoids new table for V1
- **Benchmark defaults**: Industry benchmarks stored as class constants (TIME_TO_PLACEMENT_BENCHMARK = 90 days, ENGAGEMENT_RATE_BENCHMARK = 0.35). Org can override in Organization.settings["benchmarks"].

### Existing Utilities to Use

- `get_current_user_id()` from `app/auth/clerk.py` — JWT authentication
- `TimestampMixin`, `SoftDeleteMixin` from `app/db/models.py` — model mixins
- Organization model (from story 10-1) — settings JSONB field for schedule and benchmark storage
- RBAC dependency (from story 10-6 or 10-2) — admin role check

### Project Structure Notes

- Service file: `backend/app/services/enterprise/roi_report.py`
- API routes: added to `backend/app/api/v1/admin_enterprise.py`
- Frontend component: `frontend/src/components/enterprise/ROIReportDashboard.tsx`
- Backend test file: `backend/tests/unit/test_services/test_roi_report.py`
- Frontend test file: `frontend/src/__tests__/ROIReportDashboard.test.tsx`

### References

- [Source: backend/app/db/models.py — User model, AgentOutput model with JSONB data]
- [Source: backend/app/auth/clerk.py — get_current_user_id() authentication dependency]
- [Source: backend/app/api/v1/admin.py — Existing admin routes pattern]
- [Source: frontend/src/components/network/NetworkDashboard.tsx — Dashboard UI pattern reference]
- [Dependency: Story 10-1 — Organization model with settings JSONB]
- [Dependency: Story 10-2 — RBAC / admin role enforcement]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Route Taken

Sequential 4-task execution: service -> API -> frontend -> tests. All tasks completed autonomously with no deviations or blockers.

### GSD Subagents Used

None (single-agent execution)

### Debug Log References

No debug issues encountered. All tests passed on first run.

### Completion Notes List

- satisfaction_score stubs to None until feedback table is implemented
- Benchmark comparison uses 10% threshold for at_benchmark classification
- Cost per placement uses seat_cost_monthly from org settings (default $500)
- Schedule config stored in Organization.settings["roi_report_schedule"] JSONB

### Change Log

- 01c7b1d: feat(10-7): create ROIReportService with aggregate metrics and benchmarks
- f3d75b0: feat(10-7): add ROI report API endpoints with RBAC enforcement
- 1c188f8: feat(10-7): create ROIReportDashboard frontend component
- 0b4f788: test(10-7): add ROI report backend and frontend tests (32 backend + 12 frontend)

### File List

#### Files to CREATE
- `backend/app/services/enterprise/roi_report.py`
- `frontend/src/components/enterprise/ROIReportDashboard.tsx`
- `backend/tests/unit/test_services/test_roi_report.py`
- `frontend/src/__tests__/ROIReportDashboard.test.tsx`

#### Files to MODIFY
- `backend/app/api/v1/admin_enterprise.py`
- `backend/app/api/v1/router.py` (if not already registered by 10-6)
