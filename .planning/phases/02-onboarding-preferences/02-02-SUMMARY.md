---
phase: 02-onboarding-preferences
plan: 02
subsystem: analytics
tags: [posthog, analytics, tracking, infrastructure]
dependency-graph:
  requires: [01-04]
  provides: [analytics-service, analytics-hook, analytics-provider]
  affects: [02-06]
tech-stack:
  added: [posthog (backend), posthog-js (frontend)]
  patterns: [fire-and-forget analytics, graceful degradation when unconfigured]
key-files:
  created:
    - backend/app/services/analytics_service.py
    - frontend/src/providers/AnalyticsProvider.tsx
    - frontend/src/hooks/useAnalytics.ts
  modified:
    - backend/requirements.txt
    - backend/app/config.py
    - backend/.env.example
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/src/main.jsx
    - frontend/.env.example
decisions:
  - Decoupled AnalyticsProvider from Clerk useUser to avoid crash when Clerk key is missing; user identification via separate identifyUser() export
metrics:
  duration: ~3 min
  completed: 2026-01-31
---

# Phase 2 Plan 02: PostHog Analytics Infrastructure Summary

PostHog analytics wired on both backend (Python SDK wrapper) and frontend (React provider + hook), all gracefully no-op when API keys are empty.

## What Was Done

### Task 1: Backend PostHog Setup (commit 6da5861)

- Added `posthog>=3.0.0` to `backend/requirements.txt`
- Added `POSTHOG_API_KEY` and `POSTHOG_HOST` fields to `Settings` class in `backend/app/config.py`
- Created `backend/app/services/analytics_service.py` with:
  - `track_event(user_id, event, properties)` -- fire-and-forget event tracking
  - `identify_user(user_id, properties)` -- user identification
  - Lazy initialization on first call
  - Silent no-op when `POSTHOG_API_KEY` is empty
  - All exceptions caught and logged at debug level
- Added `POSTHOG_API_KEY` and `POSTHOG_HOST` to `backend/.env.example`

### Task 2: Frontend PostHog Setup (commit f256a73)

- Installed `posthog-js` via npm
- Created `frontend/src/providers/AnalyticsProvider.tsx`:
  - Initializes PostHog on mount (once) with lazy flag
  - Enables debug mode in development
  - Exports `identifyUser()` for post-auth user identification
  - No-ops when `VITE_POSTHOG_KEY` is empty
- Created `frontend/src/hooks/useAnalytics.ts`:
  - `useAnalytics()` hook returns `{ track }` function
  - Wraps `posthog.capture()` in try/catch
  - No-ops when key is empty
- Wired `<AnalyticsProvider>` into `main.jsx` between `AuthProvider` and `QueryProvider`
- Added `VITE_POSTHOG_KEY` and `VITE_POSTHOG_HOST` to `frontend/.env.example`

## Decisions Made

1. **Decoupled from Clerk useUser**: The plan suggested using `useUser()` inside AnalyticsProvider for auto-identification. Since AuthProvider renders children without ClerkProvider when the key is missing, calling `useUser()` would crash. Instead, exported a standalone `identifyUser()` function that consumers call after auth is confirmed. This keeps the provider safe regardless of Clerk configuration.

## Deviations from Plan

None -- plan executed as written with one minor design adjustment documented above.

## Acceptance Criteria Verification

- [x] `posthog` in backend requirements.txt
- [x] `posthog-js` in frontend package.json
- [x] Analytics service and hook both gracefully no-op when API keys are not set
- [x] Provider wraps the app tree (in main.jsx)
- [x] `.env.example` files document the new env vars (both backend and frontend)

## Next Phase Readiness

Plan 02 is pure infrastructure. Plan 06 (Preference Wizard) will wire actual analytics events using `useAnalytics()` on the frontend and `track_event()` on the backend. No blockers.
