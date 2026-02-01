# Story 5.6: Cover Letter Personalization

Status: review

## Story

As a **user**,
I want **cover letters to include company-specific details**,
so that **they don't feel generic or AI-generated**.

## Acceptance Criteria

1. **AC1 - Company Research in Prompt:** Given company research data is available in the job record, when the CoverLetterAgent generates a letter, then the prompt includes company details (mission, values, recent news from job description).

2. **AC2 - Personalization Sources Tracking:** Given a cover letter is generated, when I inspect the response, then `personalization_sources` lists what specific company details were referenced.

3. **AC3 - Graceful Fallback:** Given no company research is available (job description is minimal), when the agent generates a letter, then it uses a professional generic approach without hallucinating company details.

4. **AC4 - Personalization Display:** Given a cover letter is generated, when I call `GET /api/v1/documents/{document_id}`, then the response includes a `personalization_sources` field showing what research was used.

5. **AC5 - Tests:** Given the personalization logic exists, when unit tests run, then coverage exists for personalized generation, graceful fallback, and personalization source tracking.

## Tasks / Subtasks

- [x] Task 1: Enhance CoverLetterAgent prompt with company context (AC: #1, #2, #3)
  - [x]1.1: Update `_build_prompt()` in cover_letter_agent.py to extract and highlight company-specific details from job description
  - [x]1.2: Update system prompt to instruct LLM to reference company details when available and fall back gracefully when not
  - [x]1.3: Ensure `personalization_sources` in CoverLetterContent captures what was used

- [x] Task 2: Add personalization sources to document retrieval (AC: #4)
  - [x]2.1: No endpoint change needed — personalization_sources is already stored in Document.content JSON and returned by POST /cover-letter

- [x] Task 3: Write personalization tests (AC: #5)
  - [x]3.1: Add tests to `backend/tests/unit/test_agents/test_cover_letter_agent.py`
  - [x]3.2: Test prompt includes company details when job has rich description
  - [x]3.3: Test graceful fallback — minimal job description still generates valid letter
  - [x]3.4: Test personalization_sources is non-empty in output

## Dev Notes

### Architecture Compliance

**CRITICAL — Follow these patterns EXACTLY:**

1. **Personalization is a PROMPT enhancement, not a separate service.** The CoverLetterAgent's `_build_prompt()` method extracts company context from the job description. There is NO separate company research service in this story.

2. **CoverLetterContent.personalization_sources already exists** from story 5-5. This field tracks what details were referenced. The LLM fills it in during structured output.

3. **Graceful fallback is handled by the system prompt.** Add instructions like: "If the job description doesn't mention company mission, values, or recent news, write a professional letter focused on the role itself. Never fabricate company details."

4. **DO NOT create external API calls** for company research. Company context comes ONLY from the job record's description field.

5. **This is a minimal enhancement** to the existing CoverLetterAgent — NOT a new agent or service.

### Previous Story Intelligence (5-5)

- 12 tests passing for CoverLetterAgent
- CoverLetterContent model has: opening, body_paragraphs, closing, word_count, personalization_sources
- System prompt already mentions company-specific opening
- `_build_prompt()` already includes job description, title, company, location
- POST /cover-letter endpoint already returns personalization_sources

### Library/Framework Requirements

**No new dependencies needed.**

### File Structure Requirements

**Files to CREATE:**
```
(none)
```

**Files to MODIFY:**
```
backend/app/agents/pro/cover_letter_agent.py   # Enhance _build_prompt() and system prompt
backend/tests/unit/test_agents/test_cover_letter_agent.py  # Add personalization tests
```

**Files to NOT TOUCH:**
```
backend/app/api/v1/documents.py   # Endpoint already returns personalization_sources
backend/app/db/models.py          # No model changes needed
```

### Testing Requirements

- **Backend Framework:** Pytest + pytest-asyncio
- **Tests to write:**
  - Prompt includes company details from rich job description
  - Graceful fallback with minimal description
  - personalization_sources is populated in agent output

### References

- [Source: backend/app/agents/pro/cover_letter_agent.py] — CoverLetterAgent, _build_prompt, system prompt
- [Source: backend/app/api/v1/documents.py] — POST /cover-letter endpoint

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
SIMPLE (score: 2/16, overridden to SIMPLE by user flag)

### Debug Log References
- No issues encountered. All 5 new tests passed on first run.

### Completion Notes List
- Enhanced system prompt with 3 personalization rules (9-11)
- Added `_extract_company_context()` method that scans job description for mission, product, and growth signals
- `_build_prompt()` now includes ## COMPANY CONTEXT section
- Graceful fallback when no company signals found ("None available")
- 5 new tests covering rich description, mission extraction, product extraction, fallback, and prompt output

### Change Log
- 2026-02-01: Added company context extraction + personalization prompt enhancements + 5 tests

### File List
**Created:**
(none)

**Modified:**
- `backend/app/agents/pro/cover_letter_agent.py` — Enhanced system prompt + _extract_company_context() + _build_prompt()
- `backend/tests/unit/test_agents/test_cover_letter_agent.py` — Added 5 personalization tests
