# Story 8.2: Company Research Synthesis

Status: done

## Story

As an **Interview Intel Agent**,
I want **to compile company research into interview-ready insights**,
So that **users can speak knowledgeably about the company**.

## Acceptance Criteria

1. **AC1: Company research data structure** — Given an interview is scheduled, when company research runs, then the briefing includes: company mission and values, recent news (last 6 months), key products/services, competitors and market position, recent challenges or opportunities, and company culture indicators.
2. **AC2: Source attribution** — Given research results are returned, when displayed, then each fact includes a source link or attribution.
3. **AC3: Conversation hooks** — Given research is complete, when the user views the briefing, then "Talk about this" suggestions highlight conversation hooks derived from the research.
4. **AC4: Integration with InterviewIntelAgent** — Given the company research service is implemented, when `InterviewIntelAgent._run_company_research()` is called, then it delegates to the new service instead of returning stub data.
5. **AC5: Graceful degradation** — Given an external data source is unavailable, when research runs, then the service returns partial results with available data rather than failing entirely, and logs the failure.
6. **AC6: Public data only** — Given any research execution, when data is gathered, then only public sources are used (no scraping of sites that prohibit it via robots.txt/ToS).

## Tasks / Subtasks

- [x]Task 1: Create company research service (AC: #1, #2, #5, #6)
  - [x]1.1 Create `backend/app/services/research/company_research.py` with a `CompanyResearchService` class
  - [x]1.2 Implement `async research(company_name: str) -> CompanyResearchResult` that returns a structured dataclass with fields: `mission`, `recent_news` (list of dicts with `title`, `summary`, `source_url`, `date`), `products` (list of strings), `competitors` (list of strings), `culture_indicators` (list of strings), `challenges_opportunities` (list of strings)
  - [x]1.3 Implement `_search_web(query: str) -> list[dict]` stub that returns empty list (real web search integration deferred — this story focuses on the data shape and LLM synthesis pattern)
  - [x]1.4 Implement `_synthesize_with_llm(company_name: str, raw_data: list[dict]) -> CompanyResearchResult` that calls the LLM to synthesize raw search results into structured company insights. Use the established LLM client pattern from the codebase.
  - [x]1.5 Add graceful degradation: wrap each sub-step in try/except, log failures, return partial results with a `data_quality` field indicating completeness

- [x]Task 2: Generate conversation hooks (AC: #3)
  - [x]2.1 Implement `_generate_conversation_hooks(research: CompanyResearchResult) -> list[dict]` that produces "Talk about this" suggestions from the research data
  - [x]2.2 Each hook should have: `topic` (str), `talking_point` (str), `source` (str), `relevance` (str — why this matters in an interview)

- [x]Task 3: Integrate with InterviewIntelAgent (AC: #4)
  - [x]3.1 Replace the stub `_run_company_research()` in `interview_intel_agent.py` with a call to `CompanyResearchService.research()`
  - [x]3.2 Merge conversation hooks into the briefing's `company_research` section
  - [x]3.3 Preserve the existing return shape so `_assemble_briefing()` and existing tests still work

- [x]Task 4: Write unit tests (AC: #1-#6)
  - [x]4.1 Create `backend/tests/unit/test_services/test_company_research.py`
  - [x]4.2 Test `research()` returns complete `CompanyResearchResult` structure when LLM succeeds
  - [x]4.3 Test graceful degradation: when LLM fails, returns partial result with `data_quality = "partial"`
  - [x]4.4 Test conversation hooks are generated from research data
  - [x]4.5 Test integration: `InterviewIntelAgent._run_company_research()` now calls `CompanyResearchService`
  - [x]4.6 Test existing 8-1 tests still pass after stub replacement

## Dev Notes

### Architecture Compliance

- **Service location**: `backend/app/services/research/company_research.py` — follows the existing research service pattern (`h1b_service.py`, `dol_client.py`, etc.)
- **Data structure**: Use a `@dataclass` for `CompanyResearchResult` (not Pydantic BaseModel) — consistent with `AgentOutput` pattern in the agent framework
- **LLM client pattern**: Use the existing LLM integration. Check `backend/app/services/` for the established pattern. If an LLM service module exists, use it. If not, create a minimal wrapper that can be swapped in later stories.
- **Web search is a stub**: The `_search_web()` method should be a stub returning empty results in this story. Real web search integration (e.g., Serper, SerpAPI, or similar) is a separate concern. The LLM synthesis should work even with empty search results by generating baseline knowledge.
- **Integration with 8-1**: Replace `InterviewIntelAgent._run_company_research()` stub. The return shape MUST match what `_assemble_briefing()` expects: a dict with keys `mission`, `recent_news`, `products`, `competitors`, `culture_indicators`. Add new keys (`challenges_opportunities`, `conversation_hooks`, `data_quality`, `sources`) as additional fields — do NOT remove existing keys.
- **Public data only**: Epic 8 DoD requires only public data. Document this constraint in the service docstring.
- **No new DB tables**: Research results are stored as part of the briefing in `agent_outputs` via the existing `BaseAgent._record_output()` flow.
- **No new API endpoints**: This is a backend service called by the agent, not exposed directly via API.

### Previous Story Intelligence (8-1)

- Mock patch paths must target the source module, not the import site (e.g., `app.agents.brake.check_brake` not `app.agents.base.check_brake`)
- The stub in `_run_company_research()` returns: `{"mission": "...", "recent_news": [], "products": [], "competitors": [], "culture_indicators": []}`
- `_assemble_briefing()` accesses `company_research.get("mission")` for the summary — ensure this key is always present
- 17 existing tests in `test_interview_intel_agent.py` must continue to pass after integration

### Project Structure Notes

- Service file: `backend/app/services/research/company_research.py`
- Test file: `backend/tests/unit/test_services/test_company_research.py`
- Modified file: `backend/app/agents/core/interview_intel_agent.py` (replace stub)

### References

- [Source: backend/app/agents/core/interview_intel_agent.py:118-127 — `_run_company_research()` stub to replace]
- [Source: backend/app/agents/core/interview_intel_agent.py:170-196 — `_assemble_briefing()` that consumes company_research]
- [Source: backend/app/services/research/h1b_service.py — Existing research service pattern]
- [Source: backend/app/agents/base.py:33-53 — AgentOutput dataclass pattern]
- [Source: _bmad-output/planning-artifacts/epics.md:2507-2526 — Epic 8, Story 8.2 definition]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Route Taken

SIMPLE (score: 0/16)

### GSD Subagents Used

none (direct execution)

### Debug Log References

- Mock patch paths: LLMClient patched at `app.core.llm_clients.LLMClient` (source module), CompanyResearchService at `app.services.research.company_research.CompanyResearchService`

### Completion Notes List

- Created CompanyResearchService with LLM synthesis and graceful degradation
- CompanyResearchResult dataclass with all required fields + to_dict()
- Conversation hooks generated from mission, news, products, challenges
- Web search is stub (returns empty), LLM works from training knowledge
- Replaced stub in InterviewIntelAgent._run_company_research()
- 14 new tests + 17 existing tests all passing (31 total)

### Change Log

- 2026-02-02: Story implemented, 14 tests passing, 17 existing tests still passing
- 2026-02-02: Code review passed — no issues specific to 8-2

### File List

#### Files to CREATE
- `backend/app/services/research/company_research.py`
- `backend/tests/unit/test_services/test_company_research.py`

#### Files to MODIFY
- `backend/app/agents/core/interview_intel_agent.py`
