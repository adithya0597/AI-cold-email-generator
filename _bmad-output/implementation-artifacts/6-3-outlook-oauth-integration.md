# Story 6.3: Outlook OAuth Integration

Status: review

## Story

As a **user**,
I want **to connect my Outlook account for email parsing**,
So that **users with Microsoft email can use pipeline tracking**.

## Acceptance Criteria

1. **AC1 - OAuth Flow:** Given I click "Connect Outlook", then I am taken through Microsoft OAuth flow with mail.read scope.
2. **AC2 - Token Storage:** Given OAuth completes, then tokens are stored in `email_connections` table with provider='outlook'.
3. **AC3 - Connection Status:** Given Outlook is connected, then status endpoint returns "Connected" with email.
4. **AC4 - Disconnect:** Given Outlook is connected, then disconnect removes the connection.
5. **AC5 - API Endpoints:** Outlook endpoints follow same pattern as Gmail: auth-url, callback, status, disconnect.
6. **AC6 - Office 365 Support:** Supports both personal Outlook and Office 365 accounts.

## Tasks / Subtasks

- [x]Task 1: Create Outlook OAuth service (AC: #1, #2, #6)
  - [x]1.1: Create `backend/app/services/outlook_service.py` with Microsoft OAuth flow
  - [x]1.2: Implement token exchange via Microsoft identity platform
  - [x]1.3: Implement email fetching via Microsoft Graph API
  - [x]1.4: Write unit tests (>=6 tests)

- [x]Task 2: Add Outlook endpoints to integrations router (AC: #3, #4, #5)
  - [x]2.1: Add Outlook OAuth endpoints to existing `integrations.py` router
  - [x]2.2: Write unit tests for endpoints (>=5 tests)

## Dev Notes

### Architecture Compliance
- Same patterns as Gmail (Story 6-2): uses `email_connections` table with provider='outlook'
- Microsoft identity platform v2.0 endpoint: `https://login.microsoftonline.com/common/oauth2/v2.0`
- Scopes: `openid email Mail.Read offline_access`
- Add MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, MICROSOFT_REDIRECT_URI to config
- Use httpx for API calls (no new dependencies)

### File Structure Requirements

**Files to CREATE:**
```
backend/app/services/outlook_service.py                    # Outlook OAuth + email service
backend/tests/unit/test_services/test_outlook_service.py   # Outlook service tests
```

**Files to MODIFY:**
```
backend/app/api/v1/integrations.py                         # Add Outlook endpoints
backend/app/config.py                                       # Add Microsoft OAuth config
```

## Dev Agent Record
### Agent Model Used
### Route Taken
### GSD Subagents Used
### Debug Log References
### Completion Notes List
### Change Log
### File List
