# Story 8.4: Common Interview Questions

Status: done

## Story

As a **user**,
I want **likely interview questions for my specific role**,
so that **I can prepare answers in advance**.

## Acceptance Criteria

1. **AC1 - Question Generation:** Given I have an interview for a specific role type, when I view the prep briefing, then I see 10-15 likely questions.
2. **AC2 - Categories:** Questions categorized as: Behavioral, Technical, Company-specific, Role-specific.
3. **AC3 - Seniority Tailoring:** Questions tailored to seniority level.
4. **AC4 - Integration:** InterviewIntelAgent._generate_questions() calls QuestionGenerationService.
5. **AC5 - Graceful Degradation:** When LLM fails, returns fallback questions.

## Tasks / Subtasks

- [x] Task 1: Create QuestionGenerationService in backend/app/services/research/question_generation.py (AC: #1-#3)
- [x] Task 2: Replace stub in InterviewIntelAgent._generate_questions() (AC: #4)
- [x] Task 3: Write tests (AC: #1-#5)

## Dev Notes

- Files to CREATE: backend/app/services/research/question_generation.py, backend/tests/unit/test_services/test_question_generation.py
- Files to MODIFY: backend/app/agents/core/interview_intel_agent.py (replace _generate_questions stub)
- Mock path: patch("app.core.llm_clients.LLMClient")

## Dev Agent Record

- Tests: 12 new tests, all passing (56 total with existing 8-1/8-2/8-3)
- Files created: question_generation.py, test_question_generation.py
- Files modified: interview_intel_agent.py (replaced _generate_questions stub)
- No regressions in existing tests
- 2026-02-02: Code review fix — GeneratedQuestions.to_dict() now includes seniority and data_quality fields (H4)
