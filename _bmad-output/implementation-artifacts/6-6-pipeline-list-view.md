# Story 6.6: Pipeline List View

Status: review

## Story

As a **user**,
I want **an alternative list view of my pipeline**,
So that **I can sort and filter applications efficiently**.

## Acceptance Criteria

1. **AC1 - View Toggle:** Given I am on the Pipeline page, when I click a toggle button, then I switch between Kanban board and List view.
2. **AC2 - Table Columns:** Given I am in List View, when I view the table, then I see columns: Company, Title, Status, Applied Date, Last Update.
3. **AC3 - Column Sorting:** Given I am viewing the list, when I click a column header, then the table sorts by that column (ascending/descending toggle).
4. **AC4 - Status Filter:** Given I am viewing the list, when I filter by Status, then only applications with that status are shown.
5. **AC5 - Keyword Search:** Given I am viewing the list, when I type in the search box, then results are filtered by company or title matching the keyword.
6. **AC6 - Bulk Status Change:** Given I select multiple rows, when I choose "Change Status" from bulk actions, then all selected applications are updated.

## Tasks / Subtasks

- [x] Task 1: Add view toggle to Pipeline page (AC: #1)
  - [x]1.1: Add `viewMode` state ('kanban' | 'list') to Pipeline.tsx
  - [x]1.2: Create toggle button group in Pipeline page header
  - [x]1.3: Conditionally render Kanban board or PipelineListView based on viewMode
  - [x]1.4: Write test for view toggle (>=1 test)

- [x] Task 2: Create PipelineListView component (AC: #2)
  - [x]2.1: Create `frontend/src/components/pipeline/PipelineListView.tsx` with table layout
  - [x]2.2: Display columns: Company, Title, Status (badge), Applied Date, Last Update
  - [x]2.3: Receive applications as prop, render rows
  - [x]2.4: Write component test (>=2 tests)

- [x] Task 3: Add column sorting (AC: #3)
  - [x]3.1: Add `sortField` and `sortDirection` state to PipelineListView
  - [x]3.2: Implement sort logic for each column (string compare for text, date compare for dates)
  - [x]3.3: Add clickable sort indicators on column headers
  - [x]3.4: Write sort test (>=1 test)

- [x] Task 4: Add status filter and keyword search (AC: #4, #5)
  - [x]4.1: Add filter bar above table with status dropdown and search input
  - [x]4.2: Implement status filter using COLUMNS statuses from Pipeline.tsx
  - [x]4.3: Implement keyword search filtering on company and title fields
  - [x]4.4: Write filter/search test (>=1 test)

- [x] Task 5: Add bulk actions (AC: #6)
  - [x]5.1: Add row selection checkboxes and "select all" in header
  - [x]5.2: Add bulk action bar that appears when rows are selected
  - [x]5.3: Implement "Change Status" bulk action using existing useUpdateApplicationStatus mutation
  - [x]5.4: Write bulk action test (>=1 test)

## Dev Notes

### Architecture Compliance
- Frontend uses React 18 + TypeScript + Tailwind CSS (no external component library)
- State management: local React state for sort/filter/search/selection — no Zustand needed
- Reuse existing `useApplications()` hook and `useUpdateApplicationStatus()` mutation from `services/applications.ts`
- No new npm dependencies — use native HTML table elements with Tailwind styling
- Follow patterns established in Story 6-5 Pipeline.tsx (columns, grouping, empty state)
- Application statuses from schema: applied, screening, interview, offer, closed, rejected
- `ApplicationItem` type already has: id, job_id, job_title, company, status, applied_at, resume_version_id, updated_at, last_updated_by

### File Structure Requirements

**Files to CREATE:**
```
frontend/src/components/pipeline/PipelineListView.tsx    # Table view component
frontend/src/__tests__/PipelineListView.test.tsx         # List view tests
```

**Files to MODIFY:**
```
frontend/src/pages/Pipeline.tsx                          # Add view toggle, render list view
```

### Previous Story Intelligence
- Story 6-5 created the Kanban board in Pipeline.tsx with 5 columns (Applied, Screening, Interview, Offer, Closed)
- `groupByStatus()` function already maps applications to column buckets — list view should use flat application array instead
- `COLUMNS` and `CLOSED_STATUSES` constants available for status reference
- KanbanCard and CardDetailPanel already exist — list view row click should also open CardDetailPanel
- `useUpdateApplicationStatus()` mutation already works — reuse for bulk status changes
- Frontend tests use vitest + @testing-library/react with mocked `useApplications` and `useUpdateApplicationStatus`
- Pipeline page already handles loading, error, and empty states — list view shares these states

### Testing Requirements
- **View Toggle Test:** Click toggle, verify list view renders instead of kanban
- **Table Rendering Tests:** Render with mock data, verify all columns displayed. Verify status badge rendering.
- **Sort Test:** Click column header, verify rows reorder
- **Filter/Search Test:** Apply status filter, verify filtered results. Type search, verify filtered results.
- **Bulk Action Test:** Select rows, click change status, verify mutation called for each selected row
- Use `@testing-library/react` with mocked services (same pattern as Pipeline.test.tsx)

## Dev Agent Record
### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)
### Route Taken
SIMPLE (score: 1/16, overridden by user flag)
### GSD Subagents Used
None (direct execution)
### Debug Log References
None — no errors encountered
### Completion Notes List
- Created PipelineListView with sortable table, status filter, keyword search, bulk actions
- Added Board/List toggle to Pipeline page header
- View toggle conditionally renders Kanban or List view
- 9 new frontend tests covering toggle, table, sort, filter, search, bulk actions
### Change Log
- 2026-02-01: Story implemented and moved to review
### File List
**Created:**
- frontend/src/components/pipeline/PipelineListView.tsx
- frontend/src/__tests__/PipelineListView.test.tsx

**Modified:**
- frontend/src/pages/Pipeline.tsx
