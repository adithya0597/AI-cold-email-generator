---
phase: 4
plan: 9
subsystem: preference-learning
tags: [swipe-events, pattern-detection, learned-preferences, scoring]
dependency-graph:
  requires: [04-01, 04-04, 04-07]
  provides: [swipe-event-recording, preference-learning-service, learned-preferences-api, learned-preferences-ui]
  affects: [future-scoring-pipeline-integration]
tech-stack:
  added: []
  patterns: [denormalized-event-log, pattern-detection-service, optimistic-cache-updates]
key-files:
  created:
    - backend/app/services/preference_learning.py
    - backend/app/api/v1/learned_preferences.py
    - backend/tests/unit/test_api/test_learned_prefs.py
    - backend/tests/unit/test_api/test_swipe_events.py
    - backend/tests/unit/test_services/test_preference_learning.py
    - frontend/src/services/learnedPreferences.ts
    - frontend/src/components/matches/LearnedPreferenceBanner.tsx
    - frontend/src/components/matches/__tests__/LearnedPreferenceBanner.test.tsx
    - supabase/migrations/00002_swipe_events_learned_preferences.sql
  modified:
    - backend/app/db/models.py
    - backend/app/api/v1/matches.py
    - backend/app/api/v1/router.py
    - frontend/src/types/matches.ts
    - frontend/src/pages/Matches.tsx
    - frontend/src/components/matches/__tests__/Matches.test.tsx
    - frontend/src/components/matches/__tests__/TopPick.test.tsx
decisions:
  - "SwipeEvent is append-only (TimestampMixin only) for immutable audit trail"
  - "LearnedPreference uses SoftDeleteMixin — rejected preferences are soft-deleted"
  - "Pattern detection thresholds: min 3 occurrences, 60%+ dismiss rate, confidence capped at 0.95"
  - "apply_learned_preferences implemented but NOT wired into live scoring pipeline"
  - "Score adjustments: -15 * confidence for dismissed patterns, +10 * (1-confidence) for saved patterns"
metrics:
  duration: ~7 min
  completed: 2026-01-31
---

# Phase 4 Plan 9: Preference Learning from Swipe Behavior Summary

Full-stack preference learning system: SwipeEvent recording on match save/dismiss, pattern detection service with configurable thresholds, learned preferences API (GET + PATCH), and LearnedPreferenceBanner UI component.

## Tasks Completed

| Task | Name | Commit | Key Outcome |
|------|------|--------|-------------|
| 1 | DB Models + Migration | ea44354 | SwipeEvent, LearnedPreference, LearnedPreferenceStatus enum, SQL migration |
| 2 | Swipe Event Recording | 6cce794 | SwipeEvent created in update_match_status with denormalized job attrs |
| 3 | Preference Learning Service | 3858a4f | detect_patterns + apply_learned_preferences, 13 tests |
| 4 | Learned Preferences API | ab3749b | GET + PATCH endpoints, router registration, 6 tests |
| 5 | Frontend Types + Service | f896523 | LearnedPreference type, TanStack Query hooks with optimistic updates |
| 6 | Frontend UI | 9323ac8 | LearnedPreferenceBanner with Accept/Dismiss, 7 tests |

## Test Results

- **Backend:** 22 new tests (3 swipe events + 13 service + 6 API) — all passing
- **Frontend:** 7 new tests + 43 existing — 50 total passing
- **Coverage:** preference_learning.py at 97%, learned_preferences.py at 92%

## Decisions Made

1. **Denormalized SwipeEvent:** Job attributes stored directly on event (no joins for pattern detection)
2. **Conservative thresholds:** 3+ occurrences, 60%+ dismiss rate prevents false positives
3. **Confidence cap at 0.95:** Even 100% dismiss rate capped to prevent absolute exclusion
4. **Score integration deferred:** apply_learned_preferences exists but is NOT called from live pipeline

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added learnedPreferences mock to existing test files**
- **Found during:** Task 6
- **Issue:** Existing Matches.test.tsx and TopPick.test.tsx rendered full Matches page which now imports LearnedPreferenceBanner, causing Clerk useAuth error
- **Fix:** Added `vi.mock('../../../services/learnedPreferences')` to both test files
- **Files modified:** `frontend/src/components/matches/__tests__/Matches.test.tsx`, `frontend/src/components/matches/__tests__/TopPick.test.tsx`
- **Commit:** 9323ac8

## Architecture Notes

- SwipeEvent uses TimestampMixin only (append-only, no soft-delete)
- LearnedPreference uses SoftDeleteMixin + TimestampMixin
- Pattern detection is batch/on-demand, not triggered on every swipe
- detect_patterns is idempotent (safe to call multiple times)
- Frontend banner filters to pending-only preferences via select transform

## Next Phase Readiness

- apply_learned_preferences ready to wire into Job Scout Agent scoring pipeline
- Pattern detection can be called from Celery periodic task or agent orchestrator
- No blockers for downstream integration
