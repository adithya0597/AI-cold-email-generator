# Story 4.5: Match Rationale Generation

Status: ready-for-dev

## Story

As a **user**,
I want **to understand why each job was matched to me**,
so that **I can trust the agent's recommendations**.

## Acceptance Criteria

1. **AC1 - Structured Rationale Generation:** Given a job has been matched and scored by the LLM, when the scoring completes, then the rationale stored with the Match record is a structured JSON string containing: `top_reasons` (array of 3 strings referencing specific profile data), `concerns` (array of 0-3 strings about gaps), and `confidence` (one of "High", "Medium", "Low").

2. **AC2 - Profile-Specific Reasons:** Given the rationale is generated, when the user views it, then the top reasons reference specific parts of their profile (e.g., "Your Python and React skills match 4 of 5 required technologies" or "Your target salary of $180K aligns with the $150K-$200K range").

3. **AC3 - Concerns and Gaps:** Given the job has potential mismatches, when the rationale is generated, then concerns highlight specific gaps (e.g., "Job requires 8+ years experience; your profile shows 5 years" or "Location is onsite in NYC; you prefer remote").

4. **AC4 - Confidence Level:** Given the scoring breakdown, when the rationale is generated, then confidence is derived from the score: High (score >= 75), Medium (score 50-74), Low (score < 50).

5. **AC5 - Heuristic Fallback Rationale:** Given LLM scoring is unavailable, when the heuristic fallback is used, then a structured rationale is still generated from the heuristic breakdown dimensions (title, location, salary, skills, seniority, company_size) — no LLM needed for this path.

6. **AC6 - API Endpoint:** Given a user requests match details, when the API returns match data, then the rationale field contains the structured JSON that the frontend can parse and display as a "Why this match?" section.

7. **AC7 - Backward Compatibility:** Given existing matches have plain-text rationale strings, when the API returns these matches, then the frontend receives a backward-compatible format (the raw string is wrapped in a fallback structure: `{"top_reasons": ["<original rationale>"], "concerns": [], "confidence": "Medium"}`).

8. **AC8 - Test Coverage:** Given the rationale generation is implemented, when tests run, then unit tests cover: structured rationale from LLM, heuristic fallback rationale, confidence level derivation, backward compatibility wrapper, and API response format — with >80% line coverage.

## Tasks / Subtasks

