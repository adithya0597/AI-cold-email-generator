# Story 7.5: Sponsor Scorecard UI

Status: review

## Story

As an **H1B job seeker**,
I want **to view a company's sponsorship scorecard**,
So that **I can assess visa sponsorship likelihood**.

## Acceptance Criteria

1. **AC1: Scorecard display** — Given I view a company's H1B section, when the scorecard loads, then I see: overall sponsor score (A+ to F grade), approval rate with trend arrow, number of H1B employees, common sponsored job titles, average LCA wage, and last petition date.
2. **AC2: Scoring methodology** — Given I view the scorecard, when I look at the scoring section, then the scorecard explains the scoring methodology (grade thresholds).
3. **AC3: Data freshness** — Given I view the scorecard, when data exists, then "Data last updated: [date]" is displayed.
4. **AC4: API integration** — Given the scorecard component fetches data, when the API responds, then it uses the GET /api/v1/h1b/sponsors/{company} endpoint from Story 7-1.
5. **AC5: Loading and error states** — Given the scorecard is fetching, when loading, then a skeleton loader is shown. If the API errors, a retry option is displayed.

## Tasks / Subtasks

- [x] Task 1: Create H1B API service hooks (AC: #4)
  - [x] 1.1 Create `frontend/src/services/h1b.ts` with query key definitions and fetch functions
  - [x] 1.2 Implement `useSponsorData(company: string)` hook using useQuery
  - [x] 1.3 Implement `useSponsorSearch(query: string)` hook using useQuery with enabled flag

- [x] Task 2: Create SponsorScorecard component (AC: #1, #2, #3)
  - [x] 2.1 Create `frontend/src/components/h1b/SponsorScorecard.tsx`
  - [x] 2.2 Implement grade calculation: A+ (≥95%), A (≥90%), B+ (≥85%), B (≥80%), C (≥70%), D (≥50%), F (<50%)
  - [x] 2.3 Display approval rate with trend arrow (↑/↓/→)
  - [x] 2.4 Display petition count, job titles, average wage
  - [x] 2.5 Display "Data last updated: [date]" from freshness timestamps
  - [x] 2.6 Add scoring methodology tooltip/section

- [x] Task 3: Add loading and error states (AC: #5)
  - [x] 3.1 Create skeleton loader for scorecard
  - [x] 3.2 Add error state with retry button

- [x] Task 4: Write tests (AC: #1-#5)
  - [x] 4.1 Test scorecard renders all fields
  - [x] 4.2 Test grade calculation for different approval rates
  - [x] 4.3 Test loading state shows skeleton
  - [x] 4.4 Test error state shows retry

## Dev Notes

### Architecture Compliance

- **Component location**: `frontend/src/components/h1b/SponsorScorecard.tsx`
- **Service location**: `frontend/src/services/h1b.ts`
- **Styling**: Tailwind CSS, follow existing card patterns (rounded-lg border shadow-sm)
- **API pattern**: useApiClient() + useQuery from TanStack Query
- **No routing changes** — component will be imported by match detail and other pages in later stories

### References

- [Source: frontend/src/services/matches.ts — API hook pattern]
- [Source: frontend/src/components/preferences/H1BStep.tsx — existing H1B component]

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

- Created H1B API service with useSponsorData and useSponsorSearch hooks
- Created SponsorScorecard component with grade calculation (A+ to F)
- Includes skeleton loader, error state with retry, scoring methodology
- 12 tests: 8 grade calculation, 4 component rendering

### Change Log

- 2026-02-01: Story implemented, all 12 tests passing

### File List

#### Files to CREATE
- `frontend/src/services/h1b.ts`
- `frontend/src/components/h1b/SponsorScorecard.tsx`
- `frontend/src/__tests__/SponsorScorecard.test.tsx`

#### Files to MODIFY
- none
