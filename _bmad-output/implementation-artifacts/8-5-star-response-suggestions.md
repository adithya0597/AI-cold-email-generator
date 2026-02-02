# Story 8.5: STAR Response Suggestions

Status: done

## Story

As a **user**,
I want **STAR-formatted response suggestions based on my experience**,
so that **I can answer behavioral questions effectively**.

## Acceptance Criteria

1. **AC1 - STAR Generation:** Given a behavioral question, when I view response suggestions, then agent generates STAR outline using my profile.
2. **AC2 - Multiple Options:** 2-3 experience options suggested per question.
3. **AC3 - Profile-Based:** Suggestions use user profile data (skills, experience).
4. **AC4 - Integration:** InterviewIntelAgent._generate_star_suggestions() calls StarSuggestionService.
5. **AC5 - Graceful Degradation:** When LLM fails, returns generic STAR template.

## Tasks / Subtasks

- [x] Task 1: Create StarSuggestionService in backend/app/services/research/star_suggestions.py (AC: #1-#3)
- [x] Task 2: Replace stub in InterviewIntelAgent._generate_star_suggestions() (AC: #4)
- [x] Task 3: Write tests (AC: #1-#5)

## Dev Notes

- Files to CREATE: backend/app/services/research/star_suggestions.py, backend/tests/unit/test_services/test_star_suggestions.py
- Files to MODIFY: backend/app/agents/core/interview_intel_agent.py (replace _generate_star_suggestions stub)
- Mock path: patch("app.core.llm_clients.LLMClient")

## Dev Agent Record

- Tests: 9 new tests, all passing (65 total with existing 8-1/8-2/8-3/8-4)
- Files created: star_suggestions.py, test_star_suggestions.py
- Files modified: interview_intel_agent.py (replaced _generate_star_suggestions stub)
- No regressions in existing tests
- 2026-02-02: Code review fix — replaced sequential for-loop with asyncio.gather() for parallel STAR generation (M2)
