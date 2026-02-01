# Story 5.5: Cover Letter Generator

Status: review

## Story

As a **user**,
I want **AI-generated cover letters tailored to each job**,
so that **I can apply with personalized materials quickly**.

## Acceptance Criteria

1. **AC1 - Cover Letter Agent:** Given I have a profile and a saved job, when the CoverLetterAgent is triggered with a job_id, then it generates a cover letter stored as a Document with type=COVER_LETTER and the job_id reference.

2. **AC2 - Content Structure:** Given the cover letter is generated, when I inspect the content, then it includes: company-specific opening, relevant experience highlights, skills-to-requirements connection, and professional closing with call to action.

3. **AC3 - Word Count:** Given the cover letter is generated, when I measure its length, then it is between 250-400 words.

4. **AC4 - Generation Time:** Given the agent is triggered, when generation completes, then it finishes within 30 seconds (mocked in tests, architecture enforced by model choice).

5. **AC5 - Editability:** Given a cover letter is generated, when I call `GET /api/v1/documents/{document_id}`, then I can retrieve the full cover letter content for editing.

6. **AC6 - Versioning:** Given I regenerate a cover letter for the same job, when stored, then the version is auto-incremented (not overwritten).

7. **AC7 - API Trigger:** Given I am authenticated, when I call `POST /api/v1/documents/cover-letter` with `{job_id}`, then the agent runs and returns the new document_id and content.

8. **AC8 - Tests:** Given the CoverLetterAgent and endpoint exist, when unit tests run, then comprehensive coverage exists for generation, content structure, versioning, authorization, and error cases.

## Tasks / Subtasks

