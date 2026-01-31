---
phase: "02"
plan: "03"
subsystem: onboarding-backend
tags: [resume-parser, openai-structured-outputs, linkedin, fastapi, onboarding]
depends_on:
  requires: ["02-01"]
  provides: ["resume-parser-service", "linkedin-extractor-service", "onboarding-api-endpoints"]
  affects: ["02-05", "02-06"]
tech_stack:
  added: []
  patterns: ["openai-sdk-v2-structured-outputs", "graceful-degradation"]
key_files:
  created:
    - backend/app/services/resume_parser.py
    - backend/app/services/linkedin_extractor.py
    - backend/app/api/v1/onboarding.py
  modified:
    - backend/app/api/v1/router.py
decisions:
  - id: "02-03-01"
    title: "Resume parser uses OpenAI SDK v2 structured outputs (not raw httpx)"
    context: "llm_clients.py uses raw httpx, but structured outputs require SDK beta.chat.completions.parse()"
    choice: "Direct AsyncOpenAI SDK usage for resume parsing, separate from legacy httpx client"
  - id: "02-03-02"
    title: "ensure_user_exists imported from preferences.py (shared dependency)"
    context: "Both onboarding and preferences need ensure_user_exists. Plan 04 created it first in preferences.py."
    choice: "Import from preferences.py rather than duplicating. Can extract to shared module later."
  - id: "02-03-03"
    title: "LinkedIn extraction designed for graceful failure"
    context: "LinkedIn blocks scraping. Per ADR-5, resume upload is primary."
    choice: "extract_from_linkedin_url returns None on any failure, never raises exceptions"
metrics:
  duration: "~4 min"
  completed: "2026-01-31"
---

# Phase 2 Plan 03: Resume Upload + Profile Extraction Backend Summary

**One-liner:** OpenAI structured outputs for resume parsing (GPT-4o-mini + Pydantic response_format), graceful LinkedIn extraction, and 5 onboarding API endpoints with auth + analytics.

## What Was Built

### Task 1: Resume Parser Service
- **ExtractedProfile** Pydantic model with WorkExperience and Education sub-models
- PDF text extraction via PyPDF2 with image-based PDF detection (< 50 chars = image-based)
- DOCX text extraction via python-docx with empty document detection
- LLM extraction using `AsyncOpenAI().beta.chat.completions.parse()` with `response_format=ExtractedProfile`
- Truncates resume text to 8000 chars (~2K tokens) before sending to GPT-4o-mini

### Task 2: LinkedIn Extractor Service
- URL validation (must contain `linkedin.com/in/`)
- 15-second HTTP timeout with proper User-Agent header
- JSON-LD structured data parsing for Person schema
- Open Graph meta tag fallback parsing
- Returns `None` on any failure -- never raises exceptions to caller
- Imports ExtractedProfile from resume_parser to share the same model

### Task 3: Onboarding API Endpoints
Five endpoints registered under `/api/v1/onboarding`:
- `GET /status` -- returns onboarding_status + display_name
- `POST /resume/upload` -- accepts UploadFile, validates type/size, stores in Supabase, extracts via LLM, returns extracted profile for review
- `POST /linkedin/extract` -- accepts URL, returns profile or 422 with fallback message
- `PUT /profile/confirm` -- upserts Profile record, updates User.display_name and onboarding_status
- `GET /profile` -- returns current profile for review editing

All endpoints use Clerk auth via `ensure_user_exists` dependency (imported from preferences.py).
PostHog events tracked: `profile_extraction_completed`, `profile_extraction_failed`, `profile_extraction_method_chosen`, `profile_confirmed`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Shared ensure_user_exists dependency**
- **Found during:** Task 3
- **Issue:** Plan specified defining `ensure_user_exists` in onboarding.py, but Plan 04 (parallel) already created it in preferences.py
- **Fix:** Imported from preferences.py instead of duplicating
- **Files modified:** backend/app/api/v1/onboarding.py

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 90a5d22 | Resume parser service with OpenAI structured outputs |
| 2 | 7d2f4bb | LinkedIn profile extractor service with graceful failure |
| 3 | 168eabc | Onboarding API endpoints for resume upload and profile extraction |

## Verification

- Resume parser: ExtractedProfile, extract_text_from_pdf, extract_text_from_docx, extract_profile_from_resume all defined and importable
- LinkedIn extractor: extract_from_linkedin_url defined, returns Optional[ExtractedProfile]
- Onboarding router: 5 routes registered at /api/v1/onboarding/*
- File size limit (10MB) and type validation (.pdf, .docx) enforced
- Image-based PDFs return clear error message (ValueError with user-friendly text)
- All endpoints require auth (Depends(ensure_user_exists) which uses get_current_user_id)

## Next Phase Readiness

Plan 03 is complete. The onboarding backend is ready for:
- **Plan 05** (Onboarding Frontend): All API endpoints exist for resume upload, LinkedIn extraction, profile confirmation, and status checking
- **Plan 06** (Preference Wizard): Onboarding status transitions are in place for the full flow
