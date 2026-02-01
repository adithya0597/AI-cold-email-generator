# Story 5.3: Resume Diff View

Status: review

## Story

As a **user**,
I want **to see a structured comparison of my original vs tailored resume**,
so that **I understand what was changed and why before approving the application**.

## Acceptance Criteria

1. **AC1 - Diff Endpoint:** Given I have a tailored resume for a job, when I call `GET /api/v1/documents/{document_id}/diff`, then I receive structured diff data comparing the tailored version against my master resume.

2. **AC2 - Section-Level Comparison:** Given the diff is returned, when I inspect the response, then each section shows `original_content`, `tailored_content`, and `changes_made` descriptions.

3. **AC3 - Change Classification:** Given the diff is returned, when I inspect each section, then changes are classified as "added", "removed", or "modified" based on content comparison.

4. **AC4 - ATS Metrics Included:** Given the diff is returned, when I inspect the response, then it includes `ats_score`, `keywords_incorporated`, `keywords_missing`, and `tailoring_rationale` from the tailored resume.

5. **AC5 - Job Context:** Given the diff is returned, when I inspect the response, then it includes the job title, company, and job_id for context.

6. **AC6 - Authorization:** Given I request a diff for a document I don't own, when the endpoint processes the request, then it returns 404 (not revealing document existence).

7. **AC7 - Validation:** Given I request a diff for a master resume (job_id=NULL) or non-resume document, when the endpoint processes, then it returns 400 with a clear error message.

8. **AC8 - Tests:** Given the diff endpoint exists, when unit tests run, then comprehensive coverage exists for diff generation, authorization, validation, and edge cases.

## Tasks / Subtasks

- [x] Task 1: Create diff endpoint in documents API (AC: #1, #2, #3, #4, #5, #6, #7)
  - [x]1.1: Add `GET /{document_id}/diff` route to `backend/app/api/v1/documents.py`
  - [x]1.2: Load the tailored document, verify ownership and type=resume with job_id set
  - [x]1.3: Load the active master resume for the user (job_id IS NULL, deleted_at IS NULL)
  - [x]1.4: Parse both Document.content JSON, build structured diff response with section comparison
  - [x]1.5: Classify each section change as "added", "removed", or "modified"
  - [x]1.6: Include ATS metrics (score, keywords, rationale) and job context in response
  - [x]1.7: Load job title/company from jobs table for context

- [x] Task 2: Write comprehensive tests (AC: #8)
  - [x]2.1: Create tests in `backend/tests/unit/test_api/test_documents.py` (append to existing)
  - [x]2.2: Test happy path — tailored doc returns structured diff with sections, ATS, job context
  - [x]2.3: Test change classification — sections correctly classified as added/removed/modified
  - [x]2.4: Test authorization — wrong user gets 404
  - [x]2.5: Test validation — master resume (job_id=NULL) returns 400
  - [x]2.6: Test validation — non-existent document returns 404
  - [x]2.7: Test no master resume — returns appropriate error
  - [x]2.8: Test ATS metrics included in response

## Dev Notes

### Architecture Compliance

**CRITICAL — Follow these patterns EXACTLY:**

1. **TailoredResume content already contains diff data.** The ResumeAgent stores `TailoredResume` as JSON in `Document.content`. Each `TailoredSection` has `original_content`, `tailored_content`, and `changes_made`. The diff endpoint parses this JSON — NO custom diff algorithm is needed.
   [Source: backend/app/agents/pro/resume_agent.py lines 30-46]

2. **Document.content is Text (JSON string).** Parse with `json.loads()`. Master resume content is ExtractedProfile JSON. Tailored resume content is TailoredResume JSON with sections array.
   [Source: backend/app/db/models.py line 380]

3. **Master vs Tailored identification:** Master resume has `job_id = NULL`. Tailored resume has `job_id` set. Both have `type = 'resume'`.
   [Source: backend/app/db/models.py lines 369-390]

4. **API pattern:** Use `Depends(get_current_user_id)` for auth. Use `AsyncSessionLocal` with lazy imports. Follow the existing pattern in `documents.py`.
   [Source: backend/app/api/v1/documents.py]

5. **Add endpoint to EXISTING documents.py** — do NOT create a new file. The diff is a sub-resource of a document.

6. **Change classification logic:** Compare `original_content` and `tailored_content` in each TailoredSection:
   - If `original_content` is empty/missing and `tailored_content` exists → "added"
   - If `original_content` exists and `tailored_content` is empty/missing → "removed"
   - If both exist and differ → "modified"
   - If both exist and are identical → "unchanged"

7. **Job context from jobs table:** Query the job title and company using the document's `job_id` to include in the diff response.

### Previous Story Intelligence (5-2)

- 14 tests passing for documents API (test_documents.py)
- Mock pattern: `_mock_session_cm()` helper for async context manager
- `_make_upload_file()` helper for file mocks
- Tests call endpoint functions directly (not TestClient)
- Patch paths: `app.db.engine.AsyncSessionLocal`, `app.services.storage_service.*`, `app.services.resume_parser.*`
- Document content stored as JSON string via `json.dumps()`

### Library/Framework Requirements

**No new dependencies needed.** All packages already installed. `json` module from stdlib is sufficient for parsing.

### File Structure Requirements

**Files to CREATE:**
```
(none — all changes go in existing files)
```

**Files to MODIFY:**
```
backend/app/api/v1/documents.py    # Add GET /{document_id}/diff endpoint
backend/tests/unit/test_api/test_documents.py  # Add diff endpoint tests
```

**Files to NOT TOUCH:**
```
backend/app/agents/pro/resume_agent.py  # TailoredResume model is read-only reference
backend/app/db/models.py                # Document model already complete
backend/app/api/v1/router.py            # Documents router already registered
```

### Testing Requirements

- **Backend Framework:** Pytest + pytest-asyncio
- **Mocking:** Mock `AsyncSessionLocal` only (no external services needed for diff)
- **Mock paths:** Patch at source module
- **Tests to write:**
  - Happy path: tailored doc parsed, diff returned with sections + ATS + job context
  - Change classification: verify added/removed/modified/unchanged
  - Authorization: wrong user → 404
  - Validation: master resume → 400, non-existent doc → 404
  - No master resume: appropriate error
  - ATS metrics: score, keywords, rationale present

### References

- [Source: backend/app/agents/pro/resume_agent.py] — TailoredResume, TailoredSection models
- [Source: backend/app/api/v1/documents.py] — Existing documents API pattern
- [Source: backend/app/db/models.py] — Document model, DocumentType enum
- [Source: .planning/ROADMAP.md] — Phase 5 "side-by-side diff view highlighting what was changed"

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
SIMPLE (score: 2/16, overridden to SIMPLE by user flag)

### Debug Log References
- No issues encountered. All 7 new tests passed on first run.

### Completion Notes List
- Added GET /{document_id}/diff endpoint to documents.py
- Loads tailored document, validates ownership + type=resume + job_id set
- Loads active master resume for comparison
- Parses TailoredResume JSON content, builds section-level diff
- Classifies changes as added/removed/modified/unchanged
- Includes ATS metrics (score, keywords, rationale) and job context (title, company)
- 7 comprehensive tests covering all 8 ACs

### Change Log
- 2026-02-01: Added diff endpoint + 7 tests

### File List
**Created:**
(none)

**Modified:**
- `backend/app/api/v1/documents.py` — Added GET /{document_id}/diff endpoint
- `backend/tests/unit/test_api/test_documents.py` — Added 7 diff endpoint tests
