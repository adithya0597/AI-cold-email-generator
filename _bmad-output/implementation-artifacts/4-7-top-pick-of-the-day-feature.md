# Story 4.7: Top Pick of the Day Feature

Status: review

## Story

As a **user**,
I want **my single best match highlighted as "Top Pick"**,
so that **I don't miss the most promising opportunity**.

## Acceptance Criteria

1. **AC1 - Top Pick Display on Matches Page:** Given I have unreviewed ("new") job matches, when I view the matches page, then the highest-scoring match is featured above the swipe stack as "Top Pick of the Day" with enhanced styling (star badge, gradient border, special card treatment).

2. **AC2 - Extended Rationale on Top Pick:** Given the top pick card is displayed, when I view it, then it shows an extended rationale section: "Here's why this is your #1 match today" with the full `summary`, `top_reasons`, and `confidence` from the structured rationale.

3. **AC3 - One Top Pick Per Day Logic:** Given the backend identifies the top pick, when it returns the top pick via API, then only one match is returned per calendar day (UTC). If a user dismisses or saves the current top pick via swipe, the next highest-scoring "new" match becomes the top pick on the next API call.

4. **AC4 - Top Pick API Endpoint:** Given the frontend needs the top pick, when it calls `GET /api/v1/matches/top-pick`, then it receives the single highest-scoring "new" match for the current user (including joined Job data and parsed rationale), or a 204 No Content if no "new" matches exist.

5. **AC5 - Top Pick in Briefing Card:** Given a briefing is displayed on the dashboard, when the user has a top pick available, then the BriefingCard shows a "Top Pick" highlight in the New Matches section with the top match's title, company, score, and a "Review Now" link to `/matches`.

6. **AC6 - Top Pick Empty State:** Given I have no unreviewed matches, when the top pick API returns 204, then the Matches page does not display the top pick section (graceful absence, no error).

## Tasks / Subtasks

