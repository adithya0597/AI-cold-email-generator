# Story 5.1: Resume Agent Implementation

Status: review

## Story

As a **system**,
I want **a Resume Agent that tailors resumes for specific jobs**,
so that **users have optimized applications without manual editing**.

## Acceptance Criteria

1. **AC1 - Job Analysis:** Given the Resume Agent is triggered for a saved job, when it receives user_id and job_id in task_data, then it analyzes the job description requirements (title, required skills, preferred qualifications, responsibilities).

2. **AC2 - Experience Identification:** Given the agent has loaded the user's master resume (structured profile data), when it processes the job requirements, then it identifies the most relevant experience, skills, and education from the user's profile.

3. **AC3 - Tailored Resume Generation:** Given relevant experience has been identified, when the LLM generates the tailored resume, then it produces structured JSON output with rewritten sections (summary, experience bullets, skills) optimized for the specific job — without inventing qualifications not in the master resume.

4. **AC4 - Document Storage:** Given a tailored resume is generated, when the agent completes, then it stores the tailored version in the `documents` table with type=RESUME, the correct job_id reference, and an incremented version number.

5. **AC5 - Agent Output with Rationale:** Given tailoring completes, when the agent returns its AgentOutput, then it includes: action="resume_tailored", rationale explaining major changes, confidence score, and data containing keyword_gaps, sections_modified, and ats_score.

6. **AC6 - Performance:** Given the agent is triggered, when tailoring runs end-to-end, then it completes within 45 seconds (including LLM calls).

7. **AC7 - Tier Enforcement:** Given the Resume Agent creates artifacts (write action), when dispatched via the orchestrator, then autonomy tier is enforced — L0/L1 users see suggestions only, L2 users queue for approval, L3 users get direct execution.

8. **AC8 - Tests:** Given the Resume Agent exists, when unit tests run, then comprehensive test coverage exists for: LLM tailoring logic, document storage, AgentOutput structure, brake check integration, and error handling.

## Tasks / Subtasks

