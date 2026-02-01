# Story 4.6: Swipe Card Interface

Status: ready-for-dev

## Story

As a **user**,
I want **to review job matches with a Tinder-style swipe interface**,
so that **I can quickly process many jobs with minimal effort**.

## Acceptance Criteria

1. **AC1 - Match Card Display:** Given I am viewing my job matches, when I see a job card, then the card displays: company name, job title, location (with remote badge if applicable), salary range (or "Not specified"), match score as a percentage badge, and the confidence level (High/Medium/Low).

2. **AC2 - Swipe Right to Save:** Given I see a job card, when I swipe right (or press → key), then the match status is updated to "saved" via API, a brief "Saved!" animation plays, and the next card is shown.

3. **AC3 - Swipe Left to Dismiss:** Given I see a job card, when I swipe left (or press ← key), then the match status is updated to "dismissed" via API, a brief "Dismissed" animation plays, and the next card is shown.

4. **AC4 - Tap to Expand Details:** Given I see a job card, when I tap/click the card (or press Space), then the card expands to show: full job description (first 500 chars), "Why this match?" section with top_reasons and concerns from the structured rationale, and a link to the full job posting.

5. **AC5 - Touch and Drag Gestures:** Given I am on a mobile device, when I touch-drag a card horizontally, then the card follows my finger with rotation tilt, the background shows a green "Save" indicator on right drag and red "Dismiss" on left drag, and releasing past a threshold triggers the action.

6. **AC6 - Keyboard Shortcuts:** Given I am on desktop, when I press arrow keys or Space, then → saves, ← dismisses, Space toggles detail expansion, and a small keyboard shortcut hint is visible.

7. **AC7 - Empty State:** Given I have no unreviewed matches (all saved or dismissed), when I view the matches page, then I see an empty state message: "All caught up! Your agent is finding more matches." with a link to adjust preferences.

8. **AC8 - Backend Matches API:** Given the frontend needs match data, when it requests GET /api/v1/matches, then it receives paginated matches with status "new" (unreviewed) including the joined Job data and parsed rationale, sorted by score descending. PATCH /api/v1/matches/{id} updates the match status.

## Tasks / Subtasks

