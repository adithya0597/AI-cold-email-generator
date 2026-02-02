# Story 9.3: Introduction Request Message Drafts

Status: done

## Story

As a **user**,
I want **AI-generated introduction request messages**,
So that **I can reach out professionally without awkwardness**.

## Acceptance Criteria

1. **AC1: Message content** — Given I want to request an introduction, when I view the draft, then the message includes: personalized opening referencing relationship, clear specific ask, context on why interested in target company, easy out ("No worries if not possible").
2. **AC2: Message length** — Given a draft is generated, when displayed, then it is 3-5 sentences in length.
3. **AC3: Edit before sending** — Given a draft exists, when I view it, then I can edit the message before any action.
4. **AC4: Explicit approval required** — Given a draft is finalized, when sending, then it requires my explicit approval. Agent NEVER sends messages without approval.
5. **AC5: Integration with NetworkAgent** — Given the intro draft service is implemented, when `NetworkAgent._generate_intro_drafts()` is called, then it delegates to IntroDraftService.
6. **AC6: Graceful degradation** — When LLM fails, returns a generic template that user can customize.

## Tasks / Subtasks

- [x] Task 1: Create IntroDraftService (AC: #1, #2, #6)
  - [x]1.1 Create `backend/app/services/network/intro_drafts.py` with `IntroDraftService` class
  - [x]1.2 Define `IntroDraft` dataclass with fields: `recipient_name`, `connection_name`, `target_company`, `message`, `tone`, `word_count`, `data_quality`
  - [x]1.3 Implement `async generate(warm_paths: list[dict], user_profile: dict) -> list[IntroDraft]` using LLM
  - [x]1.4 Implement `_build_prompt(path, profile)` that constructs LLM prompt enforcing 3-5 sentence constraint, personalization, and easy-out inclusion
  - [x]1.5 Implement `_get_fallback(path)` returning generic template
  - [x]1.6 Add `to_dict()` method including ALL fields
  - [x]1.7 Use `asyncio.gather()` for parallel draft generation across multiple paths

- [x] Task 2: Replace stub in NetworkAgent._generate_intro_drafts() (AC: #5)
  - [x]2.1 Import and call IntroDraftService.generate()
  - [x]2.2 Return list[dict] via .to_dict()

- [x] Task 3: Write tests (AC: #1-#6)
  - [x]3.1 Create `backend/tests/unit/test_services/test_intro_drafts.py`
  - [x]3.2 Test generate() returns IntroDraft list with correct structure
  - [x]3.3 Test message contains personalized opening, clear ask, context, easy out
  - [x]3.4 Test message length constraint (3-5 sentences)
  - [x]3.5 Test fallback template on LLM failure
  - [x]3.6 Test to_dict() includes ALL fields
  - [x]3.7 Test agent integration calls service

## Dev Notes

### Architecture Compliance

- **Service location**: `backend/app/services/network/intro_drafts.py`
- **Data structure**: `@dataclass` for `IntroDraft`
- **LLM client**: Use `LLMClient` from `app.core.llm_clients`. Mock at source.
- **Approval is handled by the agent/frontend**: This service only generates drafts. The approval workflow (AC#4) is handled by `_queue_for_approval()` in the agent (9-1) and the approval UI (9-6).
- **Use asyncio.gather()** for generating multiple drafts in parallel
- **Follow StarSuggestionService pattern** from `backend/app/services/research/star_suggestions.py`

### Existing Utilities to Use

- `LLMClient` from `app.core.llm_clients`
- `asyncio.gather()` for parallel generation

### Project Structure Notes

- Service file: `backend/app/services/network/intro_drafts.py`
- Test file: `backend/tests/unit/test_services/test_intro_drafts.py`
- Modified file: `backend/app/agents/core/network_agent.py` (replace stub)

### References

- [Source: backend/app/services/research/star_suggestions.py — Reference service pattern with parallel LLM calls]
- [Source: backend/app/agents/core/network_agent.py — stub to replace]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Debug Log References
N/A

### Completion Notes List
- 10 tests passing for intro draft service
- IntroDraftService with asyncio.gather for parallel draft generation
- IntroDraft dataclass with to_dict() including all 7 fields
- Fallback template on LLM failure with easy-out phrase
- NetworkAgent._generate_intro_drafts() delegates to service

### File List
- backend/app/services/network/intro_drafts.py (created)
- backend/tests/unit/test_services/test_intro_drafts.py (created)
- backend/app/agents/core/network_agent.py (modified)
