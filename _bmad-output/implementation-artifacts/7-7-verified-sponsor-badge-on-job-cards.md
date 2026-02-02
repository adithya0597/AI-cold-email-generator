# Story 7.7: Verified Sponsor Badge on Job Cards

Status: review

## Story

As an **H1B job seeker**,
I want **job cards to show H1B sponsorship status**,
So that **I can quickly identify visa-friendly opportunities**.

## Acceptance Criteria

1. **AC1: Badge display** — Given I am viewing job matches, when a company has verified H1B sponsorship history, then the job card displays a "Verified H1B Sponsor" badge.
2. **AC2: Badge color by strength** — Given a sponsor badge is shown, when the approval rate varies, then badge color indicates: Green (80%+), Yellow (50-79%), Orange (<50%).
3. **AC3: Unknown sponsorship** — Given a company has no sponsorship data, when the card renders, then "Sponsorship Unknown" is shown.

## Tasks / Subtasks

- [x] Task 1: Create SponsorBadge component (AC: #1, #2, #3)
  - [x] 1.1 Create `frontend/src/components/h1b/SponsorBadge.tsx`
  - [x] 1.2 Implement color coding by approval rate threshold
  - [x] 1.3 Handle unknown sponsorship state

- [x] Task 2: Write tests (AC: #1-#3)
  - [x] 2.1 Test green badge for 80%+ approval rate
  - [x] 2.2 Test yellow badge for 50-79%
  - [x] 2.3 Test orange badge for <50%
  - [x] 2.4 Test unknown state display

## Dev Notes

- Component is standalone — integration into SwipeCard/MatchDetail comes when those pages are updated
- No API calls — receives approval rate as prop

### File List

#### Files to CREATE
- `frontend/src/components/h1b/SponsorBadge.tsx`
- `frontend/src/__tests__/SponsorBadge.test.tsx`

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Route Taken

SIMPLE (assessed score: 1/16)

### GSD Subagents Used

none (direct execution)

### Debug Log References

No issues encountered.

### Completion Notes List

- Created SponsorBadge with green/yellow/orange/gray color coding
- Handles unknown sponsorship state gracefully
- 5 tests passing

### Change Log

- 2026-02-01: Story implemented, 5 tests passing

### File List
