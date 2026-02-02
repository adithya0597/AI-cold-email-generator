# Story 6.14: Pipeline Empty State

Status: review

## Story

As a **user**,
I want **encouraging guidance when my pipeline is empty**,
So that **I know how to get started tracking applications**.

## Acceptance Criteria

1. **AC1 - Empty Message:** Given I have zero applications in pipeline, when I view the Pipeline page, then I see: "Your pipeline is empty. Let's fill it up!"
2. **AC2 - Kanban Illustration:** Given the pipeline is empty, when I view the empty state, then I see an illustration of the Kanban flow.
3. **AC3 - CTA Button:** Given the pipeline is empty, when I view the empty state, then I see a "Find your first matches" button linking to job matches.
4. **AC4 - Email Tip:** Given the pipeline is empty, when I view the empty state, then I see a tip: "Connect your email to auto-track existing applications".
5. **AC5 - Import Link:** Given the pipeline is empty, when I view the empty state, then I see a link to import existing applications manually.

## Tasks / Subtasks

- [x] Task 1: Enhance Pipeline empty state (AC: #1-#5)
  - [x] 1.1: Update empty state in `Pipeline.tsx` with encouraging message "Your pipeline is empty. Let's fill it up!"
  - [x] 1.2: Add Kanban flow illustration (visual representation of applied → screening → interview → offer flow)
  - [x] 1.3: Add "Find your first matches" CTA button linking to `/matches`
  - [x] 1.4: Add email connection tip text
  - [x] 1.5: Add "Import applications" link

- [x] Task 2: Update existing empty state test and add new tests (AC: #1-#5)
  - [x] 2.1: Update existing empty state test in `Pipeline.test.tsx` to verify new message
  - [x] 2.2: Add tests for CTA button, email tip, and import link

## Dev Notes

### Architecture Compliance
- Frontend: React components with Tailwind CSS, no external UI libraries
- Modify existing empty state in Pipeline.tsx (lines 90-99)
- Keep existing `data-testid="empty-state"` for backwards compatibility
- This is a frontend-only story — no backend changes

### File Structure Requirements

**Files to CREATE:**
```
(none)
```

**Files to MODIFY:**
```
frontend/src/pages/Pipeline.tsx                            # Enhance empty state
frontend/src/__tests__/Pipeline.test.tsx                   # Update/add empty state tests
```

### Previous Story Intelligence
- Story 6-5 created Pipeline.tsx with basic empty state (emoji + short text)
- Story 6-5 test `Pipeline.test.tsx` has `renders empty state when no applications` test
- Test mocks `useApplications` and `useUpdateApplicationStatus` from `../services/applications`
- Existing test checks for `data-testid="empty-state"` and text "Your pipeline is empty"

### Testing Requirements
- **Frontend Tests:** Update existing empty state test, add tests for CTA link to /matches, email tip text, import link

## Dev Agent Record
### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)
### Route Taken
SIMPLE (score: 1/16)
### GSD Subagents Used
None (direct execution)
### Debug Log References
None
### Completion Notes List
- Enhanced empty state with encouraging message "Your pipeline is empty. Let's fill it up!"
- Added Kanban flow illustration showing Applied → Screening → Interview → Offer stages
- Added "Find your first matches" CTA button linking to /matches
- Added email connection tip text
- Added "Import applications" link to /import
- Updated existing empty state test and added 4 new tests (6 total empty state tests)
- All 14 Pipeline tests passing
### Change Log
- 2026-02-01: Story implemented and moved to review
### File List
**Created:**
(none)

**Modified:**
- frontend/src/pages/Pipeline.tsx
- frontend/src/__tests__/Pipeline.test.tsx
