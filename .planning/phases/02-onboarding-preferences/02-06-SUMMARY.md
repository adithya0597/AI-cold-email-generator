---
phase: "02"
plan: "06"
name: "Preference Wizard Frontend + Integration Wiring"
status: complete
subsystem: frontend-preferences
tags: [react, preferences, wizard, react-hook-form, zod, zustand, analytics, posthog, onboarding-guard]
depends_on:
  requires: ["02-04", "02-05"]
  provides: ["preference-wizard-ui", "onboarding-guard", "full-onboarding-flow", "analytics-events"]
  affects: ["03-*"]
tech_stack:
  added: []
  patterns: ["multi-step-wizard", "per-step-server-save", "chip-picker", "tag-input", "route-guard", "analytics-event-tracking"]
key_files:
  created:
    - frontend/src/components/preferences/TagInput.tsx
    - frontend/src/components/preferences/ChipPicker.tsx
    - frontend/src/components/preferences/JobTypeStep.tsx
    - frontend/src/components/preferences/LocationStep.tsx
    - frontend/src/components/preferences/SalaryStep.tsx
    - frontend/src/components/preferences/DealBreakerStep.tsx
    - frontend/src/components/preferences/H1BStep.tsx
    - frontend/src/components/preferences/AutonomyStep.tsx
    - frontend/src/components/preferences/SummaryStep.tsx
    - frontend/src/pages/Preferences.tsx
    - frontend/src/providers/OnboardingGuard.tsx
  modified:
    - frontend/src/App.tsx
decisions:
  - Each preference step manages its own navigation buttons (consistent with onboarding steps from Plan 05)
  - TagInput and ChipPicker extracted as shared components in preferences/ (reusable for other forms)
  - OnboardingGuard gracefully allows through on API error to avoid blocking users
  - SummaryStep shows "Not specified -- agent will consider all options" for skipped sections (Story 2-8)
  - Preferences page resets Zustand store on successful final submit to prevent stale state on revisit
metrics:
  duration: "~8 min"
  completed: "2026-01-31"
---

# Phase 2 Plan 06: Preference Wizard Frontend + Integration Wiring Summary

**7-step preference wizard with OnboardingGuard, route wiring, and all 13 analytics events**

## What Was Built

### Task 1: Preference Wizard Step Components (7 steps + 2 shared)

9 new components in `frontend/src/components/preferences/`:

- **TagInput.tsx**: Reusable tag input (type + Enter to add, Backspace to remove). Used by JobType (titles), Location (cities), DealBreaker (companies/industries).
- **ChipPicker.tsx**: Multi-select chip grid. Used by JobType (categories/seniority), DealBreaker (benefits).
- **JobTypeStep.tsx**: Multi-select chips for categories (11 options) and seniority (8 levels), tag input for target titles. Zod validation requires at least 1 of each.
- **LocationStep.tsx**: Radio group for work arrangement (4 options), conditional target location tags (hidden for Remote Only), excluded location tags, relocate checkbox.
- **SalaryStep.tsx**: Dollar-formatted number inputs for min/target, radio groups for flexibility (firm/negotiable) and comp type (base/total). Privacy note banner.
- **DealBreakerStep.tsx**: Must-haves section (min company size, benefits chips) and Never-haves section (excluded companies/industries tags, travel slider 0-100%, no-oncall checkbox). Warning banner about auto-filtering.
- **H1BStep.tsx**: H1B and green card sponsorship toggles. Conditional visa detail fields (visa type dropdown, expiration date picker) shown when either toggle is on. H1B Pro upsell note.
- **AutonomyStep.tsx**: 4 radio cards (L0-L3) with icons, titles, descriptions. L0 has "Recommended" badge. Note about changing in Settings.
- **SummaryStep.tsx**: Read-only card layout showing all 6 sections. Each section has Edit button (navigates back to that step). Skipped sections show "Not specified" empty state. Tip banner encouraging completeness. "Start My Agent" button with loading state.

