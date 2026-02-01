# Story 5.4: ATS Optimization Logic

Status: done

## Story

As a **user**,
I want **my tailored resume analyzed for ATS compatibility**,
so that **my application passes automated screening systems**.

## Acceptance Criteria

1. **AC1 - ATS Analysis Endpoint:** Given I have a tailored resume, when I call `GET /api/v1/documents/{document_id}/ats-analysis`, then I receive a structured ATS analysis with score, keyword match details, and format recommendations.

2. **AC2 - ATS Score:** Given the analysis runs, when it evaluates the tailored resume, then an ATS score (0-100) is returned based on keyword match percentage between job description and resume content.

3. **AC3 - Low Score Warning:** Given the ATS score is below 70, when the analysis completes, then a warning is included with text: "Consider adding: [list of missing keywords]".

4. **AC4 - Keyword Analysis:** Given the analysis runs, when I inspect the response, then it includes `keywords_matched`, `keywords_missing`, and `match_rate` (0.0-1.0).

5. **AC5 - Format Recommendations:** Given the analysis runs, when I inspect the response, then it includes ATS-friendly format recommendations (e.g., no tables, simple fonts, standard section headings).

6. **AC6 - Authorization:** Given I request analysis for a document I don't own, when the endpoint processes, then it returns 404.

7. **AC7 - Validation:** Given I request analysis for a master resume (no job_id) or non-resume document, when the endpoint processes, then it returns 400.

8. **AC8 - Tests:** Given the ATS analysis endpoint exists, when unit tests run, then comprehensive coverage exists for scoring, warnings, keyword analysis, format recommendations, and error cases.

## Tasks / Subtasks

- [x] Task 1: Create ATS analysis endpoint (AC: #1, #2, #3, #4, #5, #6, #7)
  - [x]1.1: Add `GET /{document_id}/ats-analysis` route to `backend/app/api/v1/documents.py`
  - [x]1.2: Load tailored document, verify ownership and type=resume with job_id set
  - [x]1.3: Parse Document.content JSON to extract ATS score, keywords_incorporated, keywords_missing
  - [x]1.4: Calculate match_rate from keywords data
  - [x]1.5: Generate warning when score < 70 with missing keywords
  - [x]1.6: Include ATS format recommendations (static best practices)
  - [x]1.7: Return structured analysis response

- [x] Task 2: Write comprehensive tests (AC: #8)
  - [x]2.1: Add tests to `backend/tests/unit/test_api/test_documents.py`
  - [x]2.2: Test happy path — returns score, keywords, match_rate, recommendations
  - [x]2.3: Test low score warning — score < 70 includes warning with missing keywords
  - [x]2.4: Test high score — score >= 70 has no warning
  - [x]2.5: Test authorization — wrong user gets 404
  - [x]2.6: Test validation — master resume returns 400
  - [x]2.7: Test format recommendations present

## Dev Notes

### Architecture Compliance

**CRITICAL — Follow these patterns EXACTLY:**

1. **ATS data already exists in Document.content.** The ResumeAgent stores `ats_score`, `keywords_incorporated`, `keywords_missing` in the TailoredResume JSON. The endpoint reads and enriches this data — NO LLM call needed.
   [Source: backend/app/agents/pro/resume_agent.py lines 39-46]

2. **Add endpoint to EXISTING documents.py** — the ATS analysis is a sub-resource of a document, same as the diff endpoint.

3. **Format recommendations are STATIC** — a predefined list of ATS best practices. Do not call external services.

4. **Follow the same pattern as the diff endpoint** for loading and validating documents.
   [Source: backend/app/api/v1/documents.py — get_document_diff]

5. **match_rate calculation:** `len(keywords_incorporated) / max(len(keywords_incorporated) + len(keywords_missing), 1)`

### Previous Story Intelligence (5-3)

- 21 tests passing for documents API (test_documents.py)
- Diff endpoint pattern: load tailored doc → validate → parse JSON → build response
- Change classification pattern reusable for format analysis
- `_make_tailored_content()` helper already creates test fixture with ATS data

### Library/Framework Requirements

**No new dependencies needed.**

### File Structure Requirements

**Files to CREATE:**
```
(none)
```

**Files to MODIFY:**
```
backend/app/api/v1/documents.py           # Add ATS analysis endpoint
backend/tests/unit/test_api/test_documents.py  # Add ATS analysis tests
```

**Files to NOT TOUCH:**
```
backend/app/agents/pro/resume_agent.py  # ATS scoring is already done by the agent
backend/app/db/models.py                # Document model is complete
```

### Testing Requirements

- **Backend Framework:** Pytest + pytest-asyncio
- **Mocking:** Mock `AsyncSessionLocal` only
- **Tests to write:**
  - Happy path: score, keywords, match_rate, recommendations
  - Low score warning: score < 70 includes "Consider adding" warning
  - High score: no warning
  - Authorization: non-owner → 404
  - Validation: master resume → 400
  - Format recommendations present

### References

- [Source: backend/app/agents/pro/resume_agent.py] — TailoredResume model, ATS score calculation
- [Source: backend/app/api/v1/documents.py] — get_document_diff pattern
- [Source: .planning/ROADMAP.md] — "ATS Score" calculated (0-100), score below 70 triggers warning

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
SIMPLE (score: 2/16, overridden to SIMPLE by user flag)

### Debug Log References
- No issues encountered. All 6 new tests passed on first run.

### Completion Notes List
- Added GET /{document_id}/ats-analysis endpoint to documents.py
- Reads existing ATS data from TailoredResume JSON in Document.content
- Calculates match_rate from keywords_incorporated / total_keywords
- Warning generated when ats_score < 70 with "Consider adding: [missing keywords]"
- Static ATS format recommendations (8 best practices)
- 6 comprehensive tests covering all 8 ACs

### Change Log
- 2026-02-01: Added ATS analysis endpoint + 6 tests
- 2026-02-01: Code review fixes — defensive enum type comparison, moved validation inside session block

### File List
**Created:**
(none)

**Modified:**
- `backend/app/api/v1/documents.py` — Added GET /{document_id}/ats-analysis endpoint + _ATS_FORMAT_RECOMMENDATIONS
- `backend/tests/unit/test_api/test_documents.py` — Added 6 ATS analysis tests
