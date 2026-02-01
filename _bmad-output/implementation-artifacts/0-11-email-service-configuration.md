# Story 0.11: Email Service Configuration

Status: review

## Story

As a **user**,
I want **to receive transactional emails from JobPilot**,
so that **I get briefings and notifications in my inbox**.

## Acceptance Criteria

1. **AC1 - Email Delivery:** Given Resend is configured, when a briefing email is triggered, then the email is delivered within 5 minutes.

2. **AC2 - Branded Templates:** Given an email is sent, when it renders, then emails use branded HTML templates.

3. **AC3 - Webhook Handling:** Given a bounce or complaint occurs, when Resend sends a webhook, then the event is processed and user preferences updated.

4. **AC4 - CAN-SPAM Compliance:** Given any transactional email, when sent, then an unsubscribe link is included per CAN-SPAM.

5. **AC5 - Email Event Logging:** Given emails are sent, when delivery/open/click events occur, then events are logged for analytics.

## Tasks / Subtasks

- [x] Task 1: Add Resend webhook endpoint for email events (AC: #3, #5)
  - [x] 1.1: Create `backend/app/api/v1/webhooks.py` with `POST /webhooks/resend` endpoint
  - [x] 1.2: Add webhook signature verification using Resend's svix signature headers
  - [x] 1.3: Handle event types: `email.delivered`, `email.bounced`, `email.complained`, `email.opened`, `email.clicked`
  - [x] 1.4: Log events to database via `EmailEvent` model (or structured logging for MVP)
  - [x] 1.5: On bounce/complaint: log warning and publish alert (no auto-unsubscribe for MVP — requires user preferences table)

- [x] Task 2: Add webhook route to API router (AC: #3)
  - [x] 2.1: Register `webhooks.router` in `router.py`
  - [x] 2.2: Add `RESEND_WEBHOOK_SECRET` to config.py settings

- [x] Task 3: Write comprehensive email service tests (AC: #1-#5)
  - [x] 3.1: Create `backend/tests/unit/test_services/test_transactional_email.py`
  - [x] 3.2: Test `send_email()` calls Resend SDK with correct params
  - [x] 3.3: Test `send_email()` returns suppressed response when API key not set
  - [x] 3.4: Test `send_briefing()` uses briefing template with unsubscribe link
  - [x] 3.5: Test `send_welcome()` uses welcome template
  - [x] 3.6: Test `send_account_deletion_notice()` uses deletion template
  - [x] 3.7: Test all templates include unsubscribe link or comply with CAN-SPAM
  - [x] 3.8: Test webhook endpoint processes delivery events
  - [x] 3.9: Test webhook endpoint handles bounce events
  - [x] 3.10: Test webhook signature verification rejects invalid signatures
  - [x] 3.11: Test graceful degradation when Resend unavailable

## Dev Notes

### Architecture Compliance

**CRITICAL — Email service is ALREADY SUBSTANTIALLY IMPLEMENTED:**

1. **transactional_email.py EXISTS:** `backend/app/services/transactional_email.py` with:
   - `send_email()` — core Resend SDK integration
   - `send_briefing()` — daily briefing with branded template + unsubscribe link
   - `send_welcome()` — onboarding email
   - `send_account_deletion_notice()` — GDPR deletion notice
   - Graceful fallback when RESEND_API_KEY not configured
   [Source: backend/app/services/transactional_email.py]

2. **Config setting EXISTS:** `RESEND_API_KEY: str = ""` in config.py
   [Source: backend/app/config.py:55]

3. **Package installed:** `resend>=2.0.0` in requirements.txt
   [Source: backend/requirements.txt:43]

4. **HTML templates EXIST** with branded styling, unsubscribe links (CAN-SPAM compliant)
   [Source: backend/app/services/transactional_email.py:35-76]

5. **ADR-6:** Resend chosen over SendGrid for better DX and free tier
   [Source: _bmad-output/planning-artifacts/epics.md, planning docs]

**WHAT'S MISSING:**
- No Resend webhook endpoint for bounce/complaint/delivery/open/click events
- No webhook signature verification
- No email event logging
- No RESEND_WEBHOOK_SECRET config setting
- No tests for transactional_email.py

### Previous Story Intelligence (0-10)

- 14 WebSocket tests passing, mock patterns well established
- API endpoint pattern: APIRouter with prefix, Pydantic response models
- Webhook pattern: POST endpoint accepting JSON body, signature verification in headers

### Technical Requirements

**Resend Webhook Endpoint:**
Resend sends webhook events via POST with svix signature headers:
- `svix-id`: Unique message ID
- `svix-timestamp`: Unix timestamp
- `svix-signature`: HMAC-SHA256 signature

Webhook payload format:
```json
{
  "type": "email.delivered",
  "data": {
    "email_id": "...",
    "to": ["user@example.com"],
    "created_at": "2026-01-30T12:00:00Z"
  }
}
```

Event types to handle:
- `email.delivered` — log delivery confirmation
- `email.bounced` — log + alert
- `email.complained` — log + alert (spam complaint)
- `email.opened` — log for analytics
- `email.clicked` — log for analytics

**Signature Verification:**
```python
import hashlib, hmac, base64, time

def verify_resend_webhook(payload: bytes, headers: dict, secret: str) -> bool:
    msg_id = headers.get("svix-id")
    timestamp = headers.get("svix-timestamp")
    signature = headers.get("svix-signature")

    # Check timestamp freshness (within 5 minutes)
    if abs(time.time() - int(timestamp)) > 300:
        return False

    to_sign = f"{msg_id}.{timestamp}.{payload.decode()}"
    expected = base64.b64encode(
        hmac.new(base64.b64decode(secret.split("_")[1]),
                 to_sign.encode(), hashlib.sha256).digest()
    ).decode()

    # svix-signature may contain multiple signatures (v1,...)
    for sig in signature.split():
        if sig.startswith("v1,") and hmac.compare_digest(sig[3:], expected):
            return True
    return False
```

### Library/Framework Requirements

**No new dependencies needed.** Resend SDK already installed.

### File Structure Requirements

**Files to CREATE:**
```
backend/app/api/v1/webhooks.py
backend/tests/unit/test_services/test_transactional_email.py
```

**Files to MODIFY:**
```
backend/app/api/v1/router.py              # Register webhooks router
backend/app/config.py                      # Add RESEND_WEBHOOK_SECRET
```

**Files to NOT TOUCH:**
```
backend/app/services/transactional_email.py  # Already complete — do not modify
backend/app/services/email_service.py        # Legacy cold email — separate concern
backend/app/main.py                          # Legacy email routes — separate concern
```

### Testing Requirements

- **Backend Framework:** Pytest + pytest-asyncio
- **Mocking:** Mock `resend.Emails.send`, mock webhook request headers
- **Tests to write:**
  - send_email: calls resend.Emails.send with correct params
  - send_email: returns suppressed when API key not set
  - send_briefing: formats template with user_name, content, unsubscribe
  - send_welcome: formats template with user_name, dashboard_url
  - send_account_deletion_notice: formats template with user_name
  - Templates: all include unsubscribe link or CAN-SPAM text
  - Webhook: processes email.delivered event
  - Webhook: processes email.bounced event with alert
  - Webhook: rejects invalid signature
  - Webhook: handles unknown event types gracefully

### References

- [Source: backend/app/services/transactional_email.py] — Full email service
- [Source: backend/app/config.py:55] — RESEND_API_KEY setting
- [Source: backend/requirements.txt:43] — resend package
- [Resend Webhooks Docs: https://resend.com/docs/webhooks]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
SIMPLE (score: 4/16) — direct execution, no GSD subagents

### Debug Log References
None — clean implementation

### Completion Notes List
- Created Resend webhook endpoint with svix HMAC-SHA256 signature verification
- Handles 5 event types: delivered, bounced, complained, opened, clicked
- Bounce/complaint events logged at WARNING level for alerting
- Webhook route registered in API router
- RESEND_WEBHOOK_SECRET config setting added
- 16 comprehensive tests covering email sending, templates, CAN-SPAM compliance, webhook processing, signature verification

### Change Log
- 2026-02-01: Implemented webhook endpoint + 16 tests

### File List
**Created:**
- `backend/app/api/v1/webhooks.py`
- `backend/tests/unit/test_services/test_transactional_email.py`

**Modified:**
- `backend/app/api/v1/router.py` — register webhooks router
- `backend/app/config.py` — add RESEND_WEBHOOK_SECRET
