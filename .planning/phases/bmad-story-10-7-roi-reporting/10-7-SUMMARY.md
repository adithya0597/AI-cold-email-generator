---
phase: bmad-10
plan: 10-7
subsystem: enterprise-admin
tags: [roi, metrics, benchmarks, reporting, enterprise]
dependency-graph:
  requires: [10-1, 10-2]
  provides: [roi-metrics-api, roi-dashboard, benchmark-comparison]
  affects: []
tech-stack:
  added: []
  patterns: [aggregate-only-queries, jsonb-settings-storage, props-based-dashboard]
key-files:
  created:
    - backend/app/services/enterprise/roi_report.py
    - frontend/src/components/enterprise/ROIReportDashboard.tsx
    - backend/tests/unit/test_services/test_roi_report.py
    - frontend/src/__tests__/ROIReportDashboard.test.tsx
  modified:
    - backend/app/api/v1/admin_enterprise.py
decisions:
  - satisfaction_score stubs to None until feedback table exists
  - 10% threshold for at_benchmark classification in comparisons
  - seat_cost_monthly default $500 from org settings for cost calculation
metrics:
  duration: ~5 min
  completed: 2026-02-02
---

# Story 10-7: ROI Reporting Summary

ROIReportService with 4 aggregate metrics (cost_per_placement, time_to_placement, engagement_rate, satisfaction_score), configurable benchmark comparison, schedule storage in Organization.settings JSONB, and React dashboard with metric cards, benchmark bars, date picker, and window.print() export.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create ROIReportService | 01c7b1d | backend/app/services/enterprise/roi_report.py |
| 2 | Create API endpoints | f3d75b0 | backend/app/api/v1/admin_enterprise.py |
| 3 | Create ROIReportDashboard | 1c188f8 | frontend/src/components/enterprise/ROIReportDashboard.tsx |
| 4 | Write tests | 0b4f788 | test_roi_report.py, ROIReportDashboard.test.tsx |

## Acceptance Criteria Verification

- [x] AC1: ROI metric computation -- cost_per_placement, time_to_placement_days, engagement_rate, satisfaction_score using aggregate queries
- [x] AC2: Benchmark comparison -- configurable defaults (90 days, 35%), org overrides via settings["benchmarks"]
- [x] AC3: Date range filtering -- defaults to current calendar month, accepts start_date/end_date
- [x] AC4: Monthly report scheduling -- stored in Organization.settings["roi_report_schedule"]
- [x] AC5: ROIReportDashboard -- 4 metric cards, benchmark bars, date picker, export button, schedule toggle
- [x] AC6: Privacy-safe -- COUNT/AVG/SUM only, no individual user data in responses
- [x] AC7: RBAC enforcement -- all 3 endpoints use require_admin dependency

## Decisions Made

1. **Satisfaction score stub**: Returns None until feedback table is implemented. Benchmark comparison returns "no_data" for None values.
2. **Benchmark threshold**: 10% band around benchmark value classifies as "at_benchmark". Outside band is "better" or "worse".
3. **Cost calculation**: Uses enrolled_members * seat_cost_monthly / placements. seat_cost_monthly from Organization.settings (default $500).
4. **Export approach**: window.print() per constraints -- no server-side PDF library.

## Deviations from Plan

None -- plan executed exactly as written.

## Test Results

- Backend: 32 tests passing (pytest)
- Frontend: 12 tests passing (vitest)
