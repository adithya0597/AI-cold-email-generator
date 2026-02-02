# Epic 8 Retrospective: Interview Preparation

Status: done

## Summary

Epic 8 delivered a complete interview preparation pipeline across 8 stories, covering the Interview Intel Agent orchestrator, company research synthesis, interviewer background research, common interview question generation, STAR response suggestions, prep briefing delivery, calendar interview detection, and an interview prep empty state. All stories were assessed as SIMPLE complexity and completed successfully with 98 tests passing (88 backend + 10 frontend). Code review found 19 issues (6 HIGH, 8 MEDIUM, 5 LOW); 3 HIGH issues were false positives after verification, and all real HIGH and MEDIUM issues were fixed.

## Metrics

- Stories: 8 completed (8-1 through 8-8)
- Tests: 98 passing (88 backend + 10 frontend)
- Code Review Issues: 19 found (6 HIGH, 8 MEDIUM, 5 LOW); 3 HIGH false positives; all real HIGH and MEDIUM fixed
- Complexity: All 8 stories scored SIMPLE (0-4) in assessment
- Route: All SIMPLE — direct execution, no GSD subagents

## What Went Well

- **Consistent service pattern across all research services**: CompanyResearchService (8-2) established the pattern (dataclass result + service class + LLM synthesis + graceful degradation + `to_dict()`), and stories 8-3, 8-4, 8-5 followed it predictably. This made implementation fast and review consistent.
- **Stub-first architecture worked well**: Story 8-1 created the full agent skeleton with stubs, and stories 8-2 through 8-5 replaced stubs with real implementations. This allowed parallel development potential and kept each story's scope tight.
- **Code review caught real issues that TDD missed (again)**: H4 (missing serialization fields in `to_dict()`), H6 (sequential LLM calls where parallel was needed), and H1 (Redis connection per call instead of pool) were all issues that passing tests did not surface.
- **False positive verification prevented unnecessary changes**: 3 of 6 HIGH issues from code review were verified as false positives (H3: method IS async, H5: `AgentOutput.to_dict()` exists, M8: frontend test count correct). Checking before fixing avoided wasted effort and unnecessary code churn.
- **Calendar detection pattern matching is self-contained**: Story 8-7 implemented calendar interview detection as a pure logic service (no external API dependencies), making it testable and portable. Actual calendar API integration was correctly deferred.
- **Good test counts per story**: 17 (8-1), 14 (8-2), 13 (8-3), 12 (8-4), 9 (8-5), 8 (8-6), 15 (8-7), 10 (8-8) — no story had weak coverage.

## What Could Improve

- **Sequential LLM calls slipped through in two stories**: Both interviewer research (8-3, H6) and STAR suggestions (8-5, M2) originally used sequential for-loops for LLM calls that could run in parallel. This should have been caught during implementation, not code review.
- **Redis connection anti-pattern in prep_delivery (8-6)**: Creating a new `aioredis.from_url()` connection per call instead of using the existing `get_redis_client()` pool was a clear miss of an established codebase pattern. Story Dev Notes should have referenced the Redis client utility.
- **`to_dict()` completeness not validated by tests**: H4 showed that `GeneratedQuestions.to_dict()` silently dropped fields (`seniority`, `data_quality`). Tests checked that `to_dict()` returned a dict, but didn't assert all fields were present. Round-trip serialization tests would catch this.
- **Story 8-3 and 8-4 Dev Agent Records were sparse**: Unlike 8-1 and 8-2 which had detailed records with model, route, GSD usage, and debug logs, stories 8-3 through 8-8 had abbreviated records. This makes traceability harder.
- **No integration test for full briefing pipeline**: The complete flow (detect interview → trigger agent → company research → interviewer research → questions → STAR → assemble → schedule delivery) is only tested in isolated units. Same gap noted in Epic 7 retro.

## Key Decisions & Rationale

- **LLM synthesis with stub web search**: All research services (company, interviewer, questions, STAR) use LLM synthesis but have stub web search methods. Real web search integration (Serper, SerpAPI, etc.) was intentionally deferred to keep stories focused on data shape and synthesis logic. LLMs generate baseline knowledge from training data even without search results.
- **`asyncio.gather()` for parallel LLM calls**: Code review identified sequential LLM loops in 8-3 and 8-5 and replaced them with `asyncio.gather()`. This is the correct pattern for I/O-bound parallel work in async Python, with per-item error handling inside the gather tasks.
- **Redis connection pooling via `get_redis_client()`**: Instead of per-call `aioredis.from_url()`, the existing shared pool from `app.cache.redis_client` was used. This avoids connection exhaustion under load and follows the established pattern.
- **Calendar detection as pure logic service**: Story 8-7 implements pattern matching on calendar event dicts rather than directly calling Google/Outlook APIs. This keeps the detection logic testable without API mocks and allows the API integration to be added later as a thin adapter.
- **Frontend empty state follows H1BEmptyState pattern**: Story 8-8 used the same component structure as the H1B empty state from Epic 7, maintaining UI consistency.

## Lessons Learned

- **Always use `asyncio.gather()` for independent LLM calls**: Sequential for-loops over LLM calls are an O(N) latency pattern. When calls are independent (different inputs, no shared state), `asyncio.gather()` reduces to O(1) latency with per-item error handling. This should be a default pattern, not a code review fix.
- **`to_dict()` methods need round-trip assertion tests**: A `to_dict()` that silently drops fields is a serialization bug that only surfaces when consumers expect the missing fields. Tests should assert `set(result.to_dict().keys()) == expected_keys` or round-trip through construction.
- **Verify code review findings before fixing**: 3 of 6 HIGH findings were false positives. Blind fixing would have introduced unnecessary changes. Always verify by reading the actual code (grep, read) before making review-driven fixes.
- **Reference existing utility modules in Dev Notes**: The Redis pool (`app.cache.redis_client`) was already in the codebase but wasn't referenced in story 8-6's Dev Notes. If Dev Notes had listed it, the anti-pattern would have been avoided. Future stories should include "Existing utilities to use" in Dev Notes.
- **Code review false positive rate correlates with codebase familiarity**: The adversarial reviewer didn't have full context of `base.py:44` (`to_dict()`) or async method signatures, leading to 3 false positives. Providing more codebase context to the reviewer or having it read key base classes first could reduce this.

## Recommendations for Next Epic

- **Add "Existing utilities to use" section to Dev Notes**: Each story's Dev Notes should reference relevant shared utilities (Redis client, LLM client, base classes) to prevent anti-patterns.
- **Default to `asyncio.gather()` for multi-item LLM calls**: Make this a standing architectural rule in the project context file so all agents/services use parallel patterns from the start.
- **Add round-trip serialization tests**: For any dataclass with `to_dict()`, add a test that asserts all fields are present in the serialized output.
- **Establish the integration test pattern**: This was recommended in the Epic 7 retro and still hasn't been addressed. Before Epic 9, create a reusable pattern for end-to-end agent pipeline tests.
- **Standardize Dev Agent Records**: All stories should use the full template (Model, Route, GSD Usage, Debug Logs, Completion Notes, Change Log, File List) rather than abbreviated bullet points.
