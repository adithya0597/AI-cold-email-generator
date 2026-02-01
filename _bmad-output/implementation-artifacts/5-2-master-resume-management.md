# Story 5.2: Master Resume Management

Status: review

## Story

As a **user**,
I want **to upload and manage my master resume**,
so that **the agent has a complete source to tailor from**.

## Acceptance Criteria

1. **AC1 - Upload Master Resume:** Given I am authenticated, when I call `POST /api/v1/documents/master-resume` with a PDF/DOCX file, then the file is stored in Supabase Storage, a Document record is created with type=RESUME and job_id=NULL (master), and my Profile.resume_storage_path is updated.

2. **AC2 - Archive Previous Master:** Given I already have a master resume, when I upload a new one, then the previous master is soft-deleted (not permanently removed) and the new one becomes active.

3. **AC3 - Single Active Master:** Given I have uploaded resumes, when I query my master resume, then only one active master resume exists (job_id IS NULL AND deleted_at IS NULL).

4. **AC4 - Structured Data Parsing:** Given I upload a master resume, when the upload completes, then the resume is parsed via the existing resume_parser service and structured data (skills, experience, education) is stored/updated in my Profile.

5. **AC5 - Download Master Resume:** Given I have a master resume, when I call `GET /api/v1/documents/master-resume`, then I receive the document metadata with a signed download URL.

6. **AC6 - List Documents:** Given I have resumes (master + tailored), when I call `GET /api/v1/documents`, then I receive a paginated list of all my documents with metadata.

7. **AC7 - Delete Document:** Given I own a document, when I call `DELETE /api/v1/documents/{id}`, then the document is soft-deleted.

8. **AC8 - Tests:** Given documents endpoints exist, when unit tests run, then comprehensive coverage exists for upload, archive, download, list, and delete operations.

## Tasks / Subtasks

