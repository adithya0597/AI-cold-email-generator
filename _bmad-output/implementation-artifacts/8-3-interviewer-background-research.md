# Story 8.3: Interviewer Background Research

Status: done

## Story

As an **Interview Intel Agent**,
I want to **research interviewer backgrounds**,
so that **users can build rapport and anticipate perspectives**.

## Acceptance Criteria

1. **AC1 - Interviewer Profile:** Given interviewer name(s) are known, when interviewer research runs, then briefing includes (from public sources only): current role/tenure, career history highlights, LinkedIn posts/articles (if public), speaking topics/publications, shared connections/interests.
2. **AC2 - Privacy:** Research respects privacy (public data only).
3. **AC3 - Conversation Starters:** "Conversation starters" suggested based on common ground.
4. **AC4 - Integration:** InterviewIntelAgent._run_interviewer_research() calls InterviewerResearchService.
5. **AC5 - Graceful Degradation:** When LLM fails, returns partial result for each interviewer.

## Tasks / Subtasks

- [x] Task 1: Create InterviewerResearchService in backend/app/services/research/interviewer_research.py (AC: #1, #2)
  - [x] 1.1: Define InterviewerProfile dataclass with fields: name, current_role, tenure, career_highlights, public_content, speaking_topics, shared_interests, conversation_starters, data_quality
  - [x] 1.2: Implement research(names) -> list[InterviewerProfile]
  - [x] 1.3: Implement _synthesize_interviewer(name) via LLMClient.generate_json()
  - [x] 1.4: Implement _generate_conversation_starters(profile) for common ground

- [x] Task 2: Replace stub in InterviewIntelAgent._run_interviewer_research() (AC: #4)
  - [x] 2.1: Import and call InterviewerResearchService.research()
  - [x] 2.2: Return list[dict] via .to_dict()

- [x] Task 3: Write tests (AC: #1-#5)
  - [x] 3.1: Test service returns InterviewerProfile list
  - [x] 3.2: Test profile has required fields
  - [x] 3.3: Test conversation starters generated
  - [x] 3.4: Test LLM failure graceful degradation
  - [x] 3.5: Test agent integration calls service
  - [x] 3.6: Test privacy (no non-public data fields)

## Dev Notes

- Files to CREATE: backend/app/services/research/interviewer_research.py, backend/tests/unit/test_services/test_interviewer_research.py
- Files to MODIFY: backend/app/agents/core/interview_intel_agent.py (replace _run_interviewer_research stub)
- Mock path: patch("app.core.llm_clients.LLMClient")
- Follow CompanyResearchService pattern

## Dev Agent Record

- Tests: 13 new tests, all passing (44 total with existing 8-1/8-2)
- Files created: interviewer_research.py, test_interviewer_research.py
- Files modified: interview_intel_agent.py (replaced _run_interviewer_research stub)
- No regressions in existing tests
- 2026-02-02: Code review fix — replaced sequential for-loop with asyncio.gather() for parallel interviewer research (H6)
