# Story 7.8: H1B Filter in Job Search

Status: review

## Story

As an **H1B job seeker**,
I want **to filter jobs by sponsorship status**,
So that **I only see visa-friendly opportunities**.

## Acceptance Criteria

1. **AC1: Filter options** — Given I am in job matches, when I apply the H1B filter, then I can select: "Verified sponsors only", "High approval rate (80%+)", or "Any sponsorship history".
2. **AC2: Filter persistence** — Given I select an H1B filter, when I navigate away and return, then the filter selection persists.
3. **AC3: Filter composability** — Given the H1B filter is applied, when combined with other filters, then both filters apply simultaneously.

## Tasks / Subtasks

- [x] Task 1: Create H1BFilter component (AC: #1, #2, #3)
  - [x] 1.1 Create `frontend/src/components/h1b/H1BFilter.tsx`
  - [x] 1.2 Implement filter options as radio group: "All jobs", "Verified sponsors only", "High approval rate (80%+)", "Any sponsorship history"
  - [x] 1.3 Persist selection to localStorage
  - [x] 1.4 Expose onFilterChange callback for parent components

- [x] Task 2: Write tests (AC: #1-#3)
  - [x] 2.1 Test all filter options render
  - [x] 2.2 Test filter selection persists to localStorage
  - [x] 2.3 Test callback fires on selection

## Dev Notes

- Standalone component — integration into Matches page is a composition concern for later
- Uses localStorage for persistence (simple, no backend storage needed)

### File List

#### Files to CREATE
- `frontend/src/components/h1b/H1BFilter.tsx`
- `frontend/src/__tests__/H1BFilter.test.tsx`

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

- Created H1BFilter component with 4 filter options
- localStorage persistence for cross-session filter state
- 5 tests passing

### Change Log

- 2026-02-01: Story implemented, 5 tests passing

### File List