- [x] Task 1: Create backend top-pick endpoint (AC: #3, #4)
  - [x] 1.1: Add `GET /api/v1/matches/top-pick` endpoint in `backend/app/api/v1/matches.py` — returns the single highest-scoring "new" match for the authenticated user with joined Job data and parsed rationale, or 204 No Content if none exist
  - [x] 1.2: Add `TopPickResponse` Pydantic schema (reuses existing `MatchResponse` structure)
  - [x] 1.3: Write backend tests for top-pick endpoint (match found, no matches 204, dismissed match excluded)

- [x] Task 2: Create TopPickCard frontend component (AC: #1, #2)
  - [x] 2.1: Create `frontend/src/components/matches/TopPickCard.tsx` — featured card with star badge, gradient border (indigo-to-purple), enhanced sizing, shows job title, company, location, salary, score as large badge, and extended rationale ("Here's why this is your #1 match today") with `summary` and `top_reasons`
  - [x] 2.2: Add action buttons on the top pick card: "Save" (right arrow icon, green), "Dismiss" (X icon, red), and "View Details" (expands inline)

- [x] Task 3: Create top-pick service hook (AC: #4)
  - [x] 3.1: Add `useTopPick()` TanStack Query hook in `frontend/src/services/matches.ts` — calls `GET /api/v1/matches/top-pick`, handles 204 as null, uses query key `matchKeys.topPick()`
  - [x] 3.2: Add query key `topPick` to `matchKeys` factory
  - [x] 3.3: Invalidate top-pick query when `useUpdateMatchStatus` mutation settles (so dismissing/saving top pick fetches next one)

- [x] Task 4: Integrate top pick into Matches page (AC: #1, #6)
  - [x] 4.1: Update `frontend/src/pages/Matches.tsx` — add TopPickCard above the swipe stack when `useTopPick()` returns data; hide section when null/loading
  - [x] 4.2: Wire TopPickCard save/dismiss actions to `useUpdateMatchStatus` mutation
  - [x] 4.3: Ensure that when top pick is saved/dismissed, it doesn't appear again in the swipe stack below (it should already be removed by optimistic cache update)

- [x] Task 5: Add top pick highlight to BriefingCard (AC: #5)
  - [x] 5.1: Update `frontend/src/components/briefing/BriefingCard.tsx` — add a "Top Pick" banner at the top of the New Matches section if a top-pick match exists (identified as the first match with the highest score in `content.new_matches`)
  - [x] 5.2: Add "Review Now →" link to `/matches` on the top pick item

- [x] Task 6: Write frontend tests (AC: #1, #2, #5, #6)
  - [x] 6.1: Test TopPickCard renders job data, star badge, extended rationale
  - [x] 6.2: Test Matches page shows top pick section when data present
  - [x] 6.3: Test Matches page hides top pick section when no top pick
  - [x] 6.4: Test BriefingCard top pick highlight renders correctly

## Dev Notes

### Architecture Compliance

**CRITICAL — Follow these patterns EXACTLY:**

1. **Backend API Pattern:** Add the new endpoint to the EXISTING `backend/app/api/v1/matches.py` router. Use `Depends(ensure_user_exists)` (already defined in matches.py). Return `MatchResponse` for the top pick (same schema as list items). Return 204 with `Response(status_code=204)` when no matches — do NOT return an empty object.
   [Source: backend/app/api/v1/matches.py — established pattern with ensure_user_exists]

2. **Top Pick Selection Logic — KEEP IT SIMPLE:** The "top pick" is simply `SELECT * FROM matches WHERE user_id=X AND status='new' ORDER BY score DESC LIMIT 1` with joined Job data. No new DB columns, no caching, no daily tracking table. The "one per day" AC means there's only one top pick shown at any time — when it's dismissed, the next highest becomes the new top pick. This is stateless and query-driven.

3. **Frontend Feature Organization:** New component goes in `frontend/src/components/matches/TopPickCard.tsx`. Reuse existing types from `frontend/src/types/matches.ts` — the `MatchData` interface already has everything needed.
   [Source: frontend/src/components/matches/ — feature-based organization]

4. **TanStack Query Pattern:** Add `useTopPick()` hook to the existing `frontend/src/services/matches.ts`. Follow the same pattern as `useMatches()` — use `useApiClient()`, typed response, query key factory.
   [Source: frontend/src/services/matches.ts — established hook pattern]

5. **Styling:** Use Tailwind utility classes. Top pick card should use `bg-gradient-to-r from-indigo-50 to-purple-50 border-2 border-indigo-200` for the featured treatment. Star badge uses FiStar from react-icons/fi (already imported in BriefingCard).
   [Source: frontend/src/components/briefing/BriefingCard.tsx — FiStar import exists]

6. **No Schema Changes:** Do NOT modify `backend/app/db/models.py`. The Match model already has `score` and `status` which are sufficient for top-pick selection.
   [Source: backend/app/db/models.py:289-309 — Match model is stable]

7. **Briefing Integration — MINIMAL:** The BriefingCard already renders `content.new_matches`. Simply identify the highest-scored match in that array and render it with enhanced styling. Do NOT modify the briefing generation pipeline or Briefing model. This is a frontend-only presentation change.
   [Source: frontend/src/components/briefing/BriefingCard.tsx:302-329 — New Matches section]

### Previous Story Intelligence (4-6)

**Key learnings from Story 4-6 that MUST be applied:**

1. **Optimistic cache update removes items from array:** When `useUpdateMatchStatus` fires, the match is optimistically removed from the `matchKeys.list('new')` cache. The top-pick query should also be invalidated via `onSettled` so it refetches the next best match. The `matchKeys.all` invalidation already handles this since `topPick` key should be under the `matches` namespace.
   [Source: frontend/src/services/matches.ts:98-101 — onSettled invalidates matchKeys.all]

2. **Score is already integer in API response:** The `_match_to_response` helper converts `Numeric(5,2)` to `int`. TopPickCard can use `match.score` directly as a percentage.
   [Source: backend/app/api/v1/matches.py:120 — score conversion]

3. **`parse_rationale()` usage:** The top-pick endpoint should use the same `_match_to_response` helper (already in matches.py) for consistent response format.
   [Source: backend/app/api/v1/matches.py:113-135 — _match_to_response helper]

4. **currentIndex was removed in code review:** The Matches page now shows `matches[0]` and relies on optimistic array removal. Top pick card is a separate component above the stack — it should NOT affect the swipe stack's state or index.
   [Source: frontend/src/pages/Matches.tsx — currentIndex removed, uses matches[0]]

5. **framer-motion is installed:** Can use motion animations for the top pick card entrance.
   [Source: frontend/package.json — framer-motion ^11.x already installed]

### Technical Requirements

**Backend Top-Pick Endpoint Design:**

```
GET /api/v1/matches/top-pick
→ Returns single MatchResponse (same schema as list items)
→ 204 No Content if no "new" matches exist

Query: SELECT * FROM matches
  WHERE user_id = :user_id AND status = 'new'
  ORDER BY score DESC
  LIMIT 1
  (with selectinload(Match.job))
```

**IMPORTANT ROUTE ORDER:** The `/top-pick` route MUST be registered BEFORE the `/{match_id}` route in the router, otherwise FastAPI will try to match "top-pick" as a match_id UUID and return 422. Add it above the existing PATCH route.

**Frontend TopPickCard Component:**
- Star badge (⭐) with "Top Pick" label
- Gradient border: `border-2 border-indigo-300 bg-gradient-to-r from-indigo-50 to-purple-50`
- Larger card than SwipeCard: `max-w-lg` instead of `max-w-md`
- Extended rationale: Shows `rationale.summary` as a quote block, `rationale.top_reasons` as bullet list
- Action buttons: Save (green), Dismiss (red) — same mutation as swipe actions

### Library/Framework Requirements

**No new dependencies needed.**

**Existing dependencies used:**
- `framer-motion` — entrance animation for top pick card
- `@tanstack/react-query` — data fetching hook
- `react-icons/fi` — FiStar for star badge
- `react-router-dom` — Link for "Review Now" in briefing
- `tailwindcss` — styling

### File Structure Requirements

**Files to CREATE:**
```
frontend/src/components/matches/TopPickCard.tsx         # Featured top pick card
frontend/src/components/matches/__tests__/TopPick.test.tsx  # Frontend tests
backend/tests/unit/test_api/test_top_pick.py            # Backend tests
```

**Files to MODIFY:**
```
backend/app/api/v1/matches.py                           # Add GET /top-pick endpoint
frontend/src/services/matches.ts                        # Add useTopPick() hook + query key
frontend/src/pages/Matches.tsx                          # Integrate TopPickCard above swipe stack
frontend/src/components/briefing/BriefingCard.tsx        # Add top pick highlight in New Matches
```

**Files to NOT TOUCH:**
```
backend/app/db/models.py                                # No schema changes needed
backend/app/services/job_scoring.py                     # Scoring service is stable
frontend/src/types/matches.ts                           # MatchData type already sufficient
frontend/src/components/matches/SwipeCard.tsx            # Swipe card is stable
frontend/src/components/matches/MatchDetail.tsx          # Match detail is stable
```

### Testing Requirements

- **Backend Coverage Target:** >80% line coverage for the new top-pick endpoint
- **Backend Framework:** pytest with FastAPI TestClient, mock database session
- **Backend Tests:**
  - Top pick returns highest-scoring "new" match with full response format
  - Top pick returns 204 when no "new" matches exist
  - Top pick excludes saved/dismissed matches
- **Frontend Framework:** Vitest + React Testing Library
- **Frontend Tests:**
  - TopPickCard renders job data, star badge, extended rationale
  - Matches page shows top pick section when data exists
  - Matches page hides top pick section when no top pick (204)
  - BriefingCard renders top pick highlight for highest-scored match
- **Key Mock Strategy:**
  - Backend: Mock async session, return SimpleNamespace Match/Job objects (same pattern as test_matches.py)
  - Frontend: Mock useTopPick hook, mock useUpdateMatchStatus

### Project Structure Notes

- Top-pick endpoint lives in existing matches.py router — no new router file needed
- TopPickCard is a separate component, not a variant of SwipeCard — different layout and purpose
- The briefing integration is purely frontend presentation — identify highest score in existing data
- Route order in matches.py is critical: `/top-pick` before `/{match_id}`

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 4, Story 4.7]
- [Source: _bmad-output/planning-artifacts/architecture.md — Frontend stack, component patterns]
- [Source: backend/app/db/models.py:56-61 — MatchStatus enum]
- [Source: backend/app/db/models.py:289-309 — Match model (no changes)]
- [Source: backend/app/api/v1/matches.py — GET/PATCH endpoints, ensure_user_exists, _match_to_response]
- [Source: frontend/src/services/matches.ts — matchKeys factory, useMatches, useUpdateMatchStatus]
- [Source: frontend/src/pages/Matches.tsx — Matches page structure (post code-review fix)]
- [Source: frontend/src/components/briefing/BriefingCard.tsx — New Matches section, FiStar import]
- [Source: frontend/src/types/matches.ts — MatchData, MatchListResponse interfaces]
- [Source: 4-6-swipe-card-interface.md — Code review learnings, optimistic cache pattern]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Route Taken

MODERATE (score: 6/16)

### GSD Subagents Used

gsd-executor x1

### Debug Log References

- 1 auto-fixed deviation: Updated existing Matches.test.tsx mock to include useTopPick after import was added to Matches.tsx

### Completion Notes List

- Added GET /api/v1/matches/top-pick backend endpoint — returns highest-scoring "new" match or 204
- Created TopPickCard component with gradient border, star badge, extended rationale display
- Added useTopPick() TanStack Query hook with 204 handling via validateStatus
- Integrated TopPickCard above swipe stack in Matches page (conditional render)
- Added top pick highlight in BriefingCard New Matches section with star badge and "Review Now" link
- 3 backend tests, 9 frontend tests (28 total frontend matches tests passing)

### Change Log

- 2026-01-31: Implementation via MODERATE route with single gsd-executor

### File List

**Created:**
- `frontend/src/components/matches/TopPickCard.tsx` — Featured top pick card with star badge
- `frontend/src/components/matches/__tests__/TopPick.test.tsx` — 9 frontend tests
- `backend/tests/unit/test_api/test_top_pick.py` — 3 backend tests

**Modified:**
- `backend/app/api/v1/matches.py` — Added GET /top-pick endpoint
- `frontend/src/services/matches.ts` — Added useTopPick() hook + matchKeys.topPick
- `frontend/src/pages/Matches.tsx` — Integrated TopPickCard above swipe stack
- `frontend/src/components/briefing/BriefingCard.tsx` — Added top pick highlight in New Matches
- `frontend/src/components/matches/__tests__/Matches.test.tsx` — Updated mock for useTopPick
