---
phase: 4
plan: 7
subsystem: matches
tags: [top-pick, matches-api, tanstack-query, briefing]
depends_on:
  requires: [04-06]
  provides: [top-pick-endpoint, top-pick-card, briefing-top-pick]
  affects: []
tech-stack:
  added: []
  patterns: [featured-card-pattern, 204-null-handling]
key-files:
  created:
    - frontend/src/components/matches/TopPickCard.tsx
    - frontend/src/components/matches/__tests__/TopPick.test.tsx
    - backend/tests/unit/test_api/test_top_pick.py
  modified:
    - backend/app/api/v1/matches.py
    - frontend/src/services/matches.ts
    - frontend/src/pages/Matches.tsx
    - frontend/src/components/briefing/BriefingCard.tsx
    - frontend/src/components/matches/__tests__/Matches.test.tsx
decisions: []
metrics:
  duration: ~5 min
  completed: 2026-01-31
---

# Phase 4 Plan 7: Top Pick of the Day Feature Summary

Full-stack "Top Pick of the Day" feature -- backend endpoint returns highest-scoring new match, TopPickCard renders with gradient styling and extended rationale, BriefingCard highlights top match with star badge and Review Now link.

## What Was Done

### Task 1: Backend top-pick endpoint
- Added `GET /matches/top-pick` route to existing matches.py router
- Query: `SELECT ... WHERE status='new' ORDER BY score DESC LIMIT 1` with selectinload(Match.job)
- Returns MatchResponse (same schema) or 204 No Content
- Route registered BEFORE `/{match_id}` to avoid FastAPI path conflicts
- 3 backend tests: highest match returned, 204 empty, non-new excluded

### Task 2: TopPickCard component
- Created `TopPickCard.tsx` with gradient border (`border-indigo-300 from-indigo-50 to-purple-50`)
- Star badge (FiStar) with "Top Pick of the Day" label
- Extended rationale section: summary, green checkmark reasons, amber warning concerns
- Save/Dismiss action buttons matching Matches page styling
- framer-motion entrance animation

### Task 3: Top-pick service hook
- Added `matchKeys.topPick()` to key factory (under 'matches' namespace)
- `fetchTopPick` uses `validateStatus` to handle 204 as null
- `useTopPick()` hook follows established useMatches pattern
- Existing `matchKeys.all` invalidation in `onSettled` covers topPick automatically

### Task 4: Matches page integration
- TopPickCard rendered above swipe stack when topPick data exists
- Save/dismiss callbacks wired to existing useUpdateMatchStatus mutation
- Graceful absence when topPick is null/undefined

### Task 5: BriefingCard top pick highlight
- Identifies highest-scored match in `content.new_matches` array
- Renders with star badge, gradient styling, "Top Pick" label, and "Review Now" link to /matches
- Remaining matches render normally without duplication

### Task 6: Frontend tests (9 tests)
- 6 TopPickCard tests: badge, title, company, rationale, save click, dismiss click
- 2 Matches page integration: top pick present, top pick absent
- 1 BriefingCard highlight test: verifies highest score identified and rendered
- Fixed existing Matches.test.tsx mock to include useTopPick

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated existing Matches.test.tsx mock**
- **Found during:** Task 6
- **Issue:** Existing Matches.test.tsx mocked `services/matches` without `useTopPick`, causing test failures after Matches.tsx now imports it
- **Fix:** Added `useTopPick: () => ({ data: null, isLoading: false, isError: false })` to mock
- **Files modified:** frontend/src/components/matches/__tests__/Matches.test.tsx
- **Commit:** c3e69d7

## Test Results

- Backend: 3/3 passing (test_top_pick.py)
- Frontend: 28/28 passing (SwipeCard 11 + Matches 8 + TopPick 9)

## Commits

| Hash | Description |
|------|-------------|
| dfbf26f | feat(04-07): add GET /matches/top-pick backend endpoint |
| 8521d55 | feat(04-07): create TopPickCard component |
| 4af1a05 | feat(04-07): add useTopPick hook and fetchTopPick service |
| 170454a | feat(04-07): integrate TopPickCard into Matches page |
| e6abac4 | feat(04-07): add top pick highlight to BriefingCard |
| c3e69d7 | test(04-07): add frontend tests for top pick feature |
