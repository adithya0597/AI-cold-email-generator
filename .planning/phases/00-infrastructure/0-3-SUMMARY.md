# Phase 0 Plan 3: Clerk Authentication Integration Summary

**One-liner:** User sync endpoint + ProtectedRoute with auto-sync, new user onboarding redirect, and Outlet-based route protection

## What Was Done

### Task 1: Create user sync endpoint
- Created `backend/app/api/v1/auth.py` with `POST /api/v1/auth/sync`
- Endpoint uses `get_current_user_id` from existing clerk.py to extract clerk_id
- Upserts User record by clerk_id (find or create)
- Returns `{ user: { id, clerk_id, email, tier }, is_new: bool }`
- Registered auth router in `backend/app/api/v1/router.py`
- Commit: b75dd30

### Task 2: Add frontend auth routing
- Created `frontend/src/components/auth/ProtectedRoute.tsx` using Outlet pattern
- ProtectedRoute checks `useAuth()` from Clerk, redirects to /sign-in if unauthenticated
- On mount, calls POST /api/v1/auth/sync via useApiClient() to ensure user record exists
- New users (is_new=true) are navigated to /onboarding
- Updated `frontend/src/pages/SignUp.tsx` afterSignUpUrl from /dashboard to /onboarding
- Refactored `frontend/src/App.tsx` to use nested Route with ProtectedRoute element (Outlet pattern)
- Sign-out already handled by Clerk's `UserButton afterSignOutUrl="/"` in nav bar
- Commit: eafa778

### Task 3: Write tests
- Backend: 4 tests in `backend/tests/unit/test_api/test_auth_sync.py`
  - New user creation (is_new=true, DB add called)
  - Returning user lookup (is_new=false, existing data returned)
  - Unauthorized request rejection (401/422 without auth)
  - Response schema validation (user fields + is_new flag)
- Frontend: 6 tests in `frontend/src/components/auth/__tests__/ProtectedRoute.test.tsx`
  - Renders nothing while Clerk loading
  - Redirects to /sign-in when not signed in
  - Renders child route when signed in
  - Calls sync API on mount
  - Does not call sync when unauthenticated
  - Navigates new user to /onboarding
- Commit: 7b7e66d

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SignUp.tsx already existed with wrong afterSignUpUrl**
- **Found during:** Task 2
- **Issue:** SignUp.tsx already existed (plan said CREATE) with afterSignUpUrl="/dashboard" instead of "/onboarding"
- **Fix:** Modified existing file to change afterSignUpUrl to "/onboarding"
- **Files modified:** frontend/src/pages/SignUp.tsx

**2. [Rule 1 - Bug] App.tsx inline ProtectedRoute replaced**
- **Found during:** Task 2
- **Issue:** App.tsx already had an inline ProtectedRoute function using SignedIn/SignedOut/RedirectToSignIn pattern without user sync
- **Fix:** Replaced with imported ProtectedRoute component using Outlet pattern with user sync
- **Files modified:** frontend/src/App.tsx

## Decisions Made

- ProtectedRoute uses React Router Outlet pattern (layout route) instead of wrapper-children pattern for cleaner nesting
- User sync is fire-and-forget on mount (non-blocking) -- sync failure logged but does not prevent route rendering
- syncCalled ref prevents duplicate sync calls on re-renders
- Placeholder email uses `{clerk_id}@pending.sync` format (Clerk manages real email)

## Files

### Created
- `backend/app/api/v1/auth.py`
- `frontend/src/components/auth/ProtectedRoute.tsx`
- `backend/tests/unit/test_api/test_auth_sync.py`
- `frontend/src/components/auth/__tests__/ProtectedRoute.test.tsx`

### Modified
- `backend/app/api/v1/router.py`
- `frontend/src/pages/SignUp.tsx`
- `frontend/src/App.tsx`

## Metrics

- **Duration:** ~5 min
- **Completed:** 2026-02-01
- **Tests:** 10 total (4 backend, 6 frontend), all passing
