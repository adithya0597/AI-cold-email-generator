# Story 7.6: Approval Rate Visualization

Status: review

## Story

As an **H1B job seeker**,
I want **to see approval rate trends visually**,
So that **I can identify companies improving or declining in sponsorship**.

## Acceptance Criteria

1. **AC1: Trend chart display** — Given I view a company's H1B scorecard, when historical data is available, then I see a visual representation showing approval rate by year (last 5 years) and number of petitions by year.
2. **AC2: Trend indicator** — Given historical data shows a significant change, when approval rate is declining, then a red flag indicator is shown.
3. **AC3: Data-driven rendering** — Given the approval rate visualization component receives data, when it renders, then it displays year-over-year data points with labels.

## Tasks / Subtasks

- [x] Task 1: Create ApprovalRateChart component (AC: #1, #2, #3)
  - [x] 1.1 Create `frontend/src/components/h1b/ApprovalRateChart.tsx`
  - [x] 1.2 Implement simple bar/visual display of approval rate by year (no heavy charting library — use Tailwind-based bars)
  - [x] 1.3 Add trend arrow and red flag indicator for declining rates
  - [x] 1.4 Show petition counts per year as secondary data

- [x] Task 2: Write tests (AC: #1-#3)
  - [x] 2.1 Test chart renders data points
  - [x] 2.2 Test declining trend shows red flag
  - [x] 2.3 Test empty data shows appropriate message

## Dev Notes

- Use simple Tailwind CSS bars, not a heavy charting library (recharts/chart.js)
- Component receives pre-processed yearly data as props
- No new API calls — data comes from sponsor scorecard context

### File List

#### Files to CREATE
- `frontend/src/components/h1b/ApprovalRateChart.tsx`
- `frontend/src/__tests__/ApprovalRateChart.test.tsx`

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

- Created ApprovalRateChart with Tailwind-based bars (no charting library)
- Trend detection: improving/declining/stable with red flag indicator
- 5 tests passing

### Change Log

- 2026-02-01: Story implemented, 5 tests passing

### File List
