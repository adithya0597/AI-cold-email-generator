# Story 6.8: Follow-up Draft Generation

Status: review

## Story

As a **user**,
I want **AI-generated follow-up email drafts with editing and send/copy capabilities**,
So that **I can follow up professionally without writing from scratch**.

## Acceptance Criteria

1. **AC1 - Draft Display:** Given a follow-up is suggested, when I view the suggestion, then I see a draft email with: appropriate subject line, reference to original application, polite status inquiry, restatement of interest.
2. **AC2 - Edit Before Send:** Given I am viewing a draft, when I click edit, then I can modify the subject and body before sending.
3. **AC3 - Send via Email:** Given I have a connected email account, when I click "Send", then the follow-up is sent via the connected account and the suggestion is marked as sent.
4. **AC4 - Copy to Clipboard:** Given no connected email (or user prefers), when I click "Copy to Clipboard", then the draft is copied and the suggestion is marked as sent.
5. **AC5 - Suggestion List UI:** Given I navigate to follow-ups, when the page loads, then I see a list of pending follow-up suggestions with company, title, due date, and expandable draft preview.
6. **AC6 - Update Draft Endpoint:** Given a user edits a draft, when they save changes, then the backend persists the updated subject/body via a PATCH endpoint.

## Tasks / Subtasks

