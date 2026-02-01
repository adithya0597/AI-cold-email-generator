# Story 5.9: One-Tap Approval from Briefing

Status: review

## Story

As a **user**,
I want **to approve applications directly from my daily briefing**,
so that **I don't need to navigate to a separate queue**.

## Acceptance Criteria

1. **AC1 - Approval Cards in Briefing:** Given pending approval items exist, when a briefing is generated, then the briefing content includes a `pending_approval_cards` section with job title, company, submission method, and approval_item_id for each pending item.

2. **AC2 - Approve via Existing Endpoint:** Given an approval card in the briefing, when the user calls `POST /api/v1/applications/queue/{item_id}/approve`, then the application is approved (reuses 5-8 endpoint).

3. **AC3 - Briefing Includes Approval Count:** Given pending items exist, when the briefing metrics are generated, then `pending_approvals` reflects the actual count (already implemented — verify).

4. **AC4 - Tests:** Given the briefing includes approval cards, when unit tests run, then coverage exists for approval card inclusion, empty state (no approvals), and card data structure.

## Tasks / Subtasks

- [x] Task 1: Add pending approval cards to briefing generator (AC: #1, #3)
  - [x]1.1: Create `_get_pending_approval_cards()` in generator.py that fetches pending items with job details from payload
  - [x]1.2: Include `pending_approval_cards` in the raw_data passed to LLM and in no-LLM fallback
  - [x]1.3: Update `_build_no_llm_briefing()` to include the cards section

- [x] Task 2: Write tests (AC: #4)
  - [x]2.1: Create `backend/tests/unit/test_agents/test_briefing_approval_cards.py`
  - [x]2.2: Test `_get_pending_approval_cards()` returns structured card data
  - [x]2.3: Test no-LLM briefing includes `pending_approval_cards`
  - [x]2.4: Test empty approval cards when no pending items

## Dev Notes

### Architecture Compliance

**CRITICAL — Follow these patterns EXACTLY:**

1. **This story enhances the briefing generator**, not the approval queue endpoints. The approve endpoint from 5-8 is reused as-is.

2. **Add a new data-gathering function** `_get_pending_approval_cards()` that fetches the actual approval items (not just count). Follow the `_get_pending_approval_count()` pattern but return structured data.

3. **The no-LLM fallback** (`_build_no_llm_briefing`) must also include the cards so they work without OpenAI.

4. **DO NOT modify the approval queue endpoints.** They already support one-tap approve.

5. **Card structure**: `{"item_id": str, "job_title": str, "company": str, "submission_method": str, "rationale": str}`

### Previous Story Intelligence (5-8)

- 10 tests passing for approval queue endpoints
- Approval items have payload JSONB with job_id, job_title, company, submission_method
- POST /applications/queue/{id}/approve works for one-tap

### Library/Framework Requirements

**No new dependencies needed.**

### File Structure Requirements

**Files to CREATE:**
```
backend/tests/unit/test_agents/test_briefing_approval_cards.py
```

**Files to MODIFY:**
```
backend/app/agents/briefing/generator.py    # Add _get_pending_approval_cards, update briefing content
```

**Files to NOT TOUCH:**
```
backend/app/api/v1/applications.py    # Already has approve endpoint
backend/app/api/v1/briefings.py       # No changes needed
```

### Testing Requirements

- **Backend Framework:** Pytest + pytest-asyncio
- **Tests to write:**
  - _get_pending_approval_cards returns card data
  - No-LLM briefing includes pending_approval_cards
  - Empty cards when no pending items

### References

- [Source: backend/app/agents/briefing/generator.py] — Briefing generator, data gathering
- [Source: backend/app/api/v1/applications.py] — Approve endpoint (reused)

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
SIMPLE (score: 1/16)

### Debug Log References
- No issues encountered. All 6 tests passed on first run.

### Completion Notes List
- Added `_get_pending_approval_cards()` to briefing generator — fetches pending items with structured card data
- Updated `generate_full_briefing()` to gather cards in parallel with other data
- Updated `_build_no_llm_briefing()` to include `pending_approval_cards` section
- Card structure: item_id, job_title, company, submission_method, rationale
- 6 tests covering card data, empty state, error fallback, no-LLM inclusion

### Change Log
- 2026-02-01: Added approval cards to briefing generator + 6 tests

### File List
**Created:**
- `backend/tests/unit/test_agents/test_briefing_approval_cards.py` — 6 tests

**Modified:**
- `backend/app/agents/briefing/generator.py` — Added _get_pending_approval_cards, updated briefing content
