---
phase: "02"
plan: "05"
name: "Onboarding Frontend Flow"
status: complete
subsystem: frontend-onboarding
tags: [react, onboarding, drag-drop, react-dropzone, react-hook-form, zustand, tanstack-query]
depends_on:
  requires: ["02-03", "02-04"]
  provides: ["onboarding-frontend-flow", "resume-upload-ui", "profile-review-ui", "briefing-preview"]
  affects: ["02-06"]
tech_stack:
  added: []
  patterns: ["multi-step-wizard", "zustand-persistence", "tanstack-query-mutations", "react-dropzone", "inline-editing"]
key_files:
  created:
    - frontend/src/components/onboarding/ResumeUpload.tsx
    - frontend/src/components/onboarding/ProfileReview.tsx
    - frontend/src/components/onboarding/BriefingPreview.tsx
    - frontend/src/pages/Onboarding.tsx
  modified:
    - frontend/src/App.tsx
decisions:
  - Each onboarding step manages its own navigation buttons rather than using WizardShell nav (step indicator only)
  - ProfileReview uses react-hook-form with useFieldArray for dynamic experience/education entries
  - SkillTagInput is a dedicated sub-component within ProfileReview (not extracted to shared)
metrics:
  duration: "~6 min"
  completed: "2026-01-31"
---

# Phase 2 Plan 05: Onboarding Frontend Flow Summary

**One-liner:** Complete onboarding UI flow with react-dropzone resume upload, inline profile editing via react-hook-form, and personalized briefing preview "magic moment"

## What Was Built

### Task 1: ResumeUpload Component (e17dc05)
- Drag-and-drop resume upload using `react-dropzone` (PDF/DOCX, 10MB max)
- File size and type validation with clear error messages
- Upload progress indicator with animated bar
- LinkedIn URL secondary input with `linkedin.com/in/` validation
- 15-second timeout for LinkedIn extraction with fallback messaging
- Loading states: "Your agent is reading your resume/profile..."
- Error states: image-based PDF detection, network errors, LinkedIn failures
- Analytics: `resume_uploaded`, `profile_extraction_method_chosen`, `profile_extraction_completed/failed`

### Task 2: ProfileReview + BriefingPreview Components (d71f3f1)
- **ProfileReview**: Full inline editing form using `react-hook-form` with `useFieldArray`
  - Editable fields: name (required), headline, phone, skills (tag input), experience (dynamic cards), education (dynamic cards)
  - SkillTagInput: Enter to add, Backspace to remove, chip-style display
  - Validation: name required, at least 1 experience with company + title
  - EmptyState shown when extraction yielded < 3 populated fields
  - Add/remove buttons for experience and education entries
  - Analytics: `profile_review_started`, `profile_confirmed` with `fields_edited_count`

- **BriefingPreview**: "Magic moment" page personalized with user's name
  - "Good morning, {firstName}!" greeting in gradient header
  - 3 mock job cards with match scores (92%, 87%, 84%), locations, salary ranges, skill tags
  - Grayed-out approval actions (thumbs up/down) as visual preview
  - "Preview -- Your first real briefing arrives tomorrow" label
  - Motivational copy about AI agent working 24/7
  - "Continue to Preferences" button navigates to `/preferences`
  - Analytics: `briefing_preview_viewed`

### Task 3: Onboarding Page + Routing (1e3c34a)
- Multi-step controller: Step 0 (ResumeUpload) -> Step 1 (ProfileReview) -> Step 2 (BriefingPreview)
- On mount: checks `GET /api/v1/onboarding/status` via TanStack Query
  - Redirects to `/dashboard` if complete
  - Redirects to `/preferences` if preferences_pending
  - Skips to step 2 if profile_complete
  - Tracks `onboarding_started` if not_started
- Profile confirmation: `useMutation` calling `PUT /api/v1/onboarding/profile/confirm`
- Progress persists across page refreshes via Zustand `persist` middleware
- WizardShell wraps all steps for consistent step indicator display
- App.tsx: `/onboarding` route added as `ProtectedRoute`

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

1. **Step navigation owned by each component**: Rather than using WizardShell's Back/Next/Skip buttons, each step component manages its own navigation (ResumeUpload triggers next on success, ProfileReview has its own Back/Confirm buttons, BriefingPreview has Continue button). WizardShell is used only for the step indicator.

2. **SkillTagInput as local component**: The skill tag input is defined within ProfileReview.tsx rather than extracted to shared/ -- it's specific enough to onboarding that sharing is premature.

3. **Confirming state in parent**: Profile confirmation loading state is managed in the Onboarding page (parent) rather than ProfileReview, so the parent can control step advancement after mutation success.

## Verification

- All TypeScript files follow existing patterns (strict: false, allowJs: true)
- All imports reference existing modules from Plans 02-04
- Components use established patterns: useApiClient, useAnalytics, useOnboardingStore
- Build verification was not possible due to sandbox restrictions on npm/node execution

## Next Step Readiness

**Plan 06 (Preference Wizard Frontend + Integration Wiring)** is unblocked:
- All onboarding components exist and are routed
- Zustand stores (useOnboardingStore, usePreferenceStore) are ready
- WizardShell, StepIndicator, EmptyState shared components available
- BriefingPreview's "Continue to Preferences" navigates to `/preferences`
- App.tsx is ready for the `/preferences` route addition