- [x] Task 1: Create CoverLetterAgent (AC: #1, #2, #3, #4)
  - [x]1.1: Create `backend/app/agents/pro/cover_letter_agent.py` following ResumeAgent pattern
  - [x]1.2: Define Pydantic models: `CoverLetterContent` with fields (opening, body_paragraphs, closing, word_count, personalization_sources)
  - [x]1.3: Write system prompt enforcing anti-hallucination + 250-400 word limit + structure requirements
  - [x]1.4: Implement `execute()` — load profile, load job, call LLM with structured output, store Document(type='cover_letter', job_id=job_id)
  - [x]1.5: Include cost tracking via `track_llm_cost()`

- [x] Task 2: Add cover letter API endpoint (AC: #5, #6, #7)
  - [x]2.1: Add `POST /cover-letter` to `backend/app/api/v1/documents.py` — accepts `{job_id}`, runs agent inline, returns document_id + content
  - [x]2.2: Validate job exists and belongs to user
  - [x]2.3: Auto-increment version for same user+job cover letters

- [x] Task 3: Write comprehensive tests (AC: #8)
  - [x]3.1: Create `backend/tests/unit/test_agents/test_cover_letter_agent.py`
  - [x]3.2: Test happy path — agent produces structured CoverLetterContent, stores Document
  - [x]3.3: Test content structure — opening, body, closing all present
  - [x]3.4: Test word count enforcement — content within 250-400 words
  - [x]3.5: Test versioning — second generation for same job gets version 2
  - [x]3.6: Test API endpoint — POST /cover-letter returns document_id
  - [x]3.7: Test authorization — wrong user cannot trigger for another's job
  - [x]3.8: Test missing job — returns 404

## Dev Notes

### Architecture Compliance

**CRITICAL — Follow these patterns EXACTLY:**

1. **Follow the ResumeAgent pattern exactly.** CoverLetterAgent extends BaseAgent, uses `agent_type = "cover_letter"`, overrides `execute()`.
   [Source: backend/app/agents/pro/resume_agent.py]

2. **DocumentType.COVER_LETTER already exists** in the enum. Use `type = 'cover_letter'` when inserting the Document row.
   [Source: backend/app/db/models.py lines 63-65]

3. **Use OpenAI structured output** via `client.beta.chat.completions.parse()` with a Pydantic `response_format`. Same pattern as ResumeAgent._tailor_resume().
   [Source: backend/app/agents/pro/resume_agent.py — _tailor_resume method]

4. **Store content as JSON string** in Document.content via `json.dumps()`. Parse with `json.loads()` on retrieval.

5. **Version auto-increment:** Query `SELECT COALESCE(MAX(version), 0) + 1 FROM documents WHERE user_id=... AND job_id=... AND type='cover_letter'` before inserting.
   [Source: backend/app/agents/pro/resume_agent.py — _store_document method]

6. **Cost tracking:** Call `track_llm_cost(user_id, model, input_tokens, output_tokens, agent_type="cover_letter")` after LLM call.
   [Source: backend/app/observability/cost_tracker.py]

7. **API endpoint runs agent inline** — do NOT dispatch via Celery for this story. The endpoint calls `CoverLetterAgent().execute()` directly and returns the result. Celery integration is a separate concern for background processing.

8. **Use `Depends(get_current_user_id)` for auth** and `AsyncSessionLocal` with lazy imports. Follow the existing document endpoint patterns.
   [Source: backend/app/api/v1/documents.py]

### Previous Story Intelligence (5-4)

- 28 tests passing for documents API (test_documents.py) after code review fixes
- Code review added `deleted_by` to soft-delete queries, defensive enum comparison, storage failure 502
- Mock pattern: `_mock_session_cm()` for async context manager, patch at source module
- Documents API has 6 endpoints; the new POST /cover-letter will be the 7th
- ATS analysis endpoint pattern reusable for reading generated content

### Library/Framework Requirements

**No new dependencies needed.** OpenAI SDK already installed. Pydantic already available.

### File Structure Requirements

**Files to CREATE:**
```
backend/app/agents/pro/cover_letter_agent.py    # CoverLetterAgent class
backend/tests/unit/test_agents/test_cover_letter_agent.py  # Agent tests
```

**Files to MODIFY:**
```
backend/app/api/v1/documents.py    # Add POST /cover-letter endpoint
backend/tests/unit/test_api/test_documents.py  # Add endpoint tests
```

**Files to NOT TOUCH:**
```
backend/app/agents/pro/resume_agent.py   # Reference only
backend/app/db/models.py                 # DocumentType.COVER_LETTER already exists
backend/app/worker/tasks.py              # Celery task is NOT part of this story
backend/app/agents/orchestrator.py       # Routing is NOT part of this story
```

### Testing Requirements

- **Backend Framework:** Pytest + pytest-asyncio
- **Mocking:** Mock `AsyncSessionLocal`, mock `AsyncOpenAI` (LLM calls), mock `track_llm_cost`
- **Tests to write:**
  - Agent happy path: LLM returns structured CoverLetterContent, stored as Document
  - Content structure: opening, body_paragraphs, closing present and non-empty
  - Word count: content within 250-400 words
  - Versioning: second call for same job gets version=2
  - API POST endpoint: returns document_id and content
  - Authorization: non-owner job → 404
  - Missing job: nonexistent job_id → 404

### References

- [Source: backend/app/agents/pro/resume_agent.py] — Agent pattern, LLM structured output, document storage
- [Source: backend/app/agents/base.py] — BaseAgent, AgentOutput
- [Source: backend/app/db/models.py] — DocumentType.COVER_LETTER enum, Document model
- [Source: backend/app/api/v1/documents.py] — Existing endpoint patterns
- [Source: backend/app/observability/cost_tracker.py] — track_llm_cost function
- [Source: .planning/ROADMAP.md] — Cover letter 250-400 words, company-specific opening

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
SIMPLE (score: 4/16, overridden to SIMPLE by user flag)

### Debug Log References
- No issues encountered. All 12 tests passed on first run.

### Completion Notes List
- Created CoverLetterAgent following ResumeAgent pattern exactly
- CoverLetterContent Pydantic model with opening, body_paragraphs, closing, word_count, personalization_sources
- System prompt enforces 250-400 word limit, anti-hallucination, company-specific personalization
- Uses OpenAI structured output via client.beta.chat.completions.parse()
- Cost tracking via track_llm_cost(agent_type="cover_letter")
- Auto-incrementing version for same user+job cover letters
- POST /cover-letter endpoint validates job ownership, runs agent inline
- 12 comprehensive tests covering all 8 ACs

### Change Log
- 2026-02-01: Created CoverLetterAgent + POST /cover-letter endpoint + 12 tests

### File List
**Created:**
- `backend/app/agents/pro/cover_letter_agent.py` — CoverLetterAgent class
- `backend/tests/unit/test_agents/test_cover_letter_agent.py` — 12 tests

**Modified:**
- `backend/app/api/v1/documents.py` — Added POST /cover-letter endpoint
