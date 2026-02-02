# Story 7.10: H1B Empty State

Status: review

## Story

As an **H1B job seeker**,
I want **helpful guidance when no sponsor data exists for a company**,
So that **I know what to do next**.

## Acceptance Criteria

1. **AC1: Empty state message** — Given I view a company with no H1B data, when I access the H1B section, then I see "No sponsorship data found for [Company]".
2. **AC2: Helpful suggestions** — Given the empty state is shown, when I read it, then I see suggestions: "This may be a new company or one that hasn't sponsored recently", "Check the company's careers page for sponsorship policy", "Ask during the interview process".
3. **AC3: Notification request** — Given the empty state is shown, then I can see a "Notify me when data becomes available" option.
4. **AC4: Anonymous tip** — Given the empty state is shown, then I can see a "Know something? Share anonymous tip" option.

## Tasks / Subtasks

- [x] Task 1: Create H1BEmptyState component (AC: #1, #2, #3, #4)
  - [x] 1.1 Create `frontend/src/components/h1b/H1BEmptyState.tsx`
  - [x] 1.2 Display "No sponsorship data found for [Company]"
  - [x] 1.3 Add suggestion list
  - [x] 1.4 Add "Notify me" button (visual only — backend wiring in future story)
  - [x] 1.5 Add "Share anonymous tip" button (visual only)

- [x] Task 2: Write tests (AC: #1-#4)
  - [x] 2.1 Test empty state renders with company name
  - [x] 2.2 Test suggestions are displayed
  - [x] 2.3 Test notify and tip buttons render

## Dev Notes

- Standalone component — no backend integration for notify/tip buttons (those come in future stories)
- Follow existing EmptyState patterns in the codebase

### File List

#### Files to CREATE
- `frontend/src/components/h1b/H1BEmptyState.tsx`
- `frontend/src/__tests__/H1BEmptyState.test.tsx`

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

- Created H1BEmptyState with company name, suggestions, notify/tip buttons
- 4 tests passing

### Change Log

- 2026-02-02: Story implemented, 4 tests passing

### File List
