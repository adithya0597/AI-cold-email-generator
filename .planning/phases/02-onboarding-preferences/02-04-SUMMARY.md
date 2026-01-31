---
phase: "02"
plan: "04"
subsystem: preferences-api-shared-components
tags: [preferences, crud-api, fastapi, zod, zustand, wizard, typescript, react]
depends_on:
  requires: ["02-01"]
  provides: ["preferences-crud-api", "deal-breakers-endpoint", "wizard-shell", "step-indicator", "preference-types", "zod-schemas", "onboarding-stores"]
  affects: ["02-05", "02-06"]
tech_stack:
  added: ["@hookform/resolvers"]
  patterns: ["upsert-on-first-access", "per-section-patch", "zustand-persist", "zod-form-validation"]
key_files:
  created:
    - backend/app/api/v1/preferences.py
    - frontend/src/types/onboarding.ts
    - frontend/src/types/preferences.ts
    - frontend/src/components/shared/StepIndicator.tsx
    - frontend/src/components/shared/EmptyState.tsx
    - frontend/src/components/shared/WizardShell.tsx
    - frontend/src/hooks/useOnboarding.ts
  modified:
    - backend/app/api/v1/router.py
    - frontend/package.json
decisions:
  - id: "02-04-01"
    description: "ensure_user_exists dependency defined in preferences.py (Plan 03 may have not yet been executed); to be extracted to shared module when Plan 03 runs"
  - id: "02-04-02"
    description: "Zustand stores use arrays (not Sets) for completedSteps since Sets don't serialize to JSON"
  - id: "02-04-03"
    description: "Autonomy level 'l0' treated as 'not yet configured' for missing_sections logic"
metrics:
  duration: "~6 min"
  completed: "2026-01-31"
---

# Phase 2 Plan 04: Preferences API + Shared Frontend Components Summary

Preferences CRUD API with upsert pattern, per-section PATCH for wizard step saves, structured deal-breakers endpoint for agent querying, plus WizardShell/StepIndicator/EmptyState components with Zod schemas and Zustand stores.

## Tasks Completed

### Task 1: Preferences API Endpoints
- Created `backend/app/api/v1/preferences.py` with 5 endpoints:
  - `GET /preferences` -- full preferences with upsert on first access
  - `PUT /preferences` -- full upsert, transitions onboarding_status to "complete"
  - `PATCH /preferences/{section}` -- per-section update for wizard step persistence
  - `GET /preferences/summary` -- completion status with missing_sections list
  - `GET /preferences/deal-breakers` -- structured must_haves/never_haves for agents
- Pydantic schemas for all sections: JobType, Location, Salary, DealBreakers, H1B, Autonomy
- `ensure_user_exists` dependency creates User record on first authenticated access
- Registered router in `backend/app/api/v1/router.py`

### Task 2: Shared Frontend Components
- **TypeScript types** (`types/onboarding.ts`, `types/preferences.ts`):
  - ExtractedProfile, WorkExperience, Education, OnboardingStatus
  - All preference section types matching backend Pydantic schemas
  - Constants for job categories, seniority levels, work arrangements, benefits, visa types, autonomy levels
- **Zod schemas** (`types/preferences.ts`):
  - Per-step validation: jobTypeSchema, locationSchema, salarySchema, dealBreakerSchema, h1bSchema, autonomySchema
  - Used with `@hookform/resolvers` for react-hook-form integration
- **StepIndicator component**: horizontal progress with numbered steps, responsive mobile collapse
- **EmptyState component**: reusable card with icon, title, description, optional action button
- **WizardShell component**: layout wrapper with StepIndicator, content area, Back/Skip/Next navigation
- **Zustand stores** (`hooks/useOnboarding.ts`):
  - `useOnboardingStore`: currentStep, profileData, completedSteps with persist middleware
  - `usePreferenceStore`: currentStep, preferencesData, completedSteps with persist middleware

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ensure_user_exists dependency created in preferences.py**
- **Found during:** Task 1
- **Issue:** Plan 03 (onboarding) creates the `ensure_user_exists` dependency, but since Plan 04 runs in parallel with Plan 03, the dependency doesn't exist yet
- **Fix:** Defined `ensure_user_exists` directly in `preferences.py` with a comment noting it should be extracted to a shared module
- **Files modified:** `backend/app/api/v1/preferences.py`
- **Commit:** c5312fd

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| 02-04-01 | ensure_user_exists defined locally | Plan 03 may not have run yet; avoids cross-module dependency |
| 02-04-02 | Arrays for completedSteps | Sets don't serialize to JSON in Zustand persist |
| 02-04-03 | l0 = "not configured" in missing_sections | Default autonomy level treated as incomplete to encourage users to make an active choice |

## Verification Status

- Backend: preferences.py file created with correct route structure and Pydantic schemas
- Frontend: all component files created with correct TypeScript types
- Build verification: could not run `npm run build` due to environment restrictions; code follows existing patterns and all dependencies are installed

## Next Phase Readiness

Plan 04 is complete. Plan 05 (Onboarding Frontend Flow) and Plan 06 (Preference Wizard Frontend) can now use:
- WizardShell, StepIndicator, EmptyState components
- TypeScript types and Zod schemas
- Zustand stores for wizard state management
- Preferences API for server-side persistence
