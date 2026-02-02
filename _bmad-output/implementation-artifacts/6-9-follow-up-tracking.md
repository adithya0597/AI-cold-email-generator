# Story 6.9: Follow-up Tracking

Status: review

## Story

As a **user**,
I want **to track whether I've followed up on applications**,
So that **I don't accidentally follow up twice or miss follow-ups**.

## Acceptance Criteria

1. **AC1 - Follow-up History:** Given I view a pipeline card or follow-up suggestion, when follow-ups have occurred, then I see follow-up history with date and message preview.
2. **AC2 - Last Followed Up Indicator:** Given an application has been followed up, when I view its pipeline card, then I see "Last followed up: X days ago" indicator.
3. **AC3 - Overdue Reminder Badge:** Given a follow-up is overdue, when I view the pipeline card, then the card shows a reminder badge.
4. **AC4 - Manual Follow-up Mark:** Given I followed up outside the app, when I click "Followed up manually", then the suggestion is dismissed and a history record is created.
5. **AC5 - Excessive Follow-up Warning:** Given I've followed up 3+ times on an application, when another follow-up is suggested, then I see a warning: "You've followed up 3 times — consider moving on".

## Tasks / Subtasks

- [x] Task 1: Add backend follow-up history endpoint (AC: #1, #2)
  - [x] 1.1: Add GET `/api/v1/applications/{id}/followup-history` endpoint returning sent follow-ups for an application
  - [x] 1.2: Query `followup_suggestions` where `sent_at IS NOT NULL` for the application, ordered by sent_at DESC
  - [x] 1.3: Return list of `{id, draft_subject, sent_at}` items plus `followup_count` and `last_followup_at`

- [x] Task 2: Add manual follow-up mark endpoint (AC: #4)
  - [x] 2.1: Add POST `/api/v1/applications/followups/{id}/mark-manual` endpoint
  - [x] 2.2: Set `sent_at = NOW()` and `draft_subject = 'Manual follow-up'` on the suggestion, then dismiss it

- [x] Task 3: Add follow-up count to followup suggestions response (AC: #5)
  - [x] 3.1: Modify GET `/api/v1/applications/followups` to include `followup_count` per application (count of sent follow-ups)
  - [x] 3.2: Frontend displays warning when `followup_count >= 3`

- [x] Task 4: Add follow-up indicators to KanbanCard (AC: #2, #3)
  - [x] 4.1: Create `useFollowupHistory(applicationId)` hook in `frontend/src/services/followups.ts`
  - [x] 4.2: Add "Last followed up: X days ago" text to KanbanCard when history exists
  - [x] 4.3: Add overdue reminder badge to KanbanCard when follow-up is overdue (followup_date < now and not sent/dismissed)

- [x] Task 5: Add follow-up history panel to FollowUps page (AC: #1)
  - [x] 5.1: Create `frontend/src/components/followups/FollowUpHistory.tsx` — shows sent follow-ups per application
  - [x] 5.2: Integrate into FollowUpList expanded view — show history below draft preview

- [x] Task 6: Add excessive follow-up warning (AC: #5)
  - [x] 6.1: In FollowUpList, show warning banner when `followup_count >= 3` for a suggestion
  - [x] 6.2: Warning text: "You've followed up {count} times — consider moving on"

- [x] Task 7: Write comprehensive tests (AC: #1-#5)
  - [x] 7.1: Write backend tests (>=3): followup history, mark manual, followup count in list
  - [x] 7.2: Write frontend tests (>=5): history display, last-followup indicator, overdue badge, manual mark button, excessive warning

## Dev Notes

### Architecture Compliance
- Backend: raw SQL via `text()` with parameterized queries, lazy imports inside methods
- Backend: FastAPI endpoints in `app/api/v1/applications.py` with `Depends(get_current_user_id)`
- Frontend: TanStack Query hooks in `frontend/src/services/followups.ts`, `useApiClient()` pattern
- Frontend: React components with Tailwind CSS, no external UI libraries
- `followup_suggestions` table already has `sent_at` column (added in Story 6-8)
- Query sent follow-ups: `WHERE sent_at IS NOT NULL AND application_id = :aid`
- Overdue detection: compare `followup_date` to current date for undismissed/unsent suggestions

### File Structure Requirements

**Files to CREATE:**
```
frontend/src/components/followups/FollowUpHistory.tsx      # History component
frontend/src/__tests__/FollowUpTracking.test.tsx           # Frontend tests
backend/tests/unit/test_api/test_followup_tracking_endpoints.py  # API tests
```

**Files to MODIFY:**
```
backend/app/api/v1/applications.py                         # Add history, mark-manual, count endpoints
frontend/src/services/followups.ts                         # Add useFollowupHistory, useMarkManual hooks
frontend/src/components/followups/FollowUpList.tsx          # Add history, warning, manual-mark button
frontend/src/components/pipeline/KanbanCard.tsx             # Add last-followup indicator, overdue badge
```

### Previous Story Intelligence
- Story 6-7 created `followup_suggestions` table with: id, user_id, application_id, company, job_title, status, followup_date, draft_subject, draft_body, dismissed_at, created_at
- Story 6-8 added `sent_at` column to the table and PATCH/POST endpoints for drafts
- Story 6-8 GET `/followups` filters `AND fs.sent_at IS NULL` — only shows unsent suggestions
- Story 6-8 `useSendFollowup()` marks suggestion as sent, `useDismissFollowup()` dismisses
- Backend test pattern: patch `app.db.engine.AsyncSessionLocal` (lazy import)
- Frontend test pattern: mock hooks from `../services/followups`
- KanbanCard shows `daysSince()` helper and agent badge — extend with follow-up indicators
- `FollowupSuggestion` type already has `followup_date`, `application_id` fields
- Story 6-5 KanbanCard test pattern in `Pipeline.test.tsx`

### Testing Requirements
- **Backend Tests:** Test GET history endpoint (with results + empty), POST mark-manual, GET followups with count
- **Frontend Tests:** Test history display in expanded row, last-followup indicator on KanbanCard, overdue badge, manual mark button, excessive follow-up warning
- Use `patch` + `AsyncMock` for DB sessions
- Frontend: mock hooks, render components with test data

## Dev Agent Record
### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)
### Route Taken
SIMPLE (score: 6/16, overridden by user flag)
### GSD Subagents Used
None (direct execution)
### Debug Log References
- Fixed Story 6-7 test regression: added `followup_count` to mock row in `test_followup_endpoints.py`
### Completion Notes List
- GET /{application_id}/followup-history endpoint with sent_at history, count, last_followup_at
- POST /followups/{id}/mark-manual endpoint — sets sent_at + dismissed_at simultaneously
- GET /followups now includes followup_count per application via subquery
- FollowupSuggestionItem schema extended with followup_count field
- useFollowupHistory and useMarkManualFollowup hooks added to followups.ts
- FollowUpHistory component showing sent follow-ups with date
- FollowUpList updated with history display, manual-mark button, excessive follow-up warning (>=3x)
- KanbanCard updated with "Last followed up: Xd ago" indicator and "Overdue" badge
- 13 new tests (5 backend + 8 frontend), all passing
### Change Log
- 2026-02-01: Story implemented and moved to review
### File List
**Created:**
- frontend/src/components/followups/FollowUpHistory.tsx
- frontend/src/__tests__/FollowUpTracking.test.tsx
- backend/tests/unit/test_api/test_followup_tracking_endpoints.py

**Modified:**
- backend/app/api/v1/applications.py
- backend/tests/unit/test_api/test_followup_endpoints.py
- frontend/src/services/followups.ts
- frontend/src/components/followups/FollowUpList.tsx
- frontend/src/components/pipeline/KanbanCard.tsx
