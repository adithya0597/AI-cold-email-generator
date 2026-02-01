# Story 0.3: Clerk Authentication Integration

Status: done

## Story

As a **user**,
I want **to sign up and log in using my LinkedIn account**,
so that **I can access JobPilot quickly without creating another password**.

## Acceptance Criteria

1. **AC1 - LinkedIn OAuth Flow:** Given I am on the login page, when I click "Continue with LinkedIn", then I am redirected to LinkedIn OAuth flow via Clerk.

2. **AC2 - JWT Token Validation:** Given OAuth authentication succeeds, when the backend receives an authenticated request, then the JWT is validated against Clerk's JWKS endpoint and the user ID is extracted.

3. **AC3 - User Record Sync:** Given a JWT is validated, when the backend processes the request, then my `users` record is created (if new) or looked up (if returning) using the Clerk `sub` claim as `clerk_id`.

4. **AC4 - Post-Auth Navigation:** Given authentication completes, when I am redirected back to the app, then new users go to `/onboarding` and returning users go to `/dashboard`.

5. **AC5 - Protected Routes:** Given I am not authenticated, when I try to access a protected page, then I am redirected to `/sign-in`.

6. **AC6 - Sign Out:** Given I am logged in, when I click sign out, then my session is cleared and I am redirected to the sign-in page.

## Tasks / Subtasks

- [x] Task 1: Create user sync endpoint (AC: #3)
  - [x] 1.1: Create `backend/app/api/v1/auth.py` with `POST /api/v1/auth/sync` endpoint that: extracts clerk_id from JWT, creates User record if not exists (upsert by clerk_id), returns user data
  - [x] 1.2: Register auth router in `backend/app/api/v1/router.py`

- [x] Task 2: Add frontend auth routing (AC: #1, #4, #5, #6)
  - [x] 2.1: Create `frontend/src/components/auth/ProtectedRoute.tsx` that redirects to `/sign-in` if not authenticated, and calls user sync on first load
  - [x] 2.2: Create `frontend/src/pages/SignUp.tsx` with Clerk SignUp component
  - [x] 2.3: Update `frontend/src/App.tsx` to wrap protected routes with ProtectedRoute and add sign-in/sign-up routes
  - [x] 2.4: Add sign-out button/functionality to the layout or navigation

- [x] Task 3: Write tests (AC: #1-#6)
  - [x] 3.1: Create `backend/tests/unit/test_api/test_auth_sync.py` with tests for user sync endpoint: new user creation, returning user lookup, missing auth rejection
  - [x] 3.2: Create `frontend/src/components/auth/__tests__/ProtectedRoute.test.tsx` with tests for redirect behavior

## Dev Notes

### Architecture Compliance

**CRITICAL — Follow these patterns EXACTLY:**

1. **Clerk is ALREADY partially integrated.** The following files already exist and work:
   - `backend/app/auth/clerk.py` — JWT validation via `fastapi-clerk-auth`, exports `require_auth` and `get_current_user_id`
   - `frontend/src/providers/ClerkProvider.tsx` — Wraps app with `<ClerkProvider>`
   - `frontend/src/pages/SignIn.tsx` — Uses `<ClerkSignIn>` component
   - `frontend/src/services/api.ts` — `useApiClient()` hook auto-attaches JWT Bearer token
   [Source: backend/app/auth/clerk.py, frontend/src/providers/ClerkProvider.tsx]

2. **Do NOT rewrite existing auth code.** Build on top of what exists. The `require_auth` and `get_current_user_id` dependencies are already used by other endpoints (matches, learned_preferences, etc.).
   [Source: backend/app/api/v1/matches.py, backend/app/api/v1/learned_preferences.py]

3. **User sync pattern:** Other endpoints already use an `ensure_user_exists` pattern (see matches.py and learned_preferences.py). The auth sync endpoint should use a similar but dedicated upsert approach: find User by clerk_id, create if not found.
   [Source: backend/app/api/v1/matches.py — ensure_user_exists function]

4. **Token refresh is handled by Clerk SDK.** The `@clerk/clerk-react` package handles JWT refresh automatically. The `getToken()` call in `api.ts` interceptor already fetches fresh tokens. No additional token refresh logic is needed.
   [Source: frontend/src/services/api.ts — request interceptor]

5. **Post-auth navigation:** Use Clerk's `afterSignInUrl` and `afterSignUpUrl` props (already partially set in SignIn.tsx). The `ProtectedRoute` component should check if the user has completed onboarding to route appropriately.

6. **Existing patterns to follow:**
   - Backend routers use `APIRouter(prefix=..., tags=[...])` pattern
   - User model has `clerk_id TEXT UNIQUE` field
   - Frontend uses React Router with `<Route>` components

### Previous Story Intelligence (0-2)

- Story 0-2 added RLS policies and `set_rls_context` helper
- The `ensure_user_exists` dependency in matches.py/learned_preferences.py already queries User by clerk_id
- Backend tests mock auth with `get_current_user_id` dependency override

### Technical Requirements

**User Sync Endpoint:**
```python
# POST /api/v1/auth/sync
# Called by frontend ProtectedRoute after authentication
# Upserts user record using clerk_id from JWT
@router.post("/sync")
async def sync_user(
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    # Find or create user by clerk_id
    result = await db.execute(select(User).where(User.clerk_id == clerk_user_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(clerk_id=clerk_user_id, email="pending@sync.local")
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return {"user": {...}, "is_new": True}
    return {"user": {...}, "is_new": False}
```

**ProtectedRoute Component:**
```tsx
// Wraps routes that require authentication
// Redirects to /sign-in if not logged in
// Calls /api/v1/auth/sync on mount to ensure user record exists
```

### Library/Framework Requirements

**No new dependencies needed.**
- `@clerk/clerk-react` ^5.0.0 — already installed
- `fastapi-clerk-auth` >=0.0.9 — already installed

### File Structure Requirements

**Files to CREATE:**
```
backend/app/api/v1/auth.py
frontend/src/components/auth/ProtectedRoute.tsx
frontend/src/pages/SignUp.tsx
backend/tests/unit/test_api/test_auth_sync.py
frontend/src/components/auth/__tests__/ProtectedRoute.test.tsx
```

**Files to MODIFY:**
```
backend/app/api/v1/router.py                    # Register auth router
frontend/src/App.tsx                             # Add auth routes and ProtectedRoute wrapper
```

**Files to NOT TOUCH:**
```
backend/app/auth/clerk.py                        # Already working
frontend/src/providers/ClerkProvider.tsx          # Already working
frontend/src/services/api.ts                     # Already working
backend/app/db/models.py                         # User model already has clerk_id
```

### Testing Requirements

- **Backend Framework:** Pytest + pytest-asyncio
- **Frontend Framework:** Vitest + React Testing Library
- **Backend Tests:**
  - POST /api/v1/auth/sync creates new user when clerk_id not found
  - POST /api/v1/auth/sync returns existing user when clerk_id exists
  - POST /api/v1/auth/sync returns 401 when no auth token provided
  - Response includes is_new flag
- **Frontend Tests:**
  - ProtectedRoute redirects to /sign-in when not authenticated
  - ProtectedRoute renders children when authenticated
  - SignUp page renders Clerk SignUp component

## Dev Agent Record

### Agent Model Used

### Route Taken

### GSD Subagents Used

### Debug Log References

### Completion Notes List

### Change Log

### File List