- [x] Task 1: Create ResumeAgent class extending BaseAgent (AC: #1, #2, #3, #5, #6)
  - [x]1.1: Create `backend/app/agents/pro/__init__.py`
  - [x]1.2: Create `backend/app/agents/pro/resume_agent.py` with `ResumeAgent(BaseAgent)` class
  - [x]1.3: Set `agent_type = "resume"` matching `AgentType.RESUME` enum
  - [x]1.4: Implement `execute(self, user_id, task_data)` method:
    - Load user context via `get_user_context(user_id)`
    - Load job details from DB using `task_data["job_id"]`
    - Extract master resume structured data from user's Profile
    - Call `_analyze_job(job)` to extract requirements
    - Call `_tailor_resume(profile, job_analysis)` with LLM
    - Call `_calculate_keyword_gaps(job, tailored)` for gap analysis
    - Return `AgentOutput` with action, rationale, confidence, data
  - [x]1.5: Implement `_analyze_job(job_row)` helper — extracts title, skills, qualifications from job description
  - [x]1.6: Implement `_tailor_resume(profile, job_analysis)` — calls OpenAI gpt-4o-mini with structured output (Pydantic model for tailored resume sections)
  - [x]1.7: Implement `_calculate_keyword_gaps(job, tailored)` — compares job keywords vs tailored content
  - [x]1.8: Implement `_store_document(session, user_id, job_id, tailored_content)` — creates Document row with type=RESUME, version auto-increment

- [x] Task 2: Wire Celery task to use ResumeAgent (AC: #7)
  - [x]2.1: Update `backend/app/worker/tasks.py` — replace `agent_resume` placeholder with actual `ResumeAgent` instantiation and execution (follow `agent_job_scout` pattern exactly)

- [x] Task 3: Write comprehensive tests (AC: #8)
  - [x]3.1: Create `backend/tests/unit/test_agents/test_resume_agent.py`
  - [x]3.2: Test `execute()` happy path — mock LLM, verify Document created, AgentOutput structure correct
  - [x]3.3: Test job analysis extraction
  - [x]3.4: Test keyword gap calculation
  - [x]3.5: Test document version incrementing (second tailoring for same job increments version)
  - [x]3.6: Test brake check integration (agent stops when brake active)
  - [x]3.7: Test LLM failure graceful handling (returns partial output, doesn't crash)
  - [x]3.8: Test hallucination guard — verify system prompt includes "NEVER invent qualifications"

## Dev Notes

### Architecture Compliance

**CRITICAL — Follow these patterns EXACTLY:**

1. **BaseAgent lifecycle:** Override `execute()` only. The `run()` method in BaseAgent handles brake checks, output recording, activity logging, and WebSocket event publishing automatically.
   [Source: backend/app/agents/base.py]

2. **File location:** Architecture specifies `backend/app/agents/pro/resume_agent.py` — the `pro/` subdirectory is for Pro-tier agents (Resume, Apply).
   [Source: _bmad-output/planning-artifacts/architecture.md line 1368]

3. **AgentOutput structure:** Must return `AgentOutput(action, rationale, confidence, alternatives_considered, data, requires_approval)`. The `data` dict should contain `keyword_gaps`, `sections_modified`, `ats_score`, `document_id`.
   [Source: backend/app/agents/base.py — AgentOutput dataclass]

4. **Celery task pattern:** Lazy imports inside `_execute()`, explicit Langfuse trace, `flush_traces()` in finally block. Follow `agent_job_scout` pattern exactly.
   [Source: backend/app/worker/tasks.py lines 55-94]

5. **LLM pattern:** Use `AsyncOpenAI().beta.chat.completions.parse()` with Pydantic response_format. Use `gpt-4o-mini` model (cost-effective, sufficient for resume tailoring). Track costs via `track_llm_cost()`.
   [Source: backend/app/services/resume_parser.py — same pattern]

6. **Orchestrator already routes "resume" → agent_resume task.** No changes needed to orchestrator.py.
   [Source: backend/app/agents/orchestrator.py — TASK_ROUTING dict]

7. **Tier enforcement:** Resume tailoring is a "write" action (creates artifacts). The orchestrator's `dispatch_task()` already checks `AutonomyGate` before dispatching. The agent itself does NOT need to check tiers — that's handled at dispatch level.
   [Source: backend/app/agents/orchestrator.py — dispatch_task(), backend/app/agents/tier_enforcer.py]

8. **NEVER fabricate qualifications.** The LLM system prompt MUST include explicit instructions: "You must ONLY use experience, skills, and qualifications present in the user's master resume. NEVER invent, fabricate, or embellish qualifications." This is a ROADMAP-level requirement with DeepEval testing planned.
   [Source: .planning/ROADMAP.md Phase 5 research adjustments]

### Previous Story Intelligence (4-10)

- 372 unit tests passing (plus 2 pre-existing failures in test_tier_enforcement, 2 pre-existing errors in test_health)
- TestClient cannot be used due to pre-existing ColdEmailRequest model issue in create_app() — test functions directly
- Mock pattern for lazy imports: patch at source module (`app.db.engine.AsyncSessionLocal`), NOT consumer module
- All agents use `get_user_context()` for loading profile/preferences with Redis caching (5-min TTL)

### Technical Requirements

**Pydantic model for LLM structured output:**
```python
class TailoredSection(BaseModel):
    section_name: str  # e.g., "summary", "experience", "skills"
    original_content: str
    tailored_content: str
    changes_made: list[str]  # Brief description of each change

class TailoredResume(BaseModel):
    sections: list[TailoredSection]
    keywords_incorporated: list[str]
    keywords_missing: list[str]
    ats_score: int  # 0-100
    tailoring_rationale: str
```

**System prompt for LLM (CRITICAL — anti-hallucination):**
```
You are a professional resume tailoring assistant. Given a user's master resume data and a target job description, optimize the resume for this specific role.

RULES:
1. You must ONLY use experience, skills, and qualifications present in the user's master resume. NEVER invent, fabricate, or embellish qualifications.
2. Reorder and emphasize existing experience that is most relevant to the target role.
3. Rephrase bullet points to mirror the job description's language and keywords.
4. Add relevant skills from the user's skill set that match the job requirements.
5. Optimize the professional summary to align with the target role.
6. Return an ATS score (0-100) based on keyword match percentage.
```

**Document version incrementing:**
```python
# Query max version for this user+job combo
result = await session.execute(
    text("""
        SELECT COALESCE(MAX(version), 0) + 1
        FROM documents
        WHERE user_id = (SELECT id FROM users WHERE clerk_id = :uid)
        AND job_id = :jid
        AND type = 'resume'
    """),
    {"uid": user_id, "jid": job_id},
)
next_version = result.scalar()
```

### Library/Framework Requirements

**No new dependencies needed.** All packages already installed:
- `openai` — AsyncOpenAI for LLM calls
- `pydantic` — structured output models
- `sqlalchemy` — async DB sessions
- `celery` — task execution

### File Structure Requirements

**Files to CREATE:**
```
backend/app/agents/pro/__init__.py
backend/app/agents/pro/resume_agent.py
backend/tests/unit/test_agents/test_resume_agent.py
```

**Files to MODIFY:**
```
backend/app/worker/tasks.py  # Replace agent_resume placeholder with real implementation
```

**Files to NOT TOUCH:**
```
backend/app/agents/base.py              # BaseAgent is stable
backend/app/agents/orchestrator.py      # Already routes "resume" correctly
backend/app/agents/tier_enforcer.py     # Tier enforcement handled at dispatch
backend/app/agents/brake.py             # Brake check handled by BaseAgent.run()
backend/app/services/resume_parser.py   # Parsing is for onboarding, not tailoring
backend/app/db/models.py                # Document model already exists
```

### Testing Requirements

- **Backend Framework:** Pytest + pytest-asyncio
- **Mocking:** Mock `AsyncSessionLocal`, mock `AsyncOpenAI`, mock `get_user_context`
- **Mock paths:** Patch at source module (e.g., `app.db.engine.AsyncSessionLocal`)
- **Anti-hallucination test:** Verify system prompt contains "NEVER invent" instruction
- **Tests to write:**
  - Happy path: job loaded, LLM returns tailored resume, Document created, AgentOutput correct
  - Job analysis: extracts title, skills, qualifications from job row
  - Keyword gap: identifies missing and matched keywords
  - Version increment: second tailoring for same job gets version=2
  - Brake active: agent raises BrakeActive (handled by BaseAgent.run)
  - LLM failure: returns graceful error output, doesn't crash
  - System prompt: contains anti-hallucination instructions

### References

- [Source: backend/app/agents/base.py] — BaseAgent class, AgentOutput dataclass
- [Source: backend/app/agents/core/job_scout.py] — Reference agent implementation pattern
- [Source: backend/app/agents/orchestrator.py] — TaskRouter, dispatch_task, get_user_context
- [Source: backend/app/worker/tasks.py] — Celery task pattern, agent_resume placeholder
- [Source: backend/app/services/resume_parser.py] — OpenAI structured output pattern
- [Source: backend/app/db/models.py] — Document model, AgentType enum
- [Source: backend/app/observability/langfuse_client.py] — Langfuse trace pattern
- [Source: backend/app/observability/cost_tracker.py] — LLM cost tracking
- [Source: .planning/ROADMAP.md] — Phase 5 requirements, anti-hallucination mandate

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
SIMPLE (score: 7/16, overridden to SIMPLE by user flag)

### Debug Log References
- No issues encountered. All 13 tests passed on first run.

### Completion Notes List
- Created ResumeAgent extending BaseAgent with agent_type="resume"
- Implemented execute() workflow: load context → load job → analyze → LLM tailor → keyword gaps → store document → return AgentOutput
- Used gpt-4o-mini with Pydantic structured output (TailoredResume model)
- Anti-hallucination system prompt with explicit "NEVER invent, fabricate, or embellish" mandate
- Document versioning: auto-increments for same user+job combo
- Wired Celery agent_resume task to instantiate and run ResumeAgent (replaced placeholder)
- 13 comprehensive tests covering all ACs

### Change Log
- 2026-02-01: Created ResumeAgent + Celery wiring + 13 tests

### File List
**Created:**
- `backend/app/agents/pro/__init__.py`
- `backend/app/agents/pro/resume_agent.py`
- `backend/tests/unit/test_agents/test_resume_agent.py`

**Modified:**
- `backend/app/worker/tasks.py` — replaced agent_resume placeholder with ResumeAgent execution