- [x] Task 1: Create backend matches API endpoints (AC: #8)
  - [x] 1.1: Create `backend/app/api/v1/matches.py` with GET /matches (paginated, filterable by status, joins Job data, parses rationale JSON) and PATCH /matches/{id} (updates status)
  - [x] 1.2: Add Pydantic response schemas for MatchResponse (with nested JobSummary and parsed rationale)
  - [x] 1.3: Register matches router in `backend/app/api/v1/router.py`
  - [x] 1.4: Write backend tests for both endpoints

- [x] Task 2: Install framer-motion and create SwipeCard component (AC: #1, #5)
  - [x] 2.1: Install `framer-motion` in frontend
  - [x] 2.2: Create `frontend/src/components/matches/SwipeCard.tsx` — card with drag gesture support via framer-motion's `useMotionValue`, `useTransform`, and `useDragControls`; shows company, title, location, salary, score badge, confidence badge
  - [x] 2.3: Add swipe threshold detection — drag past ±150px triggers save/dismiss; visual indicators (green/red overlays with opacity tied to drag distance)
  - [x] 2.4: Add tilt rotation transform tied to horizontal drag offset

- [x] Task 3: Create MatchDetail expanded view (AC: #4)
  - [x] 3.1: Create `frontend/src/components/matches/MatchDetail.tsx` — expanded card showing full description (first 500 chars), "Why this match?" section rendering top_reasons as bullet points, concerns as warning items, confidence badge, and external job link
  - [x] 3.2: Add expand/collapse animation via framer-motion `AnimatePresence` + `motion.div` with layout animation

- [x] Task 4: Create matches API service and hooks (AC: #8)
  - [x] 4.1: Create `frontend/src/services/matches.ts` with TanStack Query hooks: `useMatches(status)` for fetching paginated matches, `useUpdateMatchStatus()` mutation that optimistically updates the cache
  - [x] 4.2: Define TypeScript types in `frontend/src/types/matches.ts`

- [x] Task 5: Create MatchesPage with swipe stack (AC: #1, #2, #3, #6, #7)
  - [x] 5.1: Create `frontend/src/pages/Matches.tsx` — page component that renders a stack of SwipeCard components, handles swipe callbacks (save/dismiss), manages current card index
  - [x] 5.2: Add keyboard event listeners (→ save, ← dismiss, Space toggle details)
  - [x] 5.3: Add keyboard shortcut hint overlay
  - [x] 5.4: Add empty state when no unreviewed matches remain (using shared EmptyState component pattern)
  - [x] 5.5: Add route `/matches` in App.tsx (protected + onboarding-guarded)

- [x] Task 6: Write frontend tests (AC: #1-#7)
  - [x] 6.1: Test SwipeCard renders job data correctly
  - [x] 6.2: Test keyboard shortcuts trigger correct actions
  - [x] 6.3: Test empty state displays when no matches
  - [x] 6.4: Test MatchDetail expansion shows rationale fields

## Dev Notes

### Architecture Compliance

**CRITICAL — Follow these patterns EXACTLY:**

1. **Backend API Pattern:** Follow the established router pattern from `briefings.py` and `preferences.py`. Use `Depends(get_current_user)` for auth. Return standard response format: `{"data": [...], "meta": {"pagination": {...}}}`.
   [Source: backend/app/api/v1/briefings.py — established API pattern]

2. **Frontend Feature Organization:** Create components under `frontend/src/components/matches/` following the existing `briefing/`, `preferences/`, `onboarding/` convention. Page goes in `frontend/src/pages/Matches.tsx`.
   [Source: frontend/src/components/ — feature-based organization]

3. **TanStack Query Pattern:** Follow the `briefings.ts` service pattern exactly — query key factory, separate fetch functions, hooks that use `useApiClient()` for authenticated requests.
   [Source: frontend/src/services/briefings.ts — query hook pattern]

4. **Zustand NOT Needed:** Card stack state (current index, expanded state) is local component state. Do NOT create a Zustand store for this — it's ephemeral UI state, not persisted state.

5. **Styling:** Use Tailwind utility classes exclusively. Follow the existing color palette — indigo/blue for primary actions, green for "save", red/rose for "dismiss", amber for warnings. Use the existing `.card` CSS class as base.
   [Source: frontend/src/index.css — .card class, color palette]
   [Source: frontend/tailwind.config.js — custom colors and animations]

6. **TypeScript:** All new files must be `.tsx`/`.ts`. Define interfaces for props and API responses. Follow PascalCase for components, camelCase for hooks/utilities.
   [Source: frontend/src/components/briefing/BriefingCard.tsx — TypeScript component pattern]

7. **Match Model — No Schema Changes:** The Match model already has `status` (MatchStatus enum: new, saved, dismissed, applied), `score`, and `rationale` (Text). The Job model has all display fields. Do NOT modify `models.py`.
   [Source: backend/app/db/models.py:289-309 — Match model]
   [Source: backend/app/db/models.py:235-263 — Job model]
   [Source: backend/app/db/models.py:56-61 — MatchStatus enum]

8. **Rationale Parsing:** Use `parse_rationale()` from `app.services.job_scoring` in the backend API to convert the stored JSON string to a structured dict before returning to frontend.
   [Source: backend/app/services/job_scoring.py:351-388 — parse_rationale()]

### Previous Story Intelligence (4-5)

**Key learnings from Story 4-5 that MUST be applied:**

1. **Structured rationale is JSON in Match.rationale:** The rationale column stores a JSON string with `summary`, `top_reasons` (array), `concerns` (array), `confidence` (High/Medium/Low). Use `parse_rationale()` to safely parse it — handles None, plain text, and valid JSON.
   [Source: backend/app/services/job_scoring.py:351-388]

2. **Score is Numeric(5,2):** The score in Match.score is a decimal (e.g., 85.00). Convert to int for display percentage.
   [Source: backend/app/db/models.py:299]

3. **MatchStatus enum values:** `new`, `saved`, `dismissed`, `applied`. The swipe interface only transitions `new` → `saved` or `new` → `dismissed`.
   [Source: backend/app/db/models.py:56-61]

### Technical Requirements

**framer-motion Integration:**
```bash
cd frontend && npm install framer-motion
```

Key framer-motion APIs to use:
- `motion.div` — animated div element
- `useMotionValue(0)` — tracks drag x position
- `useTransform(x, [-200, 0, 200], [...])` — maps drag to rotation/opacity
- `animate()` — programmatic animations for keyboard-triggered swipes
- `AnimatePresence` — exit animations when card leaves stack
- `onDragEnd` — detect if drag exceeded threshold

**Backend Matches API Design:**

```
GET /api/v1/matches?status=new&page=1&per_page=20
→ Returns matches sorted by score DESC, with joined Job data

PATCH /api/v1/matches/{match_id}
Body: {"status": "saved" | "dismissed"}
→ Updates match status, returns updated match
```

**Response shape:**
```json
{
  "data": [
    {
      "id": "uuid",
      "score": 85,
      "status": "new",
      "rationale": {
        "summary": "Great match...",
        "top_reasons": ["...", "...", "..."],
        "concerns": ["..."],
        "confidence": "High"
      },
      "job": {
        "id": "uuid",
        "title": "Software Engineer",
        "company": "Acme Corp",
        "location": "San Francisco, CA",
        "remote": true,
        "salary_min": 140000,
        "salary_max": 180000,
        "url": "https://...",
        "description": "..."
      },
      "created_at": "ISO 8601"
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 42,
      "total_pages": 3
    }
  }
}
```

### Library/Framework Requirements

**New dependency:**
- `framer-motion` ^11.x — gesture recognition, spring animations, drag controls

**Existing dependencies used:**
- `@tanstack/react-query` — data fetching hooks
- `@heroicons/react` — icons for save/dismiss indicators
- `react-router-dom` — new /matches route
- `tailwindcss` — styling
- `axios` via `useApiClient()` — API calls

### File Structure Requirements

**Files to CREATE:**
```
backend/app/api/v1/matches.py                    # Matches API endpoints
backend/tests/unit/test_api/test_matches.py       # Backend API tests
frontend/src/components/matches/SwipeCard.tsx      # Swipe-enabled job card
frontend/src/components/matches/MatchDetail.tsx    # Expanded card detail view
frontend/src/services/matches.ts                   # TanStack Query hooks + API
frontend/src/types/matches.ts                      # TypeScript type definitions
frontend/src/pages/Matches.tsx                     # Matches page with card stack
frontend/src/components/matches/__tests__/SwipeCard.test.tsx    # Component tests
frontend/src/components/matches/__tests__/Matches.test.tsx      # Page tests
```

**Files to MODIFY:**
```
backend/app/api/v1/router.py                      # Register matches router
frontend/src/App.tsx                               # Add /matches route
frontend/package.json                              # Add framer-motion dependency
```

**Files to NOT TOUCH:**
```
backend/app/db/models.py                           # Match model is stable
backend/app/services/job_scoring.py                # Scoring service is stable
backend/app/agents/core/job_scout.py               # Agent is stable
backend/app/core/llm_clients.py                    # LLM client is stable
frontend/src/components/briefing/*                 # Briefing components are stable
frontend/src/hooks/useOnboarding.ts                # Onboarding store is stable
```

### Testing Requirements

- **Backend Coverage Target:** >80% line coverage for `matches.py`
- **Backend Framework:** pytest with pytest-asyncio, mock database session
- **Frontend Framework:** Vitest + React Testing Library
- **Frontend Tests:**
  - Render tests: SwipeCard displays job data, score badge, confidence
  - Interaction tests: keyboard shortcuts trigger correct callbacks
  - Empty state test: no matches shows empty state message
  - Detail expansion: tap shows rationale content
- **Key Mock Strategy:**
  - Backend: Mock async session, return SimpleNamespace Match/Job objects
  - Frontend: Mock TanStack Query hooks, mock framer-motion drag events via fireEvent

### Project Structure Notes

- Backend matches API follows existing pattern: router in `api/v1/`, registered in `router.py`
- Frontend follows feature-module pattern with co-located components, tests, and types
- No new Zustand stores needed — card stack state is ephemeral
- The `/matches` route is protected (requires auth + completed onboarding)

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 4, Story 4.6]
- [Source: _bmad-output/planning-artifacts/architecture.md — Frontend stack, component patterns]
- [Source: backend/app/db/models.py:56-61 — MatchStatus enum]
- [Source: backend/app/db/models.py:235-263 — Job model fields]
- [Source: backend/app/db/models.py:289-309 — Match model]
- [Source: backend/app/services/job_scoring.py:351-388 — parse_rationale()]
- [Source: backend/app/api/v1/router.py — API router pattern]
- [Source: backend/app/api/v1/briefings.py — Established API endpoint pattern]
- [Source: frontend/src/services/briefings.ts — TanStack Query hook pattern]
- [Source: frontend/src/components/briefing/BriefingCard.tsx — Card component pattern]
- [Source: frontend/src/App.tsx — Route registration pattern]
- [Source: frontend/package.json — Current dependencies (no framer-motion)]
- [Source: 4-5-match-rationale-generation.md — Structured rationale format, parse_rationale()]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### Change Log

### File List

**Created:**

**Modified:**
