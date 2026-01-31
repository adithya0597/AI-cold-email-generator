---
phase: 01-foundation-modernization
plan: "06"
subsystem: frontend-auth
tags: [clerk, react, auth, protected-routes, typescript, tanstack-query]
dependency-graph:
  requires: [01-02, 01-04]
  provides: [clerk-react-integration, protected-routes, api-token-injection]
  affects: [02-*, 03-*]
tech-stack:
  added: []
  patterns: [provider-pattern, protected-route-pattern, hook-based-api-client]
key-files:
  created:
    - frontend/src/providers/ClerkProvider.tsx
    - frontend/src/providers/QueryProvider.tsx
    - frontend/src/pages/SignIn.tsx
    - frontend/src/pages/SignUp.tsx
    - frontend/src/pages/Dashboard.tsx
    - frontend/src/App.tsx
    - frontend/src/services/api.ts
  modified:
    - frontend/src/main.jsx
  deleted:
    - frontend/src/App.jsx
    - frontend/src/services/api.js
decisions:
  - "AuthProvider gracefully degrades when VITE_CLERK_PUBLISHABLE_KEY is missing (renders children without auth wrapper)"
  - "Legacy routes (email, linkedin, author-styles, settings) remain public; only /dashboard is protected"
  - "Public api instance preserved for unauthenticated calls; useApiClient hook for authenticated calls"
metrics:
  duration: ~4 min
  completed: 2026-01-31
---

# Phase 1 Plan 06: Frontend Auth (Clerk React) + Protected Routes Summary

Clerk React SDK integrated into Vite frontend with provider pattern, sign-in/sign-up pages using Clerk components, protected dashboard route with SignedIn/SignedOut guards, and TypeScript API service with JWT token injection via useApiClient hook.

## Tasks Completed

### Task 1: Set up Clerk provider and auth pages (67f6a36)

- Created `AuthProvider` in `providers/ClerkProvider.tsx` wrapping `@clerk/clerk-react` ClerkProvider with graceful fallback when publishable key is missing
- Created `QueryProvider` in `providers/QueryProvider.tsx` wrapping TanStack Query with sensible defaults (5min stale time, 1 retry)
- Converted `App.jsx` to `App.tsx` with full route structure:
  - Public routes: `/`, `/sign-in/*`, `/sign-up/*`
  - Legacy public routes: `/email`, `/linkedin`, `/author-styles`, `/settings`
  - Protected route: `/dashboard` (wrapped in `ProtectedRoute` using `SignedIn`/`SignedOut`/`RedirectToSignIn`)
- Created `SignIn.tsx` and `SignUp.tsx` pages using Clerk's pre-built components with path-based routing
- Created `Dashboard.tsx` page showing user info (name, email, ID, join date) from `useUser()` with `UserButton` for sign-out
- Updated `main.jsx` to wrap App with `AuthProvider` > `QueryProvider`
- Added `UserButton` (signed in) and Sign In link (signed out) to navigation bar
- Renamed app title from "AI Content Suite" to "JobPilot"

### Task 2: Update API service with Clerk token injection (faae776)

- Converted `api.js` to `api.ts` with full TypeScript types
- Created `useApiClient()` hook using `useAuth()` from Clerk to get `getToken()`
- Axios request interceptor attaches `Authorization: Bearer <token>` header to every request
- Public `api` instance preserved for unauthenticated calls (health checks)
- Updated 401 response handler to redirect to `/sign-in` (Clerk route) instead of `/login`
- Legacy service wrappers (emailService, linkedInService, utilityService) preserved for backward compatibility

## Deviations from Plan

None -- plan executed exactly as written.

## Verification

- `npm run build` (vite build) completes successfully with 0 errors
- All TypeScript files compile without issues
- 284 modules transformed in ~2s build time

## Next Phase Readiness

- Clerk publishable key must be set in `.env` (VITE_CLERK_PUBLISHABLE_KEY) for auth to function
- Backend Clerk JWT verification (Plan 04) is already in place
- Frontend and backend auth are now aligned on Clerk JWT flow
