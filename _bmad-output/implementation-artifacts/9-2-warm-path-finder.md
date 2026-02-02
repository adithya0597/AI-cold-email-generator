# Story 9.2: Warm Path Finder

Status: done

## Story

As a **user**,
I want **to discover connections who can introduce me to target companies**,
So that **I can leverage my network for warm introductions**.

## Acceptance Criteria

1. **AC1: Warm path analysis** — Given I have saved jobs or target companies, when the Network Agent analyzes my connections, then I see warm paths categorized as: 1st degree (direct connections at target), 2nd degree (connections who know someone at target), Alumni (same school/company alumni at target).
2. **AC2: Path strength scoring** — Given warm paths are identified, when displayed, then each path has a strength score: strong, medium, or weak based on relationship recency, mutual connections, and interaction history.
3. **AC3: Suggested actions** — Given warm paths exist, when I view them, then each path includes a suggested action like "Ask [Connection] for intro to [Target]".
4. **AC4: Integration with NetworkAgent** — Given the warm path service is implemented, when `NetworkAgent._analyze_warm_paths()` is called, then it delegates to WarmPathService instead of returning stub data.
5. **AC5: Graceful degradation** — Given connection data is incomplete, when analysis runs, then the service returns partial results with available data and logs the gap.

## Tasks / Subtasks

- [x] Task 1: Create WarmPathService (AC: #1, #2, #3, #5)
  - [x] 1.1 Create `backend/app/services/network/warm_path.py` with `WarmPathService` class
  - [x] 1.2 Define `WarmPath` dataclass with fields: `contact_name`, `company`, `path_type` (1st_degree/2nd_degree/alumni), `strength` (strong/medium/weak), `relationship_context`, `suggested_action`, `mutual_connections`, `data_quality`
  - [x] 1.3 Implement `async analyze(target_companies: list[str], connection_data: dict) -> list[WarmPath]` that uses LLM to synthesize connection analysis
  - [x] 1.4 Implement `_score_path_strength(path: WarmPath) -> str` that scores based on relationship recency, mutual connections, interaction depth
  - [x] 1.5 Implement `_generate_suggested_action(path: WarmPath) -> str` that creates actionable suggestions
  - [x] 1.6 Add `to_dict()` method on WarmPath including ALL fields
  - [x] 1.7 Add graceful degradation: wrap in try/except, return partial results with `data_quality` field

- [x] Task 2: Replace stub in NetworkAgent._analyze_warm_paths() (AC: #4)
  - [x] 2.1 Import and call WarmPathService.analyze()
  - [x] 2.2 Return list[dict] via .to_dict()

- [x] Task 3: Write tests (AC: #1-#5)
  - [x] 3.1 Create `backend/tests/unit/test_services/test_warm_path.py`
  - [x] 3.2 Test analyze() returns WarmPath list with correct structure
  - [x] 3.3 Test path types (1st_degree, 2nd_degree, alumni) are correctly categorized
  - [x] 3.4 Test strength scoring logic
  - [x] 3.5 Test suggested actions are generated
  - [x] 3.6 Test graceful degradation on LLM failure
  - [x] 3.7 Test to_dict() includes ALL fields
  - [x] 3.8 Test agent integration calls service

## Dev Notes

### Architecture Compliance

- **Service location**: `backend/app/services/network/warm_path.py` — new `network/` subdirectory following `research/` pattern
- **Data structure**: Use `@dataclass` for `WarmPath` (consistent with `AgentOutput`, `CompanyResearchResult` patterns)
- **LLM client pattern**: Use existing `LLMClient` from `app.core.llm_clients`. Mock at `app.core.llm_clients.LLMClient`.
- **Connection data is simulated**: Real LinkedIn API integration is deferred. The service accepts connection_data dict (simulating imported connections) and uses LLM to reason about potential paths.
- **Integration with 9-1**: Replace `NetworkAgent._analyze_warm_paths()` stub. Return shape MUST match what `_assemble_network_analysis()` expects.
- **Use asyncio.gather()**: If analyzing multiple companies, run analyses in parallel.

### Existing Utilities to Use

- `LLMClient` from `app.core.llm_clients` — for LLM synthesis
- Follow `CompanyResearchService` pattern from `backend/app/services/research/company_research.py`

### Previous Story Intelligence (9-1)

- Stub returns list of dicts with keys: `company`, `paths` (list of path dicts)
- `_assemble_network_analysis()` accesses warm_paths data — ensure key compatibility

### Project Structure Notes

- Service file: `backend/app/services/network/warm_path.py`
- Create `backend/app/services/network/__init__.py`
- Test file: `backend/tests/unit/test_services/test_warm_path.py`
- Modified file: `backend/app/agents/core/network_agent.py` (replace stub)

### References

- [Source: backend/app/services/research/company_research.py — Reference service pattern]
- [Source: backend/app/agents/core/network_agent.py — stub to replace]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Debug Log References
N/A

### Completion Notes List
- 17 tests passing for warm path service
- WarmPathService with asyncio.gather for parallel company analysis
- WarmPath dataclass with to_dict() including all 8 fields
- Strength scoring based on path type, mutual connections, depth
- Graceful degradation on LLM failure returns partial results
- NetworkAgent._analyze_warm_paths() delegates to service

### File List
- backend/app/services/network/__init__.py (created)
- backend/app/services/network/warm_path.py (created)
- backend/tests/unit/test_services/test_warm_path.py (created)
- backend/app/agents/core/network_agent.py (modified)
