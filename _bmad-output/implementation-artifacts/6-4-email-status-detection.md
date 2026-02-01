# Story 6.4: Email Status Detection

Status: review

## Story

As a **Pipeline Agent**,
I want **to accurately detect application status from emails**,
So that **pipeline cards move automatically with >90% accuracy**.

## Acceptance Criteria

1. **AC1 - Detection Accuracy:** Given an email from a recruiter or ATS, when the agent analyzes it, then it detects status with >90% accuracy for: interview scheduling, rejection, offer, application confirmation.
2. **AC2 - LLM Fallback:** Given the regex-based detector returns ambiguous results (confidence < 0.7), when LLM classification is available, then the system uses LLM to classify the email with higher accuracy.
3. **AC3 - Ambiguous Flagging:** Given an email remains ambiguous after both regex and LLM analysis, when confidence is still below threshold, then the email is flagged for user review rather than auto-moved.
4. **AC4 - Confidence Storage:** Given a status detection occurs, when the result is persisted, then the confidence score and detection method (regex/llm) are stored with each detection in `application_status_changes`.
5. **AC5 - Scan Endpoint:** Given a user has a connected email provider, when the scan endpoint is called, then the system fetches recent emails and runs status detection on them.
6. **AC6 - Batch Processing:** Given multiple emails need scanning, when the scan runs, then each email is processed independently with individual confidence scores and detection results.

## Tasks / Subtasks

- [x] Task 1: Enhance EmailStatusDetector with LLM fallback (AC: #1, #2, #3)
  - [x]1.1: Add `detect_with_llm()` method to `EmailStatusDetector` that calls OpenAI for ambiguous emails
  - [x]1.2: Add `detect_enhanced()` method that tries regex first, falls back to LLM if ambiguous
  - [x]1.3: Return detection_method field ('regex' or 'llm') in `StatusDetection`
  - [x]1.4: Write unit tests for LLM fallback path (>=4 tests)

- [x] Task 2: Add email scan service (AC: #5, #6)
  - [x]2.1: Create `backend/app/services/email_scan_service.py` with `scan_user_emails()` function
  - [x]2.2: Fetch emails from Gmail/Outlook via existing services based on user's `email_connections`
  - [x]2.3: Match emails to applications by company/job title in subject
  - [x]2.4: Call PipelineAgent for each matched email
  - [x]2.5: Write unit tests (>=4 tests)

- [x] Task 3: Add scan endpoint to integrations router (AC: #5)
  - [x]3.1: Add POST `/integrations/email/scan` endpoint that triggers email scanning
  - [x]3.2: Return scan results summary (emails processed, statuses detected, flagged for review)
  - [x]3.3: Write unit tests for endpoint (>=3 tests)

- [x] Task 4: Update pipeline agent for detection method tracking (AC: #4)
  - [x]4.1: Update `_update_application_status()` to accept and store `detection_method` parameter
  - [x]4.2: Pass detection_method through from StatusDetection to audit trail
  - [x]4.3: Write unit test for detection method in audit trail

## Dev Notes

### Architecture Compliance
- Extends existing `EmailStatusDetector` in `backend/app/services/email_parser.py` — DO NOT create a new file for detection
- LLM calls must use the existing LLM client abstraction pattern (lazy import OpenAI, use `app.config.settings` for API key)
- Email scan service fetches via existing `gmail_service.fetch_job_emails()` and `outlook_service.fetch_job_emails()`
- Pipeline Agent already handles the core detection-to-DB flow — email scan service dispatches to it
- Use `detection_method` column already in `application_status_changes` table (values: 'email_parse', 'llm_classify')
- Raw SQL via `text()` with lazy imports — same pattern as all other services
- All new endpoints go in existing `backend/app/api/v1/integrations.py`

### File Structure Requirements

**Files to CREATE:**
```
backend/app/services/email_scan_service.py                    # Email scanning orchestration
backend/tests/unit/test_services/test_email_scan_service.py   # Scan service tests
```

**Files to MODIFY:**
```
backend/app/services/email_parser.py                          # Add LLM fallback + detection_method
backend/app/agents/core/pipeline_agent.py                     # Pass detection_method to audit
backend/app/api/v1/integrations.py                            # Add scan endpoint
backend/tests/unit/test_services/test_email_parser.py         # Add LLM fallback tests
backend/tests/unit/test_agents/test_pipeline_agent.py         # Update for detection_method
```

### Previous Story Intelligence
- Story 6-1 created `EmailStatusDetector` with regex patterns — 14 tests passing
- Story 6-1 created `PipelineAgent` with `_update_application_status()` — 10 tests passing
- Story 6-2 created `gmail_service.fetch_job_emails()` — returns list of dicts with id, subject, from_address, snippet
- Story 6-3 created `outlook_service.fetch_job_emails()` — same return format via Microsoft Graph API
- `email_connections` table tracks which provider each user has connected
- `application_status_changes` table already has `detection_method` column
- `_mock_session_cm()` helper used across all test files for DB mocking
- `StatusDetection` dataclass has: detected_status, confidence, evidence_snippet, is_ambiguous

### Testing Requirements
- **LLM Fallback Tests:** Mock OpenAI client. Test regex-confident skips LLM. Test ambiguous triggers LLM. Test LLM failure gracefully falls back. Test detection_method correctly set.
- **Scan Service Tests:** Mock email services and pipeline agent. Test Gmail scan. Test Outlook scan. Test no connections returns empty. Test batch processing.
- **Endpoint Tests:** Test scan endpoint returns summary. Test unauthenticated returns 401. Test no connections returns empty result.
- **Mock Pattern:** Use `_mock_session_cm()` for DB. Patch `AsyncSessionLocal`. Import inside `with patch(...)` block.

## Dev Agent Record
### Agent Model Used
Claude Opus 4.5
### Route Taken
SIMPLE (score: 6/16, overridden by user flag)
### GSD Subagents Used
None (direct execution)
### Debug Log References
- Updated pipeline agent tests to patch `detect_enhanced` (async) instead of `detect` (sync) after switching agent to use enhanced detection
- Patched `openai.AsyncOpenAI` at module level instead of `app.services.email_parser.AsyncOpenAI` for lazy imports
### Completion Notes List
- Added `detection_method` field to `StatusDetection` dataclass (default: 'regex')
- Added `detect_with_llm()` method — calls GPT-3.5-turbo for ambiguous email classification
- Added `detect_enhanced()` method — regex-first with LLM fallback for ambiguous results
- Created `email_scan_service.py` — orchestrates email fetching from Gmail/Outlook + status detection
- Added POST `/integrations/email/scan` endpoint for triggering scans
- Updated PipelineAgent to use `detect_enhanced()` and pass `detection_method` to audit trail
- 20 new tests added (6 email parser, 5 scan service, 3 endpoint, 1 detection method, 5 LLM fallback)
### Change Log
- 2026-02-01: Story 6-4 implemented — LLM fallback, scan service, detection method tracking
### File List
**Created:**
- `backend/app/services/email_scan_service.py`
- `backend/tests/unit/test_services/test_email_scan_service.py`

**Modified:**
- `backend/app/services/email_parser.py`
- `backend/app/agents/core/pipeline_agent.py`
- `backend/app/api/v1/integrations.py`
- `backend/tests/unit/test_services/test_email_parser.py`
- `backend/tests/unit/test_agents/test_pipeline_agent.py`
- `backend/tests/unit/test_api/test_integrations.py`
