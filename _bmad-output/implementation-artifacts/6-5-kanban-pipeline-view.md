# Story 6.5: Kanban Pipeline View

Status: review

## Story

As a **user**,
I want **to see my applications in a Kanban board**,
So that **I can visualize my job search pipeline at a glance**.

## Acceptance Criteria

1. **AC1 - Kanban Columns:** Given I navigate to Pipeline, when I view the Kanban board, then I see columns: Applied, Screening, Interview, Offer, Closed/Rejected.
2. **AC2 - Card Content:** Given applications exist, when I view a column, then each card shows: Company, Title, Days in stage, Last update.
3. **AC3 - Drag & Drop:** Given I am viewing the Kanban board, when I drag a card between columns, then the application status is updated via API.
4. **AC4 - Agent Indicator:** Given an application was auto-moved by the pipeline agent, when I view the card, then it shows an "Updated by agent" indicator.
5. **AC5 - Card Click:** Given I click a card, when the detail panel opens, then I see full application details.
6. **AC6 - Column Counts:** Given applications exist in columns, when I view column headers, then each header shows the count of applications in that column.

## Tasks / Subtasks

- [x] Task 1: Create Pipeline page with Kanban board (AC: #1, #6)
  - [x]1.1: Create `frontend/src/pages/Pipeline.tsx` with column layout for each status
  - [x]1.2: Use existing `useApplications()` hook to fetch data, group by status
  - [x]1.3: Display column headers with counts
  - [x]1.4: Write component test (>=2 tests)

- [x] Task 2: Create KanbanCard component (AC: #2, #4)
  - [x]2.1: Create `frontend/src/components/pipeline/KanbanCard.tsx` with company, title, days in stage, last update
  - [x]2.2: Show "Updated by agent" badge when `last_updated_by === 'agent'`
  - [x]2.3: Write component test (>=2 tests)

- [x] Task 3: Add drag & drop between columns (AC: #3)
  - [x]3.1: Implement HTML5 drag and drop (no new library) on KanbanCard and columns
  - [x]3.2: Add `useUpdateApplicationStatus()` mutation to `applications.ts` service
  - [x]3.3: Call PATCH `/api/v1/applications/{id}/status` on drop with optimistic update
  - [x]3.4: Write test for drag handler (>=1 test)

- [x] Task 4: Add card detail panel (AC: #5)
  - [x]4.1: Create `frontend/src/components/pipeline/CardDetailPanel.tsx` — slide-over panel with full details
  - [x]4.2: Show on card click, close on overlay click or Escape
  - [x]4.3: Write test for panel open/close (>=1 test)

- [x] Task 5: Add route and navigation (AC: #1)
  - [x]5.1: Add `/pipeline` route to App.tsx with OnboardingGuard
  - [x]5.2: Add Pipeline nav link in App.tsx navigation

- [x] Task 6: Add backend PATCH endpoint for status update (AC: #3)
  - [x]6.1: Add PATCH `/api/v1/applications/{id}/status` endpoint to applications router
  - [x]6.2: Validate status transitions, update DB, create audit trail
  - [x]6.3: Write backend unit tests (>=2 tests)

## Dev Notes

### Architecture Compliance
- Frontend uses React 18 + TypeScript + Tailwind CSS (no external component library)
- State management: TanStack Query for server state, no Zustand needed for this page
- Use HTML5 Drag & Drop API — NO new npm dependencies (no react-beautiful-dnd, no dnd-kit)
- Follow existing patterns from Matches page: useApiClient() hook, TanStack Query mutations with optimistic updates
- Backend: FastAPI endpoints in existing applications router, raw SQL via `text()`, Depends(get_current_user_id)
- Application statuses from schema: applied, screening, interview, offer, closed, rejected
- Kanban columns: combine closed + rejected into one "Closed" column for cleaner UX
- `ApplicationItem` type already has: id, job_id, job_title, company, status, applied_at, resume_version_id
- Need to extend `ApplicationItem` with `updated_at`, `last_updated_by` fields from backend response
- The pipeline page replaces or augments the existing Applications page — add as separate `/pipeline` route

### File Structure Requirements

**Files to CREATE:**
```
frontend/src/pages/Pipeline.tsx                           # Kanban board page
frontend/src/components/pipeline/KanbanCard.tsx           # Individual application card
frontend/src/components/pipeline/CardDetailPanel.tsx      # Slide-over detail panel
frontend/src/__tests__/Pipeline.test.tsx                  # Pipeline page tests
```

**Files to MODIFY:**
```
frontend/src/App.tsx                                      # Add /pipeline route + nav link
frontend/src/services/applications.ts                     # Add status update mutation + extend types
backend/app/api/v1/applications.py                        # Add PATCH status endpoint
backend/tests/unit/test_api/test_applications.py          # Backend endpoint tests
```

### Previous Story Intelligence
- Story 5-14 created the basic Applications page with table view and empty state
- `useApplications()` hook exists in `services/applications.ts` — fetches from `/api/v1/applications/history`
- `ApplicationItem` type already defined with core fields
- SwipeCard component in matches/ uses framer-motion drag — Kanban should use simpler HTML5 DnD
- EmptyState component exists in `components/shared/EmptyState.tsx`
- Applications backend router exists at `backend/app/api/v1/applications.py`
- `application_status_changes` audit table exists from Story 6-1

### Testing Requirements
- **Pipeline Page Tests:** Render with mock data, verify columns displayed. Render with empty data, verify empty state.
- **KanbanCard Tests:** Render with props, verify content displayed. Render with agent update, verify badge shown.
- **Drag Tests:** Verify onDragStart/onDrop handlers called.
- **Detail Panel Tests:** Verify panel opens on click, closes on Escape.
- **Backend Tests:** Test PATCH endpoint updates status. Test invalid status returns 400.
- Use `@testing-library/react` for frontend. Use `patch` + `AsyncMock` for backend.

## Dev Agent Record
### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)
### Route Taken
SIMPLE (score: 7/16, overridden by user flag)
### GSD Subagents Used
None (direct execution)
### Debug Log References
None — no errors encountered
### Completion Notes List
- Created Kanban board page with 5 columns (Applied, Screening, Interview, Offer, Closed)
- Closed/Rejected statuses merged into single Closed column
- KanbanCard shows company, title, days in stage, applied date, agent badge
- HTML5 drag & drop between columns (no external dependencies)
- CardDetailPanel slide-over with Escape/overlay close
- Backend PATCH endpoint with status validation and audit trail
- 10 frontend tests + 3 backend tests, all passing
### Change Log
- 2026-02-01: Story implemented and moved to review
### File List
**Created:**
- frontend/src/pages/Pipeline.tsx
- frontend/src/components/pipeline/KanbanCard.tsx
- frontend/src/components/pipeline/CardDetailPanel.tsx
- frontend/src/__tests__/Pipeline.test.tsx

**Modified:**
- frontend/src/App.tsx
- frontend/src/services/applications.ts
- backend/app/api/v1/applications.py
- backend/tests/unit/test_api/test_applications.py
