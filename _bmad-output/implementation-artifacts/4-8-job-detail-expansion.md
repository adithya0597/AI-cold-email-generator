# Story 4.8: Job Detail Expansion

Status: ready-for-dev

## Story

As a **user**,
I want **to see full job details without leaving the swipe interface**,
so that **I can make informed decisions quickly**.

## Acceptance Criteria

1. **AC1 - Full Job Description:** Given I tap on a job card (or press Space), when the MatchDetail expands, then I see the **full job description** (no truncation), with proper paragraph formatting and overflow scrolling if content exceeds a reasonable height (max-h-64 with overflow-y-auto).

2. **AC2 - Extended Job Metadata:** Given the MatchDetail is expanded, when I view it, then I see additional job metadata not currently displayed: **employment type** (Full-time, Part-time, Contract, etc.), **posted date** (relative format like "3 days ago"), and **job source** (Indeed, LinkedIn, etc.).

3. **AC3 - H1B Sponsorship Status:** Given the MatchDetail is expanded AND the job has a known `h1b_sponsor_status` (not "unknown"), when I view the detail, then I see a sponsorship badge: "Verified H1B Sponsor" (green) or "Unverified Sponsorship" (amber). If the status is "unknown", no badge is shown.

4. **AC4 - Backend Extended Job Response:** Given the frontend needs expanded job data, when the matches API returns job data (in list, top-pick, and patch responses), then `JobSummary` includes the additional fields: `employment_type`, `h1b_sponsor_status`, `posted_at`, and `source`.

5. **AC5 - Smooth Expand/Collapse Animation:** Given I tap the swipe card or press Space, when the detail section toggles, then it animates smoothly with height transition (existing behavior preserved). The expanded state shows full content with scroll capability.

6. **AC6 - Collapse Back to Card View:** Given the MatchDetail is expanded, when I tap the card again or press Space, then it collapses back to the compact card view with smooth animation (existing behavior — must not regress).

## Tasks / Subtasks

