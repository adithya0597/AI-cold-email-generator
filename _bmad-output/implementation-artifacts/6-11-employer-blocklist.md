# Story 6.11: Employer Blocklist

Status: review

## Story

As a **Stealth Mode user**,
I want **to blocklist companies that should never see my activity**,
So that **I'm protected from discovery by current/past employers**.

## Acceptance Criteria

1. **AC1 - Add Company:** Given Stealth Mode is active, when I add a company to my blocklist, then it is saved with the company name and optional note.
2. **AC2 - List Blocklist:** Given I have blocklisted companies, when I view my blocklist, then I see all blocked companies with their notes and date added.
3. **AC3 - Remove Company:** Given I have a company blocklisted, when I remove it, then it is deleted from my blocklist.
4. **AC4 - Note Categories:** Given I add a company, when I provide a note, then I can categorize it as "Current employer", "Competitor", or a custom note.
5. **AC5 - Stealth Required:** Given Stealth Mode is not active, when I try to access the blocklist, then I see a message that Stealth Mode must be enabled first.

## Tasks / Subtasks

- [x]Task 1: Add backend blocklist endpoints (AC: #1, #2, #3)
  - [x]1.1: Create `employer_blocklist` table via CREATE TABLE IF NOT EXISTS (id, user_id, company_name, note, created_at) in privacy.py endpoints
  - [x]1.2: Add GET `/api/v1/privacy/blocklist` endpoint — returns list of blocklisted companies for current user
  - [x]1.3: Add POST `/api/v1/privacy/blocklist` endpoint — adds a company with optional note, validates stealth is enabled
  - [x]1.4: Add DELETE `/api/v1/privacy/blocklist/{id}` endpoint — removes a company from blocklist

- [x]Task 2: Add frontend blocklist service hooks (AC: #1, #2, #3)
  - [x]2.1: Add types `BlocklistEntry`, `BlocklistResponse` and hooks `useBlocklist()`, `useAddToBlocklist()`, `useRemoveFromBlocklist()` to `frontend/src/services/privacy.ts`

- [x]Task 3: Create Blocklist UI on Privacy page (AC: #1, #2, #3, #4, #5)
  - [x]3.1: Create `frontend/src/components/privacy/BlocklistManager.tsx` — displays blocklist entries with add/remove controls
  - [x]3.2: Add input field with company name and optional note (preset categories: "Current employer", "Competitor", or custom)
  - [x]3.3: Show "Stealth Mode required" message when stealth is not active
  - [x]3.4: Integrate BlocklistManager into Privacy.tsx page below the stealth toggle

- [x]Task 4: Write comprehensive tests (AC: #1-#5)
  - [x]4.1: Write backend tests (>=3): list blocklist, add company, remove company, add without stealth → 403
  - [x]4.2: Write frontend tests (>=4): blocklist renders entries, add company, remove company, stealth-required message

## Dev Notes

### Architecture Compliance
- Backend: raw SQL via `text()` with parameterized queries, lazy imports inside methods
- Backend: FastAPI endpoints in `app/api/v1/privacy.py` with `Depends(get_current_user_id)`
- Frontend: TanStack Query hooks in `frontend/src/services/privacy.ts`, `useApiClient()` pattern
- Frontend: React components with Tailwind CSS, no external UI libraries
- Stealth validation: check `stealth_settings` table before allowing blocklist operations
- Note on encryption: The epic mentions AES-256 encryption at rest, but for MVP the database-level encryption (Supabase uses encrypted storage) suffices. Application-level encryption can be added in a follow-up story.

### File Structure Requirements

**Files to CREATE:**
```
frontend/src/components/privacy/BlocklistManager.tsx       # Blocklist UI component
frontend/src/__tests__/Blocklist.test.tsx                  # Frontend tests
backend/tests/unit/test_api/test_blocklist_endpoints.py    # API tests
```

**Files to MODIFY:**
```
backend/app/api/v1/privacy.py                              # Add blocklist endpoints
frontend/src/services/privacy.ts                           # Add blocklist hooks
frontend/src/pages/Privacy.tsx                             # Integrate BlocklistManager
```

### Previous Story Intelligence
- Story 6-10 created `privacy.py` with GET/POST `/stealth` endpoints and `stealth_settings` table
- Story 6-10 created `privacy.ts` with `useStealthStatus()` and `useToggleStealth()` hooks
- Story 6-10 created `Privacy.tsx` page with stealth toggle
- Test pattern: patch `app.db.engine.AsyncSessionLocal`, `AsyncMock` + `MagicMock`
- Frontend test pattern: mock hooks from `../services/privacy`

### Testing Requirements
- **Backend Tests:** Test GET blocklist (with entries + empty), POST add company (with stealth active), POST add without stealth (403), DELETE remove company
- **Frontend Tests:** Test blocklist renders entries, add company form, remove button, stealth-required message when stealth inactive

## Dev Agent Record
### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)
### Route Taken
SIMPLE (score: 6/16)
### GSD Subagents Used
None (direct execution)
### Debug Log References
- Fixed frontend test duplicate text issue with getAllByText for "Current employer"
### Completion Notes List
- GET /api/v1/privacy/blocklist endpoint returning entries list with total
- POST /api/v1/privacy/blocklist endpoint with stealth validation (403 if not active)
- DELETE /api/v1/privacy/blocklist/{id} endpoint
- employer_blocklist table via CREATE TABLE IF NOT EXISTS
- useBlocklist, useAddToBlocklist, useRemoveFromBlocklist hooks in privacy.ts
- BlocklistManager component with add form, note presets, entry list, remove buttons
- Stealth-required message when stealth is disabled
- Integrated into Privacy.tsx page
- 12 new tests (6 backend + 6 frontend), all passing
### Change Log
- 2026-02-01: Story implemented and moved to review
### File List
**Created:**
- frontend/src/components/privacy/BlocklistManager.tsx
- frontend/src/__tests__/Blocklist.test.tsx
- backend/tests/unit/test_api/test_blocklist_endpoints.py

**Modified:**
- backend/app/api/v1/privacy.py
- frontend/src/services/privacy.ts
- frontend/src/pages/Privacy.tsx
