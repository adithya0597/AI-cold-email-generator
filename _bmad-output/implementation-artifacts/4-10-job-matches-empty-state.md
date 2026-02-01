# Story 4.10: Job Matches Empty State

Status: ready-for-dev

## Story

As a **user**,
I want **helpful guidance when no jobs match my criteria**,
so that **I can adjust preferences rather than feel stuck**.

## Acceptance Criteria

1. **AC1 - Empty State Message:** Given I have zero new job matches, when I view the Matches page, then I see a friendly message: "No matches today. Your agent is still searching!" with a search/radar illustration.

2. **AC2 - Actionable Suggestions:** Given the empty state is displayed, when I view it, then I see three specific suggestions: "Try expanding your location preferences", "Consider adding more job titles", "Relax salary requirements temporarily" — each with a lightbulb or tip icon.

3. **AC3 - Adjust Preferences CTA:** Given the empty state is displayed, when I view it, then I see an "Adjust Preferences" button that links to `/preferences`.

4. **AC4 - Existing Tests Preserved:** Given the empty state tests exist in Matches.test.tsx, when the new empty state is implemented, then existing empty state tests continue to pass (data-testid="empty-state", "Adjust Preferences" text must remain).

## Tasks / Subtasks

- [ ] Task 1: Enhance empty state in Matches.tsx (AC: #1, #2, #3, #4)
  - [ ] 1.1: Replace the current empty state block (lines 117-140) with enhanced version that includes: updated message text, three suggestion items with icons, and preserved "Adjust Preferences" Link
  - [ ] 1.2: Ensure data-testid="empty-state" is preserved on the container
  - [ ] 1.3: Add data-testid="empty-suggestions" on the suggestions list

- [ ] Task 2: Update frontend tests (AC: #1, #2, #3, #4)
  - [ ] 2.1: Update existing empty state test in Matches.test.tsx to check for new message text
  - [ ] 2.2: Add test for suggestion items being rendered
  - [ ] 2.3: Verify "Adjust Preferences" link still present

## Dev Notes

### Architecture Compliance

**CRITICAL — Follow these patterns EXACTLY:**

1. **Modify ONLY the empty state block** in `frontend/src/pages/Matches.tsx` (lines 117-140). Do NOT restructure the page or change the loading/error states.
   [Source: frontend/src/pages/Matches.tsx:117-140 — current empty state block]

2. **Preserve data-testid="empty-state"** on the container div — existing tests depend on this.
   [Source: frontend/src/components/matches/__tests__/Matches.test.tsx — empty state test]

3. **Preserve "Adjust Preferences" text and Link to="/preferences"** — existing tests check for this.

4. **No new components needed** — this is a simple inline enhancement to the existing empty state block. Do NOT create a separate EmptyState component for this (the shared EmptyState component exists but is not suitable here due to the specific suggestion list).

5. **Use existing Tailwind patterns** — match the styling of MatchDetail and LearnedPreferenceBanner for consistency.

### Previous Story Intelligence (4-9)

- LearnedPreferenceBanner was integrated above the swipe card. The empty state renders independently (early return before the main content).
- Matches.test.tsx has mocks for useMatches, useTopPick, useUpdateMatchStatus, and useLearnedPreferences. Follow the same mock patterns.

### Technical Requirements

**Enhanced Empty State Layout:**
```
┌─────────────────────────────────────────┐
│          🔍 (search/radar icon)         │
│                                          │
│  No matches today.                       │
│  Your agent is still searching!          │
│                                          │
│  💡 Try expanding your location prefs    │
│  💡 Consider adding more job titles      │
│  💡 Relax salary requirements temporarily│
│                                          │
│  ┌──────────────────────┐               │
│  │  Adjust Preferences  │               │
│  └──────────────────────┘               │
└─────────────────────────────────────────┘
```

### Library/Framework Requirements

**No new dependencies needed.**

### File Structure Requirements

**Files to CREATE:**
```
(none)
```

**Files to MODIFY:**
```
frontend/src/pages/Matches.tsx                               # Enhanced empty state
frontend/src/components/matches/__tests__/Matches.test.tsx   # Updated tests
```

**Files to NOT TOUCH:**
```
frontend/src/components/matches/SwipeCard.tsx
frontend/src/components/matches/MatchDetail.tsx
frontend/src/components/matches/TopPickCard.tsx
frontend/src/components/matches/LearnedPreferenceBanner.tsx
frontend/src/services/matches.ts
```

### Testing Requirements

- **Frontend Framework:** Vitest + React Testing Library
- **Frontend Tests:**
  - Empty state shows "No matches today" message
  - Empty state shows "Your agent is still searching!" text
  - Empty state shows three suggestion items
  - Empty state shows "Adjust Preferences" link
  - data-testid="empty-state" present
  - data-testid="empty-suggestions" present

## Dev Agent Record

### Agent Model Used

### Route Taken

### GSD Subagents Used

### Debug Log References

### Completion Notes List

### Change Log

### File List
