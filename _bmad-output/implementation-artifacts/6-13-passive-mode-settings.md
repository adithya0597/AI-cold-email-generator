# Story 6.13: Passive Mode Settings

Status: review

## Story

As a **Career Insurance user**,
I want **to configure passive job search behavior**,
So that **I stay ready without active effort**.

## Acceptance Criteria

1. **AC1 - Tier Check:** Given I am not a Career Insurance or Enterprise subscriber, when I view Passive Mode settings, then the controls are disabled with an upgrade prompt.
2. **AC2 - Search Frequency:** Given I am eligible, when I configure Passive Mode, then I can set search frequency (weekly or daily).
3. **AC3 - Match Threshold:** Given I am eligible, when I configure Passive Mode, then I can set minimum match score to surface (higher = fewer, better matches).
4. **AC4 - Notification Preferences:** Given I am eligible, when I configure Passive Mode, then I can set notification preferences (weekly digest or immediate for hot matches).
5. **AC5 - Auto-save Threshold:** Given I am eligible, when I configure Passive Mode, then I can set auto-save threshold (automatically save jobs above X score).
6. **AC6 - Sprint Mode Activation:** Given I am in Passive Mode, when I click "Activate Sprint Mode", then all settings switch to active/daily mode instantly.

## Tasks / Subtasks

- [x]Task 1: Add backend passive mode endpoints (AC: #1-#6)
  - [x]1.1: Create `passive_mode_settings` table via CREATE TABLE IF NOT EXISTS (id, user_id UNIQUE, search_frequency, min_match_score, notification_pref, auto_save_threshold, mode, created_at, updated_at)
  - [x]1.2: Add GET `/api/v1/privacy/passive-mode` endpoint — returns current settings + tier eligibility
  - [x]1.3: Add PUT `/api/v1/privacy/passive-mode` endpoint — updates settings, validates tier
  - [x]1.4: Add POST `/api/v1/privacy/passive-mode/sprint` endpoint — switches to sprint mode (daily frequency, low thresholds)

- [x]Task 2: Add frontend passive mode service hooks (AC: #1-#6)
  - [x]2.1: Add types `PassiveModeSettings`, `PassiveModeResponse` and hooks `usePassiveMode()`, `useUpdatePassiveMode()`, `useActivateSprint()` to `frontend/src/services/privacy.ts`

- [x]Task 3: Create Passive Mode settings component (AC: #1-#6)
  - [x]3.1: Create `frontend/src/components/privacy/PassiveModeSettings.tsx` — settings form with frequency, threshold, notifications, auto-save
  - [x]3.2: Show disabled state with upgrade prompt for ineligible tiers
  - [x]3.3: Add "Activate Sprint Mode" button that switches to active settings
  - [x]3.4: Integrate into Privacy.tsx page

- [x]Task 4: Write comprehensive tests (AC: #1-#6)
  - [x]4.1: Write backend tests (>=3): get settings, update settings, activate sprint, ineligible → 403
  - [x]4.2: Write frontend tests (>=4): settings render, update form, sprint activation, upgrade prompt

## Dev Notes

### Architecture Compliance
- Backend: raw SQL via `text()` with parameterized queries, lazy imports inside methods
- Backend: FastAPI endpoints in `app/api/v1/privacy.py` with `Depends(get_current_user_id)`
- Frontend: TanStack Query hooks in `frontend/src/services/privacy.ts`, `useApiClient()` pattern
- Frontend: React components with Tailwind CSS, no external UI libraries
- Tier check: reuse ELIGIBLE_TIERS from stealth endpoints
- Default passive settings: frequency=weekly, min_match_score=70, notification_pref=weekly_digest, auto_save_threshold=85, mode=passive

### File Structure Requirements

**Files to CREATE:**
```
frontend/src/components/privacy/PassiveModeSettings.tsx    # Settings component
frontend/src/__tests__/PassiveMode.test.tsx                # Frontend tests
backend/tests/unit/test_api/test_passive_mode_endpoints.py # API tests
```

**Files to MODIFY:**
```
backend/app/api/v1/privacy.py                              # Add passive mode endpoints
frontend/src/services/privacy.ts                           # Add passive mode hooks
frontend/src/pages/Privacy.tsx                             # Integrate PassiveModeSettings
```

### Previous Story Intelligence
- Story 6-10 created privacy.py with ELIGIBLE_TIERS = {"career_insurance", "enterprise"}
- Story 6-10 pattern for tier checking: query users table for tier, compare against ELIGIBLE_TIERS
- Test pattern: patch `app.db.engine.AsyncSessionLocal`, `AsyncMock` + `MagicMock`

### Testing Requirements
- **Backend Tests:** Test GET passive mode (returns settings + eligibility), PUT update (success), POST sprint activation, PUT for ineligible tier (403)
- **Frontend Tests:** Test settings form renders, update saves settings, sprint activation button, upgrade prompt for ineligible

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
- GET /api/v1/privacy/passive-mode endpoint returning settings + tier eligibility
- PUT /api/v1/privacy/passive-mode endpoint with tier validation and upsert
- POST /api/v1/privacy/passive-mode/sprint endpoint switching to sprint mode
- passive_mode_settings table via CREATE TABLE IF NOT EXISTS
- usePassiveMode, useUpdatePassiveMode, useActivateSprint hooks
- PassiveModeSettings component with frequency, match threshold, notifications, auto-save, sprint activation
- Integrated into Privacy.tsx page
- 10 new tests (5 backend + 5 frontend), all passing
### Change Log
- 2026-02-01: Story implemented and moved to review
### File List
**Created:**
- frontend/src/components/privacy/PassiveModeSettings.tsx
- frontend/src/__tests__/PassiveMode.test.tsx
- backend/tests/unit/test_api/test_passive_mode_endpoints.py

**Modified:**
- backend/app/api/v1/privacy.py
- frontend/src/services/privacy.ts
- frontend/src/pages/Privacy.tsx
