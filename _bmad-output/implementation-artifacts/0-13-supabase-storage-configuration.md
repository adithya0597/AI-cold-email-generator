# Story 0.13: Supabase Storage Configuration

Status: review

## Story

As a **user**,
I want **to upload and store my resume and documents securely**,
so that **the system can tailor my materials for job applications**.

## Acceptance Criteria

1. **AC1 - Private Bucket Storage:** Given Supabase Storage is configured, when I upload a resume file (PDF, DOCX), then the file is stored in a private bucket associated with my user_id.

2. **AC2 - File Size Limit:** Given a file upload, when the file exceeds 10MB, then the upload is rejected with a descriptive error.

3. **AC3 - Authenticated Access Only:** Given a stored file, when access is requested, then only authenticated users can access their own files via RLS policies.

4. **AC4 - Signed URL Generation:** Given a stored file, when a signed URL is requested, then a time-limited URL is generated with 15-minute default expiry.

5. **AC5 - Upload Virus Scanning:** Given a file upload, when the file is processed, then virus scanning is documented as a recommended Supabase dashboard configuration (Supabase doesn't expose a scanning API — this is a dashboard-level setting).

6. **AC6 - Storage Service Tests:** Given the storage service, when unit tests run, then >80% coverage is achieved for storage_service.py and supabase_client.py.

## Tasks / Subtasks

- [x] Task 1: Add Supabase Storage bucket RLS migration (AC: #3)
  - [x] 1.1: Create `supabase/migrations/00004_storage_rls_policies.sql` with per-user isolation policies
  - [x] 1.2: Create rollback migration `supabase/migrations/00004_storage_rls_policies_rollback.sql`
  - [x] 1.3: Policies should enforce: users can only CRUD files in their own `{user_id}/` prefix

- [x] Task 2: Write comprehensive storage service tests (AC: #1, #2, #4, #6)
  - [x] 2.1: Create `backend/tests/unit/test_services/test_storage_service.py`
  - [x] 2.2: Test `upload_file()` calls Supabase SDK with correct params and returns path
  - [x] 2.3: Test `upload_file()` graceful degradation when Supabase not configured
  - [x] 2.4: Test `upload_file()` file size validation rejects >10MB files
  - [x] 2.5: Test `upload_file()` extension validation rejects unsupported types
  - [x] 2.6: Test `upload_file()` content type validation
  - [x] 2.7: Test `upload_file()` handles 409 duplicate by upserting
  - [x] 2.8: Test `get_signed_url()` returns signed URL with correct expiry
  - [x] 2.9: Test `get_signed_url()` graceful degradation when Supabase not configured
  - [x] 2.10: Test `delete_file()` removes file and returns True
  - [x] 2.11: Test `delete_file()` graceful degradation when Supabase not configured
  - [x] 2.12: Test `delete_file()` returns False on error

- [x] Task 3: Document virus scanning configuration (AC: #5)
  - [x] 3.1: Add inline comment in storage_service.py documenting that virus scanning is a Supabase dashboard configuration (not API-driven)

## Dev Notes

### Architecture Compliance

**CRITICAL — Storage service is ALREADY SUBSTANTIALLY IMPLEMENTED:**

1. **Supabase client EXISTS:** `backend/app/db/supabase_client.py` with:
   - Singleton pattern via `get_client()`
   - Restricted to file storage, auth forwarding, realtime (ADR-2)
   [Source: backend/app/db/supabase_client.py]

2. **Storage service EXISTS:** `backend/app/services/storage_service.py` with:
   - `upload_file()` — uploads to `{bucket}/{user_id}/{filename}`, handles 409 upsert
   - `get_signed_url()` — generates time-limited signed URLs (15-min default)
   - `delete_file()` — removes files from bucket
   - Validation: 10MB max, PDF/DOCX only, graceful degradation when Supabase not configured
   [Source: backend/app/services/storage_service.py]

3. **Config settings EXIST:** `SUPABASE_URL: str = ""` and `SUPABASE_KEY: str = ""` in config.py
   [Source: backend/app/config.py]

4. **Upload endpoint EXISTS:** `POST /api/v1/onboarding/resume/upload` in onboarding.py
   [Source: backend/app/api/v1/onboarding.py]

5. **Dependencies EXIST:** `supabase>=2.3.0` in requirements.txt
   [Source: backend/requirements.txt]

6. **ADR-2:** Supabase SDK restricted to file storage + auth forwarding + realtime ONLY
   [Source: backend/docs/adr/002-database-access-pattern.md]

**WHAT'S MISSING:**
- No RLS policies for storage buckets (per-user file isolation at DB level)
- No unit tests for storage_service.py or supabase_client.py
- No virus scanning documentation

### Previous Story Intelligence (0-12)

- CI/CD pipeline fully configured with coverage thresholds
- 349 unit tests passing (plus 2 pre-existing failures, 2 pre-existing errors)
- Mock patterns well established: `MagicMock` for sync, `AsyncMock` for async, `patch` for module-level
- Pre-existing failures: test_tier_enforcement (regex mismatch), test_health (ColdEmailRequest undefined)

### Technical Requirements

**RLS Policies for Storage:**
Supabase Storage uses PostgreSQL RLS. Policies are applied to the `storage.objects` table:
```sql
-- Allow users to upload files to their own folder
CREATE POLICY "Users can upload own files"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'resumes' AND (storage.foldername(name))[1] = auth.uid()::text);

-- Allow users to read their own files
CREATE POLICY "Users can read own files"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'resumes' AND (storage.foldername(name))[1] = auth.uid()::text);

-- Allow users to update their own files
CREATE POLICY "Users can update own files"
ON storage.objects FOR UPDATE
TO authenticated
USING (bucket_id = 'resumes' AND (storage.foldername(name))[1] = auth.uid()::text);

-- Allow users to delete their own files
CREATE POLICY "Users can delete own files"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'resumes' AND (storage.foldername(name))[1] = auth.uid()::text);
```

Note: Our app uses Clerk for auth (not Supabase Auth), so the RLS policies use `auth.uid()` which maps to the Clerk user_id when Supabase is configured with Clerk JWT forwarding. The application-level code already enforces `{user_id}/` prefix isolation, so the RLS policies are a defense-in-depth measure.

**Virus scanning:** Supabase doesn't expose a virus scanning API. It's configured at the dashboard level under Storage > Settings. Document this as a production setup step.

**Test mocking strategy:** The storage functions use `_get_storage()` which calls `get_client().storage`. Mock at the `_get_storage` level to avoid needing a real Supabase connection:
```python
@patch("app.services.storage_service._get_storage")
async def test_upload_file(mock_storage):
    mock_bucket = MagicMock()
    mock_storage.return_value.from_.return_value = mock_bucket
    ...
```

### Library/Framework Requirements

**No new dependencies needed.** All packages already installed.

### File Structure Requirements

**Files to CREATE:**
```
supabase/migrations/00004_storage_rls_policies.sql
supabase/migrations/00004_storage_rls_policies_rollback.sql
backend/tests/unit/test_services/test_storage_service.py
```

**Files to MODIFY:**
```
backend/app/services/storage_service.py     # Add virus scanning documentation comment only
```

**Files to NOT TOUCH:**
```
backend/app/db/supabase_client.py            # Already complete
backend/app/api/v1/onboarding.py             # Already has upload endpoint
backend/app/config.py                        # Already has SUPABASE_URL/KEY
backend/requirements.txt                     # supabase already installed
```

### Testing Requirements

- **Backend Framework:** Pytest + pytest-asyncio
- **Mocking:** Mock `_get_storage()` return value, mock `settings` for graceful degradation tests
- **Coverage target:** >80% for storage_service.py
- **Tests to write:**
  - upload_file: calls supabase with correct bucket/path/options
  - upload_file: returns path when supabase not configured (graceful degradation)
  - upload_file: rejects files >10MB
  - upload_file: rejects unsupported extensions (.txt, .exe)
  - upload_file: rejects unsupported content types
  - upload_file: handles 409 duplicate via upsert
  - get_signed_url: returns URL with correct expiry
  - get_signed_url: returns placeholder when supabase not configured
  - delete_file: removes file and returns True
  - delete_file: returns placeholder True when supabase not configured
  - delete_file: returns False on exception

### References

- [Source: backend/app/services/storage_service.py] — Full storage service
- [Source: backend/app/db/supabase_client.py] — Supabase client singleton
- [Source: backend/app/config.py] — SUPABASE_URL, SUPABASE_KEY settings
- [Source: backend/docs/adr/002-database-access-pattern.md] — ADR-2: Supabase usage restrictions
- [Source: backend/app/api/v1/onboarding.py] — Upload endpoint

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
SIMPLE (score: 4/16) — direct execution, no GSD subagents

### Debug Log References
None — clean implementation

### Completion Notes List
- Created RLS policies for storage.objects enforcing per-user file isolation (INSERT, SELECT, UPDATE, DELETE)
- Created rollback migration for RLS policies
- 14 comprehensive tests covering upload, signed URLs, deletion, validation, graceful degradation, and upsert handling
- Documented virus scanning as Supabase dashboard configuration

### Change Log
- 2026-02-01: Implemented RLS policies + 14 tests + virus scanning docs

### File List
**Created:**
- `supabase/migrations/00004_storage_rls_policies.sql`
- `supabase/migrations/00004_storage_rls_policies_rollback.sql`
- `backend/tests/unit/test_services/test_storage_service.py`

**Modified:**
- `backend/app/services/storage_service.py` — added virus scanning documentation comment
