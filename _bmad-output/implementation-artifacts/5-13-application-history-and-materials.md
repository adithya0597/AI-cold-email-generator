# Story 5.13: Application History and Materials

Status: review

## Story

As a **user**,
I want **to view all past applications and materials sent**,
so that **I can track what I've applied to and reference past materials**.

## Acceptance Criteria

1. **AC1 - List Applications:** Given I am authenticated, when I call `GET /api/v1/applications`, then I see all my applications sorted by date descending with company, title, date, status.

2. **AC2 - Application Detail:** Given an application exists, when I call `GET /api/v1/applications/{id}`, then I see the full application with linked resume and cover letter document IDs.

3. **AC3 - Filter by Status:** Given I pass `?status=applied`, when I call GET /applications, then only applications with that status are returned.

4. **AC4 - Tests:** Given the endpoints exist, when unit tests run, then coverage exists for list, detail, filtering, and not-found.

## Tasks / Subtasks

- [x] Task 1: Add application history endpoints (AC: #1, #2, #3)
  - [x]1.1: Add `GET /applications` — list user's applications with pagination and optional status filter
  - [x]1.2: Add `GET /applications/{id}` — single application with job and material details
  - [x]1.3: Join with jobs table to get title and company

- [x] Task 2: Write tests (AC: #4)
  - [x]2.1: Test list applications with pagination
  - [x]2.2: Test application detail
  - [x]2.3: Test status filter
  - [x]2.4: Test not found

## Dev Notes

### Architecture Compliance

1. **Add to existing applications.py** router (created in 5-8).
2. **Use raw SQL via text()** following the existing patterns.
3. **Join with jobs table** to return job title and company.

### File Structure Requirements

**Files to MODIFY:**
```
backend/app/api/v1/applications.py              # Add history endpoints
backend/tests/unit/test_api/test_applications.py # Add history tests
```

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
SIMPLE (score: 0/16)

### Completion Notes List
- Added GET /applications with pagination, status filter, job join
- Added GET /applications/{id} with material document IDs
- 4 new tests for list, detail, filter, not-found

### Change Log
- 2026-02-01: Added application history endpoints + 4 tests

### File List
**Modified:**
- `backend/app/api/v1/applications.py` — Added GET /applications and GET /applications/{id}
- `backend/tests/unit/test_api/test_applications.py` — Added 4 history tests
