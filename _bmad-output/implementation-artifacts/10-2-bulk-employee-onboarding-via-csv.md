# Story 10.2: Bulk Employee Onboarding via CSV

Status: review

## Story

As an **enterprise administrator**,
I want **to upload a CSV file of employee emails to bulk-invite them to the platform**,
So that **I can efficiently onboard my entire team without sending individual invitations**.

## Acceptance Criteria

1. **AC1: CSV upload and parsing** — Given the admin uploads a CSV file via the bulk-upload endpoint, when the file is received, then the system parses the CSV and extracts employee email rows, supporting headers `email` (required), `first_name` (optional), `last_name` (optional), `department` (optional).
2. **AC2: Email format validation** — Given a CSV has been parsed, when rows are validated, then each email is checked against RFC 5322 format and invalid emails are flagged with error reason "invalid_email_format".
3. **AC3: Duplicate detection within CSV** — Given a CSV has been parsed, when rows are validated, then duplicate emails within the same CSV are flagged with error reason "duplicate_in_upload" (first occurrence is kept, subsequent duplicates flagged).
4. **AC4: Existing account detection** — Given a CSV has been parsed, when rows are validated, then emails belonging to users already in the organization are flagged with error reason "already_in_org", and emails with existing platform accounts outside the org are flagged with "existing_account_different_org".
5. **AC5: Batch size enforcement** — Given an admin uploads a CSV, when the file contains more than 1000 rows, then the request is rejected with HTTP 400 and a message indicating the maximum batch size of 1000.
6. **AC6: Valid rows queued for invitation** — Given validation is complete, when valid rows exist, then a Celery task `bulk_onboard_employees` is enqueued to process invitations asynchronously, and the API returns a summary with `total`, `valid`, `invalid`, `queued` counts.
7. **AC7: Error report returned** — Given validation is complete, when invalid rows exist, then the API response includes an `errors` array with objects containing `row_number`, `email`, `error_reason`, downloadable as JSON.
8. **AC8: Audit logging** — Given a bulk upload is processed, when the upload completes, then an audit log entry is created with action "bulk_upload", resource_type "csv_onboarding", and changes containing the upload summary.

## Tasks / Subtasks