- [x] Task 1: Enhance LLM scoring prompt for structured rationale (AC: #1, #2, #3)
  - [x] 1.1: Update `SCORING_PROMPT` in `job_scoring.py` to request structured rationale with `top_reasons` (3 profile-specific strings), `concerns` (gap strings), and `confidence` (High/Medium/Low)
  - [x] 1.2: Update `_parse_llm_response()` to extract and validate `top_reasons`, `concerns`, `confidence` from LLM JSON response
  - [x] 1.3: Update `ScoringResult` dataclass to include `top_reasons: list[str]`, `concerns: list[str]`, `confidence: str`

- [x] Task 2: Add confidence level derivation (AC: #4)
  - [x] 2.1: Add `_derive_confidence(score: int) -> str` helper function: High (>=75), Medium (50-74), Low (<50)
  - [x] 2.2: Use LLM-provided confidence when available, fall back to score-derived confidence

- [x] Task 3: Build heuristic fallback rationale (AC: #5)
  - [x] 3.1: Add `build_heuristic_rationale(score: int, breakdown: dict, job, preferences, profile) -> dict` function in `job_scoring.py`
  - [x] 3.2: Generate profile-specific reason strings from heuristic breakdown dimensions (e.g., "Title 'Software Engineer' matches your target role" for high title score)
  - [x] 3.3: Generate concern strings from low-scoring dimensions
  - [x] 3.4: Derive confidence from heuristic score

- [x] Task 4: Update Match creation with structured rationale (AC: #1, #6)
  - [x] 4.1: Update `_create_matches()` in `job_scout.py` to store structured JSON rationale string (via `json.dumps()`) in the `rationale` column
  - [x] 4.2: Add `_format_rationale_json(scoring_result: ScoringResult) -> str` helper that serializes the structured rationale

- [x] Task 5: Add backward compatibility wrapper (AC: #7)
  - [x] 5.1: Add `parse_rationale(rationale_str: str) -> dict` utility function in `job_scoring.py` that tries JSON parse, falls back to wrapping plain text
  - [x] 5.2: The wrapper produces `{"top_reasons": ["<original>"], "concerns": [], "confidence": "Medium"}` for non-JSON rationale strings

- [ ] Task 6: Write tests (AC: #8)
  - [ ] 6.1: Test LLM structured rationale: mock LLM returning top_reasons, concerns, confidence — verify ScoringResult fields
  - [ ] 6.2: Test heuristic fallback rationale: verify profile-specific reasons generated from breakdown
  - [ ] 6.3: Test confidence derivation: score 80 → High, score 60 → Medium, score 30 → Low
  - [ ] 6.4: Test backward compatibility: plain text rationale → wrapped JSON structure
  - [ ] 6.5: Test rationale JSON serialization for Match storage
  - [ ] 6.6: Update existing `test_job_scoring.py` tests to account for new ScoringResult fields

## Dev Notes

### Architecture Compliance

**CRITICAL — Follow these patterns EXACTLY:**

1. **Extend, Don't Replace:** This story ENHANCES the existing `job_scoring.py` and `ScoringResult`. Do NOT create new files for rationale — add to the existing scoring service module.
   [Source: backend/app/services/job_scoring.py — existing scoring service]

2. **Match Model — No Schema Changes:** The `Match.rationale` column is `Text` type. Store structured rationale as a JSON string via `json.dumps()`. Do NOT add new columns or modify the DB schema.
   [Source: backend/app/db/models.py:300 — `rationale = Column(Text, nullable=True)`]

3. **LLM Client Pattern:** Continue using `OpenAIClient.generate_json()` with `LLMConfig.FAST_MODEL` (gpt-3.5-turbo). The rationale enhancement is achieved by updating the prompt, not by making additional LLM calls.
   [Source: backend/app/core/llm_clients.py — OpenAIClient class]

4. **Cost Constraint:** The enhanced prompt should NOT significantly increase token count. Target: same ~400-500 input tokens, ~300 output tokens (up from ~200). Estimated cost: ~$0.0007/job (vs current $0.00055). Still well within $6/month budget.
   [Source: _bmad-output/planning-artifacts/architecture.md — LLM cost constraint]

5. **Lazy Imports:** Continue the lazy import pattern for heavy dependencies inside functions.
   [Source: backend/app/services/job_scoring.py:162-164 — lazy imports]

6. **Heuristic Rationale Does NOT Call LLM:** The heuristic fallback rationale must be generated purely from the breakdown data — no LLM call. This ensures zero-cost operation when LLM is disabled or unavailable.

### Previous Story Intelligence (4-4)

**Key learnings from Story 4-4 that MUST be applied:**

1. **ScoringResult is the transport:** All scoring data flows through `ScoringResult`. Add new fields here for rationale data — do NOT create a separate RationaleResult class.
   [Source: backend/app/services/job_scoring.py:23-31 — ScoringResult dataclass]

2. **Defensive LLM parsing:** Always provide defaults for new fields. If LLM doesn't return `top_reasons`, default to `[rationale]` (the simple string). If no `concerns`, default to `[]`. If no `confidence`, derive from score.
   [Source: backend/app/services/job_scoring.py:93-134 — _parse_llm_response()]

3. **Concurrent scoring with Semaphore(5):** LLM calls are already concurrent. The enhanced prompt runs in the same call — no additional concurrency concerns.
   [Source: backend/app/agents/core/job_scout.py:100-129 — asyncio.gather with semaphore]

4. **Code review fix: derived normalization.** Normalization now uses `max_possible = sum(m for _, m in breakdown.values())` instead of magic 1.1.
   [Source: Code review fix #4 — job_scout.py]

5. **Test mocking pattern:** Mock `OpenAIClient.generate_json()` with `AsyncMock` returning structured JSON. Use `SimpleNamespace` for job objects.
   [Source: backend/tests/unit/test_services/test_job_scoring.py — established patterns]

### Technical Requirements

**Enhanced LLM Prompt (updated SCORING_PROMPT):**
```python
# Enhanced prompt requesting structured rationale
# Same input context, but output now includes top_reasons, concerns, confidence
# Target: ~400-500 input tokens, ~300 output tokens
# Cost per call: ~$0.0007 (marginal increase from $0.00055)

SCORING_PROMPT = """Score this job match (0-100) for a candidate.

JOB:
Title: {title}
Company: {company}
Location: {location}
Salary: {salary_range}
Description (first 500 chars): {description_truncated}

CANDIDATE PREFERENCES:
Target roles: {target_titles}
Target locations: {target_locations}
Salary range: {salary_min}-{salary_target}
Seniority: {seniority_levels}
Min company size: {min_company_size}
Skills: {skills}

Respond with JSON only:
{{"score": <0-100>, "rationale": "<1-2 sentences>", "top_reasons": ["<reason referencing candidate profile>", "<reason>", "<reason>"], "concerns": ["<gap or mismatch>"], "confidence": "<High|Medium|Low>", "breakdown": {{"title_match": <n>, "skills_overlap": <n>, "location_match": <n>, "salary_match": <n>, "company_size": <n>, "seniority_match": <n>}}}}"""
```

**Updated ScoringResult Dataclass:**
```python
@dataclass
class ScoringResult:
    score: int                    # 0-100 final score
    rationale: str                # Human-readable 1-2 sentence explanation
    breakdown: dict[str, int]     # Per-dimension scores
    model_used: str               # e.g. "gpt-3.5-turbo"
    used_llm: bool                # True if LLM was used
    top_reasons: list[str]        # NEW: Top 3 profile-specific match reasons
    concerns: list[str]           # NEW: Potential gaps/mismatches
    confidence: str               # NEW: "High", "Medium", or "Low"
```

**Structured Rationale JSON (stored in Match.rationale):**
```json
{
  "summary": "Great match for your Python skills and salary expectations",
  "top_reasons": [
    "Your Python and React skills match 4 of 5 required technologies",
    "Salary range $150K-$200K aligns with your $180K target",
    "Senior role matches your seniority preference"
  ],
  "concerns": [
    "Location is onsite in San Francisco; you prefer remote"
  ],
  "confidence": "High"
}
```

**Heuristic Fallback Rationale (no LLM):**
```python
def build_heuristic_rationale(score, breakdown, job, preferences, profile):
    """Generate structured rationale from heuristic breakdown.

    Maps each scoring dimension to a human-readable reason or concern.
    """
    # High-scoring dimensions → top_reasons
    # Low-scoring dimensions → concerns
    # Confidence derived from score
```

### Library/Framework Requirements

**No new dependencies needed:**
- `json` — stdlib, used for rationale serialization (already imported)
- All other dependencies already present from story 4-4

### File Structure Requirements

**Files to CREATE:**
```
(none — all changes in existing files)
```

**Files to MODIFY:**
```
backend/app/services/job_scoring.py              # Enhanced prompt, ScoringResult fields, rationale helpers
backend/app/agents/core/job_scout.py             # Update _create_matches to store structured rationale JSON
backend/tests/unit/test_services/test_job_scoring.py  # New tests for rationale
backend/tests/unit/test_agents/test_job_scout.py      # Update match creation tests
```

**Files to NOT TOUCH:**
```
backend/app/db/models.py                   # Match model already has Text rationale column
backend/app/core/llm_clients.py            # LLM client is stable
backend/app/core/llm_config.py             # No config changes needed
backend/app/config.py                      # No new settings needed
backend/app/observability/cost_tracker.py   # Cost tracker is stable
backend/app/services/job_sources/*.py       # Job sources are stable
frontend/*                                  # No frontend in this story
```

### Testing Requirements

- **Coverage Target:** >80% line, >70% branch for modified files
- **Framework:** pytest with pytest-asyncio
- **Mock Strategy:**
  - Mock `OpenAIClient.generate_json()` returning enhanced JSON with top_reasons, concerns, confidence
  - Use existing `SimpleNamespace` mock job pattern
  - Do NOT make real API calls
- **Key Test Scenarios:**
  - LLM returns full structured rationale → verify ScoringResult.top_reasons, concerns, confidence
  - LLM returns partial rationale (missing concerns) → verify defaults applied
  - LLM fails → verify heuristic rationale generated from breakdown
  - Confidence derivation: score 80→High, 60→Medium, 30→Low
  - Backward compatibility: plain text rationale → wrapped JSON
  - Match creation stores JSON string in rationale column
  - Existing scoring tests still pass with new ScoringResult fields

### Project Structure Notes

- All rationale logic goes in `backend/app/services/job_scoring.py` — no new files
- `build_heuristic_rationale()` is a module-level function, not a class method
- `parse_rationale()` utility is also module-level for reuse by API layer
- JSON rationale is stored as a string in `Match.rationale` (Text column)

### References

- [Source: _bmad-output/planning-artifacts/epics.md - Epic 4, Story 4.5 (lines 1527-1543)]
- [Source: _bmad-output/planning-artifacts/architecture.md - LLM cost constraint (<$6/user/month)]
- [Source: backend/app/services/job_scoring.py - Existing scoring service with ScoringResult]
- [Source: backend/app/services/job_scoring.py:34-60 - Current SCORING_PROMPT]
- [Source: backend/app/services/job_scoring.py:93-134 - _parse_llm_response() defensive parsing]
- [Source: backend/app/agents/core/job_scout.py:516-568 - _create_matches() storing rationale]
- [Source: backend/app/db/models.py:289-309 - Match model (rationale Text column)]
- [Source: backend/app/db/models.py:56-60 - MatchStatus enum]
- [Source: 4-4-ai-job-matching-algorithm.md - Code review learnings, ScoringResult patterns]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### Change Log

### File List
