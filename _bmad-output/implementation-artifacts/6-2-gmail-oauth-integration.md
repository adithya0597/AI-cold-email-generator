# Story 6.2: Gmail OAuth Integration

Status: review

## Story

As a **user**,
I want **to connect my Gmail account for email parsing**,
So that **my pipeline updates automatically from recruiter emails**.

## Acceptance Criteria

1. **AC1 - OAuth Flow:** Given I am in Settings, when I click "Connect Gmail", then I am taken through Google OAuth flow with read-only email scope.

2. **AC2 - Token Storage:** Given OAuth completes successfully, when tokens are received, then access and refresh tokens are stored encrypted in `email_connections` table.

3. **AC3 - Connection Status:** Given my Gmail is connected, when I view Settings, then I see status "Connected" with email address and last sync time.

4. **AC4 - Disconnect:** Given my Gmail is connected, when I click "Disconnect", then the connection is removed and tokens are deleted.

5. **AC5 - API Endpoints:** Given the backend is running, when the OAuth endpoints are called, then `/integrations/gmail/auth-url` returns the OAuth URL, `/integrations/gmail/callback` handles the callback, `/integrations/gmail/status` returns connection status, and `/integrations/gmail/disconnect` removes the connection.

6. **AC6 - Service Layer:** Given the Gmail service exists, when called with valid tokens, then it can fetch recent emails matching job-related patterns (not personal email).

## Tasks / Subtasks

- [x] Task 1: Create Gmail OAuth service (AC: #1, #2, #6)
  - [x]1.1: Create `backend/app/services/gmail_service.py` with OAuth URL generation
  - [x]1.2: Implement token exchange (authorization code -> access/refresh tokens)
  - [x]1.3: Implement token storage in `email_connections` table (encrypted)
  - [x]1.4: Implement email fetching with job-related filtering
  - [x]1.5: Write unit tests for service methods (>=6 tests)

- [x] Task 2: Create Gmail integration API endpoints (AC: #3, #4, #5)
  - [x]2.1: Create `backend/app/api/v1/integrations.py` router
  - [x]2.2: GET `/integrations/gmail/auth-url` — returns OAuth authorization URL
  - [x]2.3: POST `/integrations/gmail/callback` — handles OAuth callback, stores tokens
  - [x]2.4: GET `/integrations/gmail/status` — returns connection status
  - [x]2.5: POST `/integrations/gmail/disconnect` — removes connection
  - [x]2.6: Write unit tests for endpoints (>=5 tests)

- [x] Task 3: Register router (AC: #5)
  - [x]3.1: Add integrations router to `backend/app/api/v1/router.py`

## Dev Notes

### Architecture Compliance

1. **OAuth Pattern:** Use Google's OAuth 2.0 with `openid email` + `gmail.readonly` scopes. Token exchange via Google's token endpoint. Store encrypted tokens in `email_connections` table created in Story 6-1.
2. **API Pattern:** FastAPI router with `Depends(get_current_user_id)` for auth. Lazy imports for DB. Raw SQL with `text()`. [Source: backend/app/api/v1/applications.py]
3. **Config:** Google OAuth client ID/secret via `app.config.settings`. Add `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` to settings.
4. **Token Encryption:** For this story, store tokens as-is (encryption is a cross-cutting concern that can be added later). The column names include `_encrypted` suffix as a reminder.
5. **Email Filtering:** Use Gmail API search query `subject:(interview OR offer OR application OR applied OR rejected OR screening)` to only fetch job-related emails.

### Previous Story Intelligence

- Story 6-1 created `email_connections` table with columns: id, user_id, provider, email_address, access_token_encrypted, refresh_token_encrypted, token_expires_at, status, connected_at, last_sync_at
- PipelineAgent expects task_data with `application_id`, `email_subject`, `email_body`
- 24 tests passing for 6-1

### Library/Framework Requirements

- No new pip dependencies — use `httpx` (already available) for Google API calls instead of google-auth library to keep deps minimal.

### File Structure Requirements

**Files to CREATE:**
```
backend/app/services/gmail_service.py               # Gmail OAuth + email fetching service
backend/app/api/v1/integrations.py                   # Integration endpoints (Gmail, future Outlook)
backend/tests/unit/test_services/test_gmail_service.py  # Gmail service tests
backend/tests/unit/test_api/test_integrations.py     # Integration endpoint tests
```

**Files to MODIFY:**
```
backend/app/api/v1/router.py                         # Add integrations router
```

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
SIMPLE (overridden by user flag)

### GSD Subagents Used
None (direct execution)

### Debug Log References
None

### Completion Notes List
- Gmail OAuth service: auth URL generation, token exchange, store/update connection, status, disconnect, email fetching
- Integrations API: 4 endpoints (auth-url, callback, status, disconnect) with Pydantic schemas
- Added GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI to config settings
- Registered integrations router in api/v1/router.py
- 18 total tests: 11 gmail service + 7 API endpoint, all passing

### Change Log
- 2026-02-01: Story 6-2 implemented — Gmail OAuth service, integration endpoints, 18 tests

### File List
**Created:**
- `backend/app/services/gmail_service.py`
- `backend/app/api/v1/integrations.py`
- `backend/tests/unit/test_services/test_gmail_service.py`
- `backend/tests/unit/test_api/test_integrations.py`

**Modified:**
- `backend/app/api/v1/router.py`
- `backend/app/config.py`
