---
phase: "03"
plan: "07"
subsystem: briefing-frontend
tags: [briefing, react, tanstack-query, dashboard, settings, timezone, ui]
dependency-graph:
  requires: ["03-05"]
  provides: ["briefing-display", "briefing-history", "briefing-settings-ui", "briefing-empty-state"]
  affects: ["03-08"]
tech-stack:
  added: []
  patterns: ["tanstack-query-hooks", "12h-to-24h-time-conversion", "browser-timezone-detection", "expandable-sections", "skeleton-loading"]
key-files:
  created:
    - frontend/src/services/briefings.ts
    - frontend/src/components/briefing/BriefingCard.tsx
    - frontend/src/components/briefing/BriefingDetail.tsx
    - frontend/src/pages/BriefingHistory.tsx
    - frontend/src/pages/BriefingSettings.tsx
  modified:
    - frontend/src/pages/Dashboard.tsx
    - frontend/src/App.tsx
decisions:
  - "BriefingCard is the dashboard hero -- prominently displayed at top, above stats cards"
  - "12-hour AM/PM picker on frontend, converted to 24h for API -- user-friendly display"
  - "Browser timezone auto-detected via Intl.DateTimeFormat, editable from curated list of 20+ zones"
  - "Channel toggle enforces minimum-one requirement client-side to prevent empty delivery config"
  - "Lite briefing rendered with amber styling and cached-data messaging to distinguish from full briefings"
metrics:
  duration: ~6 min
  completed: 2026-01-31
---

# Phase 3 Plan 07: Briefing Frontend Summary

**In-app briefing display with dashboard hero, history page, settings page, and empty state for new users using TanStack Query hooks against the Plan 05 API.**

## What Was Built

### Task 1: BriefingCard + BriefingHistory + Dashboard Integration

**BriefingCard** (`frontend/src/components/briefing/BriefingCard.tsx`):
- Time-aware personalized greeting ("Good morning, {name}!")
- Key metrics summary cards: new matches, pending approvals, applications sent
- Expandable sections: Actions Needed, New Matches, Activity Log, Tips
- "Mark as Read" button calling POST /api/v1/briefings/{id}/read
- Unread indicator (indigo ring highlight)
- Lite briefing rendering with amber gradient and cached-data explanation
- Footer with "View Briefing History" link and generation timestamp

**BriefingEmptyState** (exported from BriefingCard):
- Encouraging message for new users with no briefings yet
- Tips: add skills, fine-tune deal-breakers, set briefing time
- Link to Preferences page

**BriefingDetail** (`frontend/src/components/briefing/BriefingDetail.tsx`):
- Full-page view with all sections expanded
- Full/Lite type badge
- Delivery channel info in footer
- Back navigation to history

**BriefingHistory** (`frontend/src/pages/BriefingHistory.tsx`):
- Paginated list from GET /api/v1/briefings (20 per page)
- Each entry: date, time, type badge, read status dot, summary preview, metrics
- Previous/Next pagination controls
- Empty state for no briefings

**Dashboard** (`frontend/src/pages/Dashboard.tsx`):
- Latest briefing shown as hero at top of page
- Skeleton loading state while fetching
- Falls back to BriefingEmptyState when no briefings exist

**Briefing API Service** (`frontend/src/services/briefings.ts`):
- Typed interfaces: Briefing, BriefingContent, BriefingSettings, BriefingHistoryResponse
- TanStack Query hooks: useLatestBriefing, useBriefingHistory, useBriefing, useMarkBriefingRead, useBriefingSettings, useUpdateBriefingSettings
- Query key factory for cache invalidation
- All hooks use authenticated axios via useApiClient

**Routes** added to App.tsx:
- `/briefings` -- BriefingHistory (protected)
- `/briefings/settings` -- BriefingSettingsPage (protected)
- `/briefings/:briefingId` -- BriefingDetail (protected)

### Task 2: BriefingSettings Page

**BriefingSettings** (`frontend/src/pages/BriefingSettings.tsx`):
- Hour picker: 1-12 dropdown with AM/PM selector, converted to 24h for API
- Minute picker: 00, 15, 30, 45 options
- Timezone: auto-detected from browser, editable from curated list of 23 common timezones
- Delivery channels: In-App and Email checkboxes with minimum-one enforcement
- Save button calls PUT /api/v1/briefings/settings
- Toast confirmation on success
- "Changes take effect from next scheduled briefing" informational note
- Disabled save when no changes or while saving

## Deviations from Plan

None -- plan executed exactly as written.

## Commits

| Hash | Message |
|------|---------|
| 0c1e0ae | feat(03-06/07): BriefingCard, BriefingDetail, BriefingHistory, Dashboard integration, API service |
| 1c722b5 | feat(03-07): BriefingSettings page with time, timezone, and channel config |

Note: Task 1 files were committed alongside Plan 06's EmergencyBrake commit (0c1e0ae) due to parallel execution on the same branch. All files are present and correct.

## Next Phase Readiness

Plan 07 is complete. All briefing frontend components are built and wired to the Plan 05 backend API. Ready for Plan 08 (Integration Tests + Phase Verification).