- [x] Task 1: Add backend endpoints for draft management (AC: #3, #4, #6)
  - [x] 1.1: Add PATCH `/api/v1/applications/followups/{id}/draft` endpoint to update draft subject/body
  - [x] 1.2: Add POST `/api/v1/applications/followups/{id}/send` endpoint that sends via email service or marks as sent
  - [x] 1.3: Add `sent_at` column handling in followup_suggestions table (via CREATE TABLE IF NOT EXISTS pattern already used)

- [x] Task 2: Create frontend followup service hooks (AC: #1, #5)
  - [x] 2.1: Add `FollowupSuggestion` type and `useFollowups()` query hook in `frontend/src/services/followups.ts`
  - [x] 2.2: Add `useUpdateDraft()` mutation hook
  - [x] 2.3: Add `useSendFollowup()` mutation hook
  - [x] 2.4: Add `useDismissFollowup()` mutation hook
  - [x] 2.5: Add `useCopyFollowup()` hook (copies to clipboard + marks sent)

- [x] Task 3: Create FollowUpList component (AC: #1, #5)
  - [x] 3.1: Create `frontend/src/components/followups/FollowUpList.tsx` — lists pending suggestions
  - [x] 3.2: Show company, job title, followup_date, draft_subject as summary row
  - [x] 3.3: Expandable row reveals full draft body preview
  - [x] 3.4: Action buttons per suggestion: Edit, Send, Copy, Dismiss

- [x] Task 4: Create FollowUpEditor component (AC: #2, #3, #4)
  - [x] 4.1: Create `frontend/src/components/followups/FollowUpEditor.tsx` — modal/inline editor
  - [x] 4.2: Editable subject input and body textarea
  - [x] 4.3: "Save Draft" button calls PATCH endpoint
  - [x] 4.4: "Send" button calls POST send endpoint
  - [x] 4.5: "Copy to Clipboard" button copies subject+body to clipboard and marks sent
  - [x] 4.6: Show toast notifications for success/failure

- [x] Task 5: Create FollowUps page and route (AC: #5)
  - [x] 5.1: Create `frontend/src/pages/FollowUps.tsx` — page wrapper with header and empty state
  - [x] 5.2: Add `/followups` route to App.tsx with OnboardingGuard
  - [x] 5.3: Add "Follow-ups" nav link in desktop and mobile navigation

- [x] Task 6: Write comprehensive tests (AC: #1-#6)
  - [x] 6.1: Write backend API tests (>=3): update draft, send followup, send not-found
  - [x] 6.2: Write frontend component tests (>=6): list rendering, expand row, edit modal, save draft, copy to clipboard, empty state

## Dev Notes

### Architecture Compliance
- Backend: raw SQL via `text()` with parameterized queries, lazy imports inside methods
- Backend: FastAPI endpoints in `app/api/v1/applications.py` with `Depends(get_current_user_id)`
- Frontend: TanStack Query hooks in dedicated service file, `useApiClient()` pattern
- Frontend: React components with Tailwind CSS, no external UI libraries
- Email sending: Use existing email service pattern (`app/services/email/`) if connected account exists, otherwise clipboard-only

### File Structure Requirements

**Files to CREATE:**
```
frontend/src/services/followups.ts                         # Query hooks
frontend/src/components/followups/FollowUpList.tsx         # List component
frontend/src/components/followups/FollowUpEditor.tsx       # Editor component
frontend/src/pages/FollowUps.tsx                           # Page wrapper
frontend/src/__tests__/FollowUps.test.tsx                  # Frontend tests
backend/tests/unit/test_api/test_followup_draft_endpoints.py  # API tests
```

**Files to MODIFY:**
```
backend/app/api/v1/applications.py                         # Add draft/send endpoints
frontend/src/App.tsx                                       # Add /followups route + nav
```

### Previous Story Intelligence
- Story 6-7 created `FollowUpAgent` with `_generate_followup_draft()` and backend storage
- Story 6-7 created GET `/followups` and PATCH `/followups/{id}/dismiss` endpoints in `applications.py`
- Story 6-7 `followup_suggestions` table has: id, user_id, application_id, company, job_title, status, followup_date, draft_subject, draft_body, dismissed_at, created_at
- Story 6-7 tests patch `app.db.engine.AsyncSessionLocal` (NOT module-level — lazy import pattern)
- Frontend `useApiClient()` pattern from `frontend/src/services/api.ts`
- App.tsx route pattern: `<Route path="/followups" element={<OnboardingGuard><FollowUps /></OnboardingGuard>} />`
- Pipeline.tsx nav link pattern used for adding new nav items
- Story 6-5 added `/pipeline` route with nav links in both desktop and mobile sections

### Testing Requirements
- **Backend API Tests:** Test PATCH draft update, POST send, POST send not-found (404)
- **Frontend Tests:** Test list renders suggestions, expand row shows body, edit opens editor, save calls API, copy to clipboard, empty state
- Use `patch` + `AsyncMock` for DB sessions, same pattern as `test_followup_endpoints.py`
- Frontend tests: mock `useFollowups`, `useUpdateDraft`, `useSendFollowup` hooks

## Dev Agent Record
### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)
### Route Taken
SIMPLE (score: 7/16, overridden by user flag)
### GSD Subagents Used
None (direct execution)
### Debug Log References
- Added `sent_at` column to followup_suggestions CREATE TABLE IF NOT EXISTS in followup_agent.py
- Updated GET /followups to filter out sent suggestions (AND fs.sent_at IS NULL)
### Completion Notes List
- PATCH /followups/{id}/draft endpoint — updates subject and/or body with validation
- POST /followups/{id}/send endpoint — marks suggestion as sent
- Frontend service with 5 hooks: useFollowups, useUpdateDraft, useSendFollowup, useDismissFollowup, useCopyFollowup
- FollowUpList component with expandable rows, action buttons (Edit, Send, Copy, Dismiss)
- FollowUpEditor modal with editable subject/body, Save/Send/Copy actions, toast notifications
- FollowUps page with loading/error/empty states
- /followups route with OnboardingGuard, desktop + mobile nav links
- 15 tests total (5 backend API + 10 frontend), all passing
### Change Log
- 2026-02-01: Story implemented and moved to review
### File List
**Created:**
- frontend/src/services/followups.ts
- frontend/src/components/followups/FollowUpList.tsx
- frontend/src/components/followups/FollowUpEditor.tsx
- frontend/src/pages/FollowUps.tsx
- frontend/src/__tests__/FollowUps.test.tsx
- backend/tests/unit/test_api/test_followup_draft_endpoints.py

**Modified:**
- backend/app/api/v1/applications.py
- backend/app/agents/core/followup_agent.py
- frontend/src/App.tsx
