# Story 6.10: Stealth Mode Activation

Status: review

## Story

As a **Career Insurance user**,
I want **to enable Stealth Mode to hide my job search**,
So that **my current employer cannot discover I'm looking**.

## Acceptance Criteria

1. **AC1 - Tier Check:** Given I navigate to Settings > Privacy, when my tier is not `career_insurance` or `enterprise`, then the Stealth Mode toggle is disabled with an upgrade prompt.
2. **AC2 - Privacy Toggle:** Given I have Career Insurance tier, when I navigate to Settings > Privacy, then I see a "Stealth Mode" toggle.
3. **AC3 - Explanation on Enable:** Given I toggle Stealth Mode on, when the toggle activates, then I see an explanation of what Stealth Mode does (profile hidden, blocklist activated, agents avoid public visibility).
4. **AC4 - Activation Effects:** Given Stealth Mode is enabled, when the system processes my data, then my profile is hidden from public search, employer blocklist is activated, and all agent actions avoid public visibility.
5. **AC5 - Active Badge:** Given Stealth Mode is enabled, when I view any page, then I see a "Stealth Mode Active" badge in the navigation.

## Tasks / Subtasks

- [x]Task 1: Add backend stealth mode endpoints (AC: #1, #2, #4)
  - [x]1.1: Create `backend/app/api/v1/privacy.py` with APIRouter prefix `/privacy`
  - [x]1.2: Add GET `/api/v1/privacy/stealth` endpoint — returns `{stealth_enabled, tier, eligible}` for current user
  - [x]1.3: Add POST `/api/v1/privacy/stealth` endpoint — toggles stealth mode on/off, validates tier is `career_insurance` or `enterprise`, returns 403 if ineligible
  - [x]1.4: Create `stealth_settings` table via CREATE TABLE IF NOT EXISTS (id, user_id UNIQUE, stealth_enabled BOOLEAN DEFAULT FALSE, enabled_at TIMESTAMPTZ, created_at TIMESTAMPTZ)
  - [x]1.5: Register privacy router in `backend/app/api/v1/__init__.py`

- [x]Task 2: Add frontend stealth mode service hooks (AC: #1, #2)
  - [x]2.1: Create `frontend/src/services/privacy.ts` with types `StealthStatus` and hooks `useStealthStatus()`, `useToggleStealth()`
  - [x]2.2: `useStealthStatus()` calls GET `/api/v1/privacy/stealth`, returns `{stealth_enabled, tier, eligible}`
  - [x]2.3: `useToggleStealth()` mutation calls POST `/api/v1/privacy/stealth` with `{enabled: boolean}`

- [x]Task 3: Create Privacy settings page with Stealth Mode toggle (AC: #1, #2, #3)
  - [x]3.1: Create `frontend/src/pages/Privacy.tsx` — Settings > Privacy page
  - [x]3.2: Show "Stealth Mode" toggle, disabled with upgrade prompt when `eligible === false`
  - [x]3.3: On toggle enable, show explanation panel: "Your profile is hidden from public search. Employer blocklist is activated. All agent actions avoid public visibility."
  - [x]3.4: Add `/privacy` route to App.tsx with OnboardingGuard, add "Privacy" nav link in Settings section or as sub-route

- [x]Task 4: Add Stealth Mode Active badge to navigation (AC: #5)
  - [x]4.1: In App.tsx navigation, when stealth is enabled, show a small "Stealth" badge near the user area
  - [x]4.2: Badge uses green/dark styling to indicate active stealth

- [x]Task 5: Write comprehensive tests (AC: #1-#5)
  - [x]5.1: Write backend tests (>=3): get stealth status, toggle on (eligible), toggle on (ineligible → 403)
  - [x]5.2: Write frontend tests (>=5): toggle renders, disabled when ineligible, explanation shown on enable, badge visible when active, upgrade prompt shown

## Dev Notes

### Architecture Compliance
- Backend: raw SQL via `text()` with parameterized queries, lazy imports inside methods
- Backend: FastAPI endpoints with `Depends(get_current_user_id)`, new router in `app/api/v1/privacy.py`
- Frontend: TanStack Query hooks in `frontend/src/services/privacy.ts`, `useApiClient()` pattern
- Frontend: React components with Tailwind CSS, no external UI libraries
- Tier check: Query `users` table for `tier` column, check if `career_insurance` or `enterprise`
- Table creation uses CREATE TABLE IF NOT EXISTS pattern (same as followup_agent.py)

### File Structure Requirements

**Files to CREATE:**
```
backend/app/api/v1/privacy.py                              # Privacy/stealth endpoints
frontend/src/services/privacy.ts                           # Query hooks
frontend/src/pages/Privacy.tsx                             # Privacy settings page
frontend/src/__tests__/Privacy.test.tsx                    # Frontend tests
backend/tests/unit/test_api/test_privacy_endpoints.py      # API tests
```

**Files to MODIFY:**
```
backend/app/api/v1/__init__.py                             # Register privacy router
frontend/src/App.tsx                                       # Add /privacy route + nav + stealth badge
```

### Previous Story Intelligence
- `users` table has `tier` column with enum: free, pro, h1b_pro, career_insurance, enterprise
- `users.py` has `/me` endpoint returning user_id — pattern for auth-based queries
- `applications.py` pattern: raw SQL with `text()`, lazy import `AsyncSessionLocal`, `Depends(get_current_user_id)`
- App.tsx route pattern: `<Route path="/privacy" element={<OnboardingGuard><Privacy /></OnboardingGuard>} />`
- Settings nav link already exists in App.tsx — Privacy can be a sibling nav item or sub-route
- Test pattern: patch `app.db.engine.AsyncSessionLocal`, `AsyncMock` + `MagicMock`
- Frontend test pattern: mock hooks from service files, render with QueryClientProvider + MemoryRouter

### Testing Requirements
- **Backend Tests:** Test GET stealth status (returns current state + eligibility), POST toggle on (career_insurance tier → success), POST toggle on (free tier → 403)
- **Frontend Tests:** Test toggle renders enabled for eligible user, toggle disabled with upgrade prompt for ineligible, explanation panel shows on enable, stealth badge visible in nav, upgrade prompt text

## Dev Agent Record
### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)
### Route Taken
SIMPLE (score: 6/16)
### GSD Subagents Used
None (direct execution)
### Debug Log References
- Fixed App.test.tsx regression: added useStealthStatus mock to prevent QueryClient error
### Completion Notes List
- GET /api/v1/privacy/stealth endpoint returning stealth_enabled, tier, eligible
- POST /api/v1/privacy/stealth endpoint with tier validation (403 for ineligible)
- stealth_settings table via CREATE TABLE IF NOT EXISTS
- Privacy router registered in router.py
- useStealthStatus and useToggleStealth hooks in privacy.ts
- Privacy page with toggle, explanation panel, upgrade prompt
- /privacy route added to App.tsx with OnboardingGuard
- "Stealth" badge in navigation when stealth is active (dark/green styling)
- 12 new tests (5 backend + 7 frontend), all passing
### Change Log
- 2026-02-01: Story implemented and moved to review
### File List
**Created:**
- backend/app/api/v1/privacy.py
- frontend/src/services/privacy.ts
- frontend/src/pages/Privacy.tsx
- frontend/src/__tests__/Privacy.test.tsx
- backend/tests/unit/test_api/test_privacy_endpoints.py

**Modified:**
- backend/app/api/v1/router.py
- frontend/src/App.tsx
- frontend/src/App.test.tsx