- [ ] Task 1: Create CSVOnboardingService (AC: #1, #2, #3, #4, #5)
  - [ ] 1.1 Create `backend/app/services/enterprise/__init__.py` if not exists
  - [ ] 1.2 Create `backend/app/services/enterprise/csv_onboarding.py` with `CSVOnboardingService` class
  - [ ] 1.3 Implement `parse_csv(file_content: bytes) -> list[dict]` — use Python `csv` module, handle BOM, validate headers, return list of row dicts
  - [ ] 1.4 Implement `validate_rows(rows: list[dict], org_id: UUID, session: AsyncSession) -> ValidationResult` — returns dataclass with `valid_rows`, `invalid_rows` (each with `row_number`, `email`, `error_reason`)
  - [ ] 1.5 Implement email format validation using `re` module with RFC 5322 simplified pattern
  - [ ] 1.6 Implement duplicate detection within the CSV (track seen emails, flag second+ occurrences)
  - [ ] 1.7 Implement existing account check — query `User` table and `OrganizationMember` table to detect existing users
  - [ ] 1.8 Enforce max 1000 row limit in `parse_csv()`, raise `ValueError` if exceeded

- [ ] Task 2: Create bulk upload API endpoint (AC: #1, #5, #6, #7, #8)
  - [ ] 2.1 Add `POST /api/v1/admin/employees/bulk-upload` to `backend/app/api/v1/admin.py`
  - [ ] 2.2 Accept `UploadFile` parameter for CSV file
  - [ ] 2.3 Require `require_admin` dependency from story 10-1
  - [ ] 2.4 Call `CSVOnboardingService.parse_csv()` and `validate_rows()`
  - [ ] 2.5 If valid rows exist, enqueue `bulk_onboard_employees` Celery task with valid row data and org_id
  - [ ] 2.6 Return `BulkUploadResponse` schema with `total`, `valid`, `invalid`, `queued` counts and `errors` array
  - [ ] 2.7 Call `log_audit_event()` with bulk upload summary

- [ ] Task 3: Create Celery task for async processing (AC: #6)
  - [ ] 3.1 Add `bulk_onboard_employees` task to `backend/app/worker/tasks.py` on the `"default"` queue
  - [ ] 3.2 Follow established pattern: `@celery_app.task(bind=True, ...)`, lazy imports, `_run_async()` wrapper
  - [ ] 3.3 Task receives `org_id` and `valid_rows` list, iterates and creates invitation records (delegates to InvitationService from story 10-3, or creates placeholder records)
  - [ ] 3.4 Max retries=2, default_retry_delay=120

- [ ] Task 4: Create response schemas (AC: #6, #7)
  - [ ] 4.1 Create `BulkUploadResponse` Pydantic model with fields: `total` (int), `valid` (int), `invalid` (int), `queued` (int), `errors` (list of `RowError`)
  - [ ] 4.2 Create `RowError` Pydantic model with fields: `row_number` (int), `email` (str), `error_reason` (str)

- [ ] Task 5: Write tests (AC: #1-#8)
  - [ ] 5.1 Create `backend/tests/unit/test_services/test_csv_onboarding.py`
  - [ ] 5.2 Test CSV parsing with valid file (correct headers, rows extracted)
  - [ ] 5.3 Test CSV parsing with missing required `email` header raises error
  - [ ] 5.4 Test CSV parsing with BOM-prefixed file succeeds
  - [ ] 5.5 Test email format validation catches invalid emails
  - [ ] 5.6 Test duplicate detection within CSV flags second occurrence
  - [ ] 5.7 Test existing account detection flags users already in org
  - [ ] 5.8 Test batch size limit rejects CSV with >1000 rows
  - [ ] 5.9 Test API endpoint returns correct summary counts
  - [ ] 5.10 Test API endpoint enqueues Celery task for valid rows
  - [ ] 5.11 Test API endpoint returns error array for invalid rows

## Dev Notes

### Architecture Compliance

- **Service location**: `backend/app/services/enterprise/csv_onboarding.py` — under enterprise-specific services directory
- **CSV parsing**: Use Python standard library `csv` module — no external dependencies needed. Handle UTF-8 BOM with `codecs.BOM_UTF8`
- **API pattern**: Endpoint added to existing `backend/app/api/v1/admin.py` under admin router, requires `require_admin` dependency from story 10-1
- **Celery pattern**: Follow existing task pattern in `backend/app/worker/tasks.py` — lazy imports inside async `_execute()`, `_run_async()` wrapper, `"default"` queue
- **File upload**: FastAPI `UploadFile` — read bytes, decode UTF-8, pass to CSV service
- **Audit logging**: Use `log_audit_event()` from `backend/app/services/enterprise/audit.py` (created in story 10-1)
- **Dependency on 10-1**: This story requires the `require_admin` dependency and `AuditLog` model from story 10-1. If 10-1 is not yet implemented, stub the admin dependency for testing.

### Existing Utilities to Use

- `require_admin` from `app.auth.admin` (story 10-1) — admin authentication
- `log_audit_event()` from `app.services.enterprise.audit` (story 10-1) — audit trail
- `AsyncSessionLocal` from `app.db.engine` — database session
- `_run_async()` pattern from `app.worker.tasks` — Celery async wrapper

### Project Structure Notes

- Service: `backend/app/services/enterprise/csv_onboarding.py`
- Endpoint: added to `backend/app/api/v1/admin.py`
- Celery task: added to `backend/app/worker/tasks.py`
- Test file: `backend/tests/unit/test_services/test_csv_onboarding.py`

### References

- [Source: backend/app/api/v1/admin.py — existing admin routes to extend]
- [Source: backend/app/worker/tasks.py — Celery task pattern with lazy imports and _run_async()]
- [Source: backend/app/auth/clerk.py — get_current_user_id() pattern for dependency injection]
- [Source: backend/app/services/transactional_email.py — service class pattern reference]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
SIMPLE (score: 4/16)

### GSD Subagents Used
None (direct execution)

### Debug Log References
N/A

### Completion Notes List
- CSVOnboardingService with parse_csv() and validate_rows() methods
- Email format validation (RFC 5322 pattern), duplicate detection, existing account checks
- Batch size limit of 1000 rows enforced
- POST /admin/employees/bulk-upload endpoint with require_admin RBAC
- BulkUploadResponse + RowErrorSchema Pydantic models
- bulk_onboard_employees Celery task (placeholder for story 10-3 integration)
- Audit logging on bulk upload with summary changes
- 17 tests covering all 8 acceptance criteria

### Change Log
- 2026-02-02: Story implemented via SIMPLE route, direct execution

### File List

#### Files to CREATE
- `backend/app/services/enterprise/csv_onboarding.py`
- `backend/tests/unit/test_services/test_csv_onboarding.py`

#### Files to MODIFY
- `backend/app/api/v1/admin.py`
- `backend/app/worker/tasks.py`