- [x] Task 1: Create documents API endpoint (AC: #1, #2, #3, #4, #5, #6, #7)
  - [x]1.1: Create `backend/app/api/v1/documents.py` with router prefix `/documents`
  - [x]1.2: Implement `POST /master-resume` — upload file, store in Supabase Storage, create Document row (type=resume, job_id=NULL), parse resume, update Profile, soft-delete previous master
  - [x]1.3: Implement `GET /master-resume` — return active master resume metadata + signed download URL
  - [x]1.4: Implement `GET /` — list all user documents (paginated, with optional type filter)
  - [x]1.5: Implement `DELETE /{document_id}` — soft-delete a document

- [x] Task 2: Register documents router (AC: #1)
  - [x]2.1: Update `backend/app/api/v1/router.py` to include documents router

- [x] Task 3: Write comprehensive tests (AC: #8)
  - [x]3.1: Create `backend/tests/unit/test_api/test_documents.py`
  - [x]3.2: Test master resume upload — Document created, Profile updated, file stored
  - [x]3.3: Test archive previous master — old master soft-deleted on new upload
  - [x]3.4: Test single active master — only one master with job_id=NULL and deleted_at=NULL
  - [x]3.5: Test download master resume — returns signed URL
  - [x]3.6: Test list documents — returns paginated list
  - [x]3.7: Test delete document — soft-deletes
  - [x]3.8: Test upload validation — rejects non-PDF/DOCX files

## Dev Notes

### Architecture Compliance

**CRITICAL — Follow these patterns EXACTLY:**

1. **Profile.resume_storage_path ALREADY EXISTS** in the model but is never populated. The upload endpoint must set this field.
   [Source: backend/app/db/models.py line 233]

2. **Document model** already has all needed fields: id, user_id, type (resume/cover_letter), version, content, job_id, schema_version. A master resume has `job_id = NULL`. Tailored resumes have `job_id` set.
   [Source: backend/app/db/models.py lines 369-390]

3. **Storage service** already provides `upload_file()`, `get_signed_url()`, `delete_file()`. Use these directly — do NOT create new storage functions.
   [Source: backend/app/services/storage_service.py]

4. **Resume parser** already exists with `extract_profile_from_resume(file_bytes, filename)`. Use this for parsing uploaded master resumes.
   [Source: backend/app/services/resume_parser.py]

5. **API pattern:** Use `Depends(get_current_user_id)` for auth. Use `AsyncSessionLocal` with lazy imports. Follow the pattern in `users.py` or `onboarding.py`.
   [Source: backend/app/api/v1/users.py]

6. **Soft-delete pattern:** Set `deleted_at = now()` instead of hard DELETE. The `SoftDeleteMixin` on Document provides `deleted_at`, `deleted_by`, `deletion_reason` fields.
   [Source: backend/app/db/models.py — SoftDeleteMixin]

7. **Copy-on-write:** Master resume is NEVER modified in place. New upload creates a new Document row and soft-deletes the old one. Tailored versions are separate Documents with job_id set.
   [Source: .planning/ROADMAP.md Phase 5 research adjustments]

8. **Onboarding already uploads resumes** but doesn't persist the storage path. This story adds the persistent master resume management layer.
   [Source: backend/app/api/v1/onboarding.py lines 91-198]

### Previous Story Intelligence (5-1)

- 13 tests passing for ResumeAgent (test_resume_agent.py)
- Mock pattern: patch at source module (`app.db.engine.AsyncSessionLocal`), NOT consumer module
- TestClient cannot be used due to pre-existing ColdEmailRequest issue — test functions directly
- Document model uses `content` field (Text) for document content and `version` (Integer) for versioning

### Library/Framework Requirements

**No new dependencies needed.** All packages already installed.

### File Structure Requirements

**Files to CREATE:**
```
backend/app/api/v1/documents.py
backend/tests/unit/test_api/test_documents.py
```

**Files to MODIFY:**
```
backend/app/api/v1/router.py  # Add documents router
```

**Files to NOT TOUCH:**
```
backend/app/services/storage_service.py   # Already has all needed functions
backend/app/services/resume_parser.py     # Already has extraction
backend/app/db/models.py                  # Document model already complete
backend/app/api/v1/onboarding.py          # Onboarding flow stays separate
```

### Testing Requirements

- **Backend Framework:** Pytest + pytest-asyncio
- **Mocking:** Mock `AsyncSessionLocal`, mock `upload_file`, mock `get_signed_url`, mock `extract_profile_from_resume`
- **Mock paths:** Patch at source module
- **Tests to write:**
  - Upload master resume: creates Document, updates Profile.resume_storage_path
  - Archive: previous master soft-deleted on new upload
  - Single active: only one master with job_id=NULL and deleted_at=NULL
  - Download: returns signed URL
  - List: returns paginated documents
  - Delete: soft-deletes document
  - Validation: rejects invalid file types

### References

- [Source: backend/app/db/models.py] — Document model, Profile model
- [Source: backend/app/services/storage_service.py] — upload_file, get_signed_url, delete_file
- [Source: backend/app/services/resume_parser.py] — extract_profile_from_resume
- [Source: backend/app/api/v1/router.py] — router registration pattern
- [Source: backend/app/api/v1/users.py] — API endpoint pattern with Depends(get_current_user_id)
- [Source: .planning/ROADMAP.md] — Phase 5 copy-on-write requirement

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
SIMPLE (score: 2/16, overridden to SIMPLE by user flag)

### Debug Log References
- 2 test assertion fixes (deletion_reason is in SQL text, not params dict)

### Completion Notes List
- Created documents API with 4 endpoints: POST /master-resume, GET /master-resume, GET /, DELETE /{id}
- Upload flow: validate file → store in Supabase Storage → soft-delete previous master → parse via resume_parser → create Document row → update Profile.resume_storage_path + structured data
- Copy-on-write: new upload creates new Document, soft-deletes old one with 'archived_by_new_upload' reason
- Download returns signed URL via storage_service.get_signed_url()
- List supports pagination and optional type filter
- Delete uses soft-delete with 'user_deleted' reason
- Registered documents router in api/v1/router.py
- 14 comprehensive tests covering all 8 ACs

### Change Log
- 2026-02-01: Created documents API + router registration + 14 tests

### File List
**Created:**
- `backend/app/api/v1/documents.py`
- `backend/tests/unit/test_api/test_documents.py`

**Modified:**
- `backend/app/api/v1/router.py` — Added documents router import and registration