- [ ] Task 1: Extend backend JobSummary schema (AC: #4)
  - [ ] 1.1: Add `employment_type: Optional[str]`, `h1b_sponsor_status: Optional[str]`, `posted_at: Optional[str]`, and `source: Optional[str]` fields to `JobSummary` Pydantic model in `backend/app/api/v1/matches.py`
  - [ ] 1.2: Update `_match_to_response` helper to populate the new fields from the Job ORM object (h1b_sponsor_status should return `.value` string, posted_at should return ISO format string or null)
  - [ ] 1.3: Write backend tests for extended job response fields

- [ ] Task 2: Extend frontend TypeScript types (AC: #4)
  - [ ] 2.1: Add `employment_type: string | null`, `h1b_sponsor_status: string | null`, `posted_at: string | null`, and `source: string | null` fields to `JobSummary` interface in `frontend/src/types/matches.ts`

- [ ] Task 3: Enhance MatchDetail component (AC: #1, #2, #3, #5)
  - [ ] 3.1: Remove the 500-character truncation of `job.description` — show full description
  - [ ] 3.2: Wrap the job description in a scrollable container (`max-h-64 overflow-y-auto`) for long descriptions
  - [ ] 3.3: Add employment type display below description (if non-null): icon + text
  - [ ] 3.4: Add posted date display in relative format (e.g., "Posted 3 days ago") — reuse or create a `formatRelativeDate` helper
  - [ ] 3.5: Add job source display (e.g., "Source: Indeed") below posted date
  - [ ] 3.6: Add H1B sponsorship badge: green for "verified", amber for "unverified", hidden for "unknown"/null

- [ ] Task 4: Write frontend tests (AC: #1, #2, #3, #6)
  - [ ] 4.1: Test MatchDetail shows full description (not truncated)
  - [ ] 4.2: Test MatchDetail shows employment type, posted date, source when available
  - [ ] 4.3: Test MatchDetail hides optional fields when null
  - [ ] 4.4: Test H1B badge renders correctly for "verified" and "unverified"
  - [ ] 4.5: Test H1B badge hidden when status is "unknown" or null

## Dev Notes

### Architecture Compliance

**CRITICAL — Follow these patterns EXACTLY:**

1. **Backend Schema Extension:** Only modify the `JobSummary` Pydantic model and `_match_to_response` helper in `backend/app/api/v1/matches.py`. Do NOT modify `backend/app/db/models.py` — the Job model already has all needed columns (`employment_type`, `h1b_sponsor_status`, `posted_at`, `source`). This is purely a schema/serialization change.
   [Source: backend/app/db/models.py:235-264 — Job model has all fields]

2. **H1B Sponsor Status Enum Values:** The `H1BSponsorStatus` enum has three values: `verified`, `unverified`, `unknown`. In the API response, return the `.value` string. The frontend should only render a badge for "verified" and "unverified" — not "unknown".
   [Source: backend/app/db/models.py:117-120 — H1BSponsorStatus enum]

3. **MatchDetail Component:** Modify the EXISTING `frontend/src/components/matches/MatchDetail.tsx` component. Do NOT create a new component or page. The story is about enhancing inline expansion, not creating a separate detail view.
   [Source: frontend/src/components/matches/MatchDetail.tsx — current 122 lines]

4. **Frontend Types:** Add new optional fields to the EXISTING `JobSummary` interface in `frontend/src/types/matches.ts`. These fields should all be `string | null` since they may not be populated for all jobs.
   [Source: frontend/src/types/matches.ts — JobSummary interface]

5. **No New Files for the Component:** This story modifies existing files. The only new file should be the test file.

6. **Relative Date Formatting:** A `formatRelativeDate` helper already exists in `frontend/src/components/briefing/BriefingCard.tsx:40-52`. However, it's a private function inside that file. For MatchDetail, create a simple inline helper or duplicate it locally (don't refactor BriefingCard — it's stable from story 4-7). Keep it simple.
   [Source: frontend/src/components/briefing/BriefingCard.tsx:40-52]

7. **Scroll Container for Long Descriptions:** Use `max-h-64 overflow-y-auto` on the description paragraph. This gives ~256px of visible text before scrolling — sufficient for most descriptions while keeping the card manageable.

### Previous Story Intelligence (4-7)

**Key learnings from Story 4-7 that MUST be applied:**

1. **`_match_to_response` is the single serialization point:** All match API responses (list, top-pick, patch) go through this helper. Adding fields here automatically propagates to all endpoints — no need to modify each endpoint separately.
   [Source: backend/app/api/v1/matches.py:113-135]

2. **`score` conversion pattern:** The helper converts `Numeric(5,2)` to `int`. For `posted_at`, convert `datetime` to ISO string. For `h1b_sponsor_status`, get `.value` from enum. For `employment_type` and `source`, pass through as string (already Text type in DB).
   [Source: backend/app/api/v1/matches.py:120]

3. **Test pattern:** Backend tests use `SimpleNamespace` mock objects with explicit fields. Frontend tests use mock data objects with typed interfaces. Follow the same patterns.
   [Source: backend/tests/unit/test_api/test_top_pick.py — SimpleNamespace pattern]
   [Source: frontend/src/components/matches/__tests__/TopPick.test.tsx — mock pattern]

4. **data-testid convention:** All interactive/display elements get `data-testid` attributes for testing. MatchDetail already has: `match-detail`, `job-description`, `top-reasons`, `concerns`, `detail-confidence`, `job-link`.
   [Source: frontend/src/components/matches/MatchDetail.tsx — existing testids]

### Technical Requirements

**Backend Changes (matches.py only):**

```python
# Add to JobSummary:
employment_type: Optional[str] = None
h1b_sponsor_status: Optional[str] = None
posted_at: Optional[str] = None
source: Optional[str] = None

# Add to _match_to_response → JobSummary construction:
employment_type=job.employment_type,
h1b_sponsor_status=job.h1b_sponsor_status.value if hasattr(job.h1b_sponsor_status, 'value') else str(job.h1b_sponsor_status) if job.h1b_sponsor_status else None,
posted_at=job.posted_at.isoformat() if isinstance(job.posted_at, datetime) else str(job.posted_at) if job.posted_at else None,
source=job.source if job.source else None,
```

**Frontend MatchDetail Enhancements:**

```
┌─────────────────────────────────────────┐
│  JOB DESCRIPTION                        │
│  ┌─────────────────────────────────┐   │
│  │ Full description text...        │   │  ← max-h-64 overflow-y-auto
│  │ (scrollable if long)            │   │
│  └─────────────────────────────────┘   │
│                                         │
│  📋 Full-time  •  📅 3 days ago  •  🔗 Indeed │  ← metadata row
│                                         │
│  🟢 Verified H1B Sponsor               │  ← conditional badge
│                                         │
│  WHY THIS MATCH?                        │
│  ✅ Strong Python experience            │
│  ✅ Remote friendly                     │
│  ⚠️ Salary slightly below target       │
│  Match confidence: [High]               │
│                                         │
│  ─────────────────────────────────────  │
│  🔗 View Full Posting                   │
└─────────────────────────────────────────┘
```

### Library/Framework Requirements

**No new dependencies needed.**

**Existing dependencies used:**
- `framer-motion` — existing expand/collapse animation (no changes)
- `react-icons/fi` — may use FiBriefcase, FiCalendar, FiExternalLink for metadata icons
- `tailwindcss` — styling

### File Structure Requirements

**Files to CREATE:**
```
frontend/src/components/matches/__tests__/MatchDetail.test.tsx  # MatchDetail tests
backend/tests/unit/test_api/test_job_detail_fields.py          # Backend schema tests
```

**Files to MODIFY:**
```
backend/app/api/v1/matches.py                                  # Extend JobSummary + _match_to_response
frontend/src/types/matches.ts                                   # Add fields to JobSummary interface
frontend/src/components/matches/MatchDetail.tsx                 # Enhanced detail view
```

**Files to NOT TOUCH:**
```
backend/app/db/models.py                                        # Job model already has all fields
frontend/src/components/matches/SwipeCard.tsx                   # Swipe card is stable
frontend/src/components/matches/TopPickCard.tsx                 # Top pick card is stable
frontend/src/pages/Matches.tsx                                  # Page integration unchanged
frontend/src/services/matches.ts                                # Hooks unchanged
```

### Testing Requirements

- **Backend Coverage Target:** >80% line coverage for schema changes
- **Backend Framework:** pytest with FastAPI TestClient, mock database session
- **Backend Tests:**
  - Extended job fields returned in match response (employment_type, h1b_sponsor_status, posted_at, source)
  - Null/missing fields handled gracefully (return null not error)
  - H1B sponsor status returns enum value string, not object
- **Frontend Framework:** Vitest + React Testing Library
- **Frontend Tests:**
  - Full description rendered (no "..." truncation)
  - Employment type, posted date, source rendered when present
  - Optional fields hidden when null
  - H1B "verified" badge renders green
  - H1B "unverified" badge renders amber
  - H1B badge hidden when "unknown" or null
- **Key Mock Strategy:**
  - Backend: Mock async session, return SimpleNamespace Job objects with all new fields
  - Frontend: Render MatchDetail with mock MatchData containing various field combinations

### Project Structure Notes

- This story enhances existing MatchDetail — no new routes, pages, or components
- The backend change is additive (new optional fields) — backward compatible
- Frontend types are additive — existing code consuming JobSummary won't break
- MatchDetail is rendered from Matches page via AnimatePresence — existing wiring untouched

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 4, Story 4.8]
- [Source: _bmad-output/planning-artifacts/architecture.md — Frontend stack, component patterns]
- [Source: backend/app/db/models.py:117-120 — H1BSponsorStatus enum]
- [Source: backend/app/db/models.py:235-264 — Job model with all columns]
- [Source: backend/app/api/v1/matches.py — JobSummary schema, _match_to_response helper]
- [Source: frontend/src/types/matches.ts — JobSummary, MatchData interfaces]
- [Source: frontend/src/components/matches/MatchDetail.tsx — Current detail view (122 lines)]
- [Source: frontend/src/components/matches/SwipeCard.tsx — Swipe card (stable)]
- [Source: frontend/src/pages/Matches.tsx — Matches page integration (stable)]
- [Source: 4-7-top-pick-of-the-day-feature.md — Previous story intelligence]

## Dev Agent Record

### Agent Model Used

### Route Taken

### GSD Subagents Used

### Debug Log References

### Completion Notes List

### Change Log

### File List
