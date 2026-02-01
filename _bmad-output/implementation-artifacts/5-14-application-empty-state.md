# Story 5.14: Application Empty State

Status: review

## Story

As a **user**,
I want **guidance when I haven't applied to any jobs yet**,
so that **I know how to get started**.

## Acceptance Criteria

1. **AC1 - Empty State Message:** Given I have zero applications, when I view the applications page, then I see: "No applications yet. Let's change that!" with an encouraging illustration.

2. **AC2 - CTA Button:** Given the empty state is displayed, when I view it, then I see a CTA: "Review your matches" linking to `/matches`.

3. **AC3 - Helpful Tip:** Given the empty state is displayed, when I view it, then I see a tip: "Save jobs you like, then approve applications in your briefing."

4. **AC4 - Tests:** Given the applications page exists, when unit tests run, then coverage exists for empty state rendering, CTA link, and tip text.

## Tasks / Subtasks

- [x] Task 1: Create Applications page with empty state (AC: #1, #2, #3)
  - [x] 1.1: Create `frontend/src/pages/Applications.tsx` with empty state using existing patterns
  - [x] 1.2: Add applications service hook for fetching application list
  - [x] 1.3: Add route `/applications` in App.tsx (protected, behind OnboardingGuard)

- [x] Task 2: Write tests (AC: #4)
  - [x] 2.1: Test empty state message renders
  - [x] 2.2: Test CTA link to /matches
  - [x] 2.3: Test tip text renders

## Dev Notes

### Architecture Compliance

1. **Use existing EmptyState-like pattern** from Matches.tsx — inline empty state with early return.
2. **Use TanStack Query** for data fetching, following matches.ts service pattern.
3. **Protected route with OnboardingGuard** — same as Dashboard and Matches.
4. **No new dependencies needed.**

### File Structure Requirements

**Files to CREATE:**
```
frontend/src/pages/Applications.tsx                    # Applications page with empty state
frontend/src/services/applications.ts                  # Application API service hooks
frontend/src/__tests__/Applications.test.tsx           # Tests
```

**Files to MODIFY:**
```
frontend/src/App.tsx                                   # Add /applications route
```

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
SIMPLE (score: 0/16)

### Completion Notes List
- Created Applications page with empty state, loading, error, and list views
- Created applications service with TanStack Query hook
- Added /applications route behind OnboardingGuard
- 5 tests for empty state, CTA, tip, loading, and list rendering

### Change Log
- 2026-02-01: Created Applications page with empty state + 5 tests

### File List
**Created:**
- `frontend/src/pages/Applications.tsx`
- `frontend/src/services/applications.ts`
- `frontend/src/__tests__/Applications.test.tsx`

**Modified:**
- `frontend/src/App.tsx`