### Task 2: Preferences Page, OnboardingGuard, Route Wiring

- **Preferences.tsx**: Multi-step controller using `usePreferenceStore` Zustand store. Loads existing preferences from `GET /api/v1/preferences` on mount. Each step's onSubmit saves to Zustand AND calls `PATCH /api/v1/preferences/{section}`. Final submit via `PUT /api/v1/preferences`. Toast confirmation on success, redirect to /dashboard, store reset.
- **OnboardingGuard.tsx**: Route guard that checks `GET /api/v1/onboarding/status`:
  - `not_started` / `profile_pending` -> redirects to `/onboarding`
  - `profile_complete` / `preferences_pending` -> redirects to `/preferences`
  - `complete` -> renders children
  - API error -> allows through (graceful degradation)
- **App.tsx**: Added `/preferences` protected route. Wrapped `/dashboard` with `OnboardingGuard`. Legacy routes remain public.

### Task 3: Analytics Event Verification

All 13 required events verified present:
1. `onboarding_started` (Onboarding.tsx)
2. `profile_extraction_method_chosen` (ResumeUpload.tsx)
3. `resume_uploaded` (ResumeUpload.tsx)
4. `profile_extraction_completed` (ResumeUpload.tsx)
5. `profile_extraction_failed` (ResumeUpload.tsx)
6. `profile_review_started` (ProfileReview.tsx)
7. `profile_confirmed` (ProfileReview.tsx)
8. `briefing_preview_viewed` (BriefingPreview.tsx)
9. `preference_wizard_started` (Preferences.tsx)
10. `preference_step_completed` x6 (Preferences.tsx, per step)
11. `preference_step_skipped` (Preferences.tsx)
12. `preferences_confirmed` (Preferences.tsx)
13. `onboarding_completed` (Preferences.tsx)

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

1. **Each preference step manages its own nav buttons**: Consistent with the pattern established in Plan 05 where onboarding steps also manage their own navigation. WizardShell is used for the step indicator only.
2. **TagInput and ChipPicker as shared components**: Extracted into the preferences/ directory rather than shared/ since they are preference-specific in styling and behavior. Can be moved to shared/ later if needed elsewhere.
3. **OnboardingGuard allows through on API failure**: To avoid blocking authenticated users from accessing the dashboard when the backend is temporarily unavailable.
4. **Store reset on final submit**: Prevents stale preference data from appearing if the user revisits /preferences later.

## Full Flow (End-to-End)

```
Sign up -> Clerk auth -> /dashboard -> OnboardingGuard checks status
  -> not_started: redirect to /onboarding
    -> Step 0: ResumeUpload (drag-drop PDF/DOCX or LinkedIn URL)
    -> Step 1: ProfileReview (edit extracted data)
    -> Step 2: BriefingPreview ("magic moment")
    -> Navigate to /preferences
  -> /preferences wizard:
    -> Step 0: JobType (categories, titles, seniority)
    -> Step 1: Location (arrangement, cities, exclusions)
    -> Step 2: Salary (min/target, flexibility, comp type)
    -> Step 3: DealBreakers (must-haves, never-haves)
    -> Step 4: H1B (sponsorship, visa details)
    -> Step 5: Autonomy (L0-L3)
    -> Step 6: Summary (review + "Start My Agent")
  -> PUT /api/v1/preferences -> status = complete
  -> Redirect to /dashboard (OnboardingGuard passes)
```

## Next Phase Readiness

Phase 2 is now complete. All 6 plans delivered:
- Database schema + models (Plan 01)
- Analytics infrastructure (Plan 02)
- Resume upload + profile extraction backend (Plan 03)
- Preferences backend + shared components (Plan 04)
- Onboarding frontend flow (Plan 05)
- Preference wizard + integration wiring (Plan 06)

Ready for Phase 3: Agent orchestration framework.
