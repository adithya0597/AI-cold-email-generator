# Story 6.12: Privacy Proof Documentation

Status: review

## Story

As a **Stealth Mode user**,
I want **proof that my employer is blocked**,
So that **I can trust the system is actually protecting me**.

## Acceptance Criteria

1. **AC1 - Blocklist Dashboard:** Given I have companies blocklisted, when I view Privacy Proof, then I see each blocklisted company with "Last checked" timestamp and "0 exposures" verification.
2. **AC2 - Blocked Actions Log:** Given actions have been blocked for a company, when I view Privacy Proof, then I see a log of blocked actions (e.g., "Blocked match from [Company]").
3. **AC3 - Download Report:** Given I view Privacy Proof, when I click "Download Report", then I receive a JSON privacy report with all proof data.
4. **AC4 - Empty State:** Given I have no blocklisted companies, when I view Privacy Proof, then I see a message guiding me to add companies.

## Tasks / Subtasks

- [x]Task 1: Add backend privacy proof endpoint (AC: #1, #2, #3)
  - [x]1.1: Create `privacy_audit_log` table via CREATE TABLE IF NOT EXISTS (id, user_id, company_name, action_type, details, created_at)
  - [x]1.2: Add GET `/api/v1/privacy/proof` endpoint — returns blocklist entries with last_checked timestamp, exposure_count (always 0 for MVP), and recent blocked actions
  - [x]1.3: Add GET `/api/v1/privacy/proof/report` endpoint — returns downloadable JSON privacy report

- [x]Task 2: Add frontend privacy proof service hooks (AC: #1, #3)
  - [x]2.1: Add types `PrivacyProofEntry`, `PrivacyProofResponse` and hooks `usePrivacyProof()`, `useDownloadReport()` to `frontend/src/services/privacy.ts`

- [x]Task 3: Create Privacy Proof dashboard component (AC: #1, #2, #4)
  - [x]3.1: Create `frontend/src/components/privacy/PrivacyProof.tsx` — shows proof dashboard with blocklist verification
  - [x]3.2: Show each company with "Last checked" timestamp, "0 exposures" badge, blocked actions log
  - [x]3.3: Show empty state when no companies blocklisted
  - [x]3.4: Add "Download Report" button
  - [x]3.5: Integrate PrivacyProof into Privacy.tsx page below BlocklistManager

- [x]Task 4: Write comprehensive tests (AC: #1-#4)
  - [x]4.1: Write backend tests (>=3): proof with entries, proof empty, report download
  - [x]4.2: Write frontend tests (>=4): proof renders entries, blocked actions shown, download button, empty state

## Dev Notes

### Architecture Compliance
- Backend: raw SQL via `text()` with parameterized queries, lazy imports inside methods
- Backend: FastAPI endpoints in `app/api/v1/privacy.py` with `Depends(get_current_user_id)`
- Frontend: TanStack Query hooks in `frontend/src/services/privacy.ts`, `useApiClient()` pattern
- Frontend: React components with Tailwind CSS, no external UI libraries
- For MVP: exposure_count is always 0 (no real matching engine to cross-reference yet)
- last_checked is the current timestamp (system continuously validates)
- Blocked actions log uses privacy_audit_log table (populated by agents in future stories)

### File Structure Requirements

**Files to CREATE:**
```
frontend/src/components/privacy/PrivacyProof.tsx           # Proof dashboard component
frontend/src/__tests__/PrivacyProof.test.tsx               # Frontend tests
backend/tests/unit/test_api/test_privacy_proof_endpoints.py # API tests
```

**Files to MODIFY:**
```
backend/app/api/v1/privacy.py                              # Add proof endpoints
frontend/src/services/privacy.ts                           # Add proof hooks
frontend/src/pages/Privacy.tsx                             # Integrate PrivacyProof
```

### Previous Story Intelligence
- Story 6-10 created `privacy.py` with stealth endpoints
- Story 6-11 added blocklist endpoints and `employer_blocklist` table
- Story 6-11 created `BlocklistManager.tsx` component
- `employer_blocklist` table has: id, user_id, company_name, note, created_at
- Test pattern: patch `app.db.engine.AsyncSessionLocal`, `AsyncMock` + `MagicMock`
- Frontend test pattern: mock hooks from `../services/privacy`

### Testing Requirements
- **Backend Tests:** Test GET proof with entries (returns blocklist + last_checked + exposure_count), GET proof empty, GET report download
- **Frontend Tests:** Test proof dashboard renders entries with verification, blocked actions log, download button, empty state

## Dev Agent Record
### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)
### Route Taken
SIMPLE (score: 5/16)
### GSD Subagents Used
None (direct execution)
### Debug Log References
None
### Completion Notes List
- GET /api/v1/privacy/proof endpoint returning blocklist verification with last_checked, exposure_count, blocked_actions
- GET /api/v1/privacy/proof/report endpoint returning downloadable JSON privacy report
- privacy_audit_log table via CREATE TABLE IF NOT EXISTS
- usePrivacyProof and useDownloadReport hooks in privacy.ts
- PrivacyProof component with verification dashboard, blocked actions log, download button, empty state
- Integrated into Privacy.tsx page
- 8 new tests (3 backend + 5 frontend), all passing
### Change Log
- 2026-02-01: Story implemented and moved to review
### File List
**Created:**
- frontend/src/components/privacy/PrivacyProof.tsx
- frontend/src/__tests__/PrivacyProof.test.tsx
- backend/tests/unit/test_api/test_privacy_proof_endpoints.py

**Modified:**
- backend/app/api/v1/privacy.py
- frontend/src/services/privacy.ts
- frontend/src/pages/Privacy.tsx
