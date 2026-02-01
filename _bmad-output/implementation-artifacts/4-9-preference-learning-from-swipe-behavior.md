# Story 4.9: Preference Learning from Swipe Behavior

Status: ready-for-dev

## Story

As a **user**,
I want **my agent to learn from my swipe patterns**,
so that **matching improves over time without manual preference updates**.

## Acceptance Criteria

1. **AC1 - Pattern Detection:** Given I have swiped on 5+ jobs where a common attribute is present (e.g., same company dismissed 3+ times), when the system analyzes my swipe history, then it detects the pattern and creates a `LearnedPreference` record with a confidence score.

2. **AC2 - Scoring Integration:** Given learned preferences exist for a user, when the job scoring pipeline runs for new matches, then the score is adjusted: negative patterns (dismissed attributes) reduce the score, positive patterns (saved attributes) increase the score, proportional to confidence.

3. **AC3 - Learned Preferences API:** Given I want to view my learned preferences, when I call `GET /api/v1/preferences/learned`, then I receive a list of all learned preferences with type, value, confidence, occurrences, and status (pending/acknowledged/rejected).

4. **AC4 - Acknowledge/Reject Learned Preference:** Given a learned preference exists with status "pending", when I call `PATCH /api/v1/preferences/learned/{id}` with `{"status": "acknowledged"}` or `{"status": "rejected"}`, then the preference status is updated. Rejected preferences are soft-deleted and that pattern is excluded from future detection.

5. **AC5 - Frontend Learned Preferences Section:** Given learned preferences exist, when I view the Matches page, then I see a "Learned Preferences" banner/section showing pending suggestions (e.g., "I noticed you dismiss jobs at Company X. Add as deal-breaker?") with Accept/Dismiss buttons.

6. **AC6 - Swipe Event Recording:** Given I save or dismiss a match, when the PATCH /matches/{id} endpoint completes, then a `SwipeEvent` is recorded with the match_id, job attributes (company, location, salary, remote, employment_type), and the action taken (saved/dismissed), for later pattern analysis.

## Tasks / Subtasks

- [x] Task 1: Add LearnedPreference and SwipeEvent DB models (AC: #1, #6)
  - [x] 1.1: Add `SwipeEvent` model to `backend/app/db/models.py` with fields: id, user_id, match_id, action (saved/dismissed), job_company, job_location, job_remote, job_salary_min, job_salary_max, job_employment_type, created_at
  - [x] 1.2: Add `LearnedPreference` model to `backend/app/db/models.py` with fields: id, user_id, pattern_type (company/location/salary/remote/employment_type), pattern_value, confidence (0.0-1.0), occurrences (int), status (pending/acknowledged/rejected), created_at, updated_at
  - [x] 1.3: Add `LearnedPreferenceStatus` enum to models.py: pending, acknowledged, rejected
  - [x] 1.4: Create Supabase migration `00002_swipe_events_learned_preferences.sql`
  - [x] 1.5: Add relationships to User model (swipe_events, learned_preferences)

- [x] Task 2: Record swipe events on match status update (AC: #6)
  - [x] 2.1: In `backend/app/api/v1/matches.py`, after successful status update in `update_match_status`, create a `SwipeEvent` capturing the action and denormalized job attributes
  - [x] 2.2: Write backend tests for swipe event recording (verify event created on save, event created on dismiss, job attributes captured correctly)

- [x] Task 3: Implement preference learning service (AC: #1, #2)
  - [x] 3.1: Create `backend/app/services/preference_learning.py` with `detect_patterns(user_id, db)` function
  - [x] 3.2: Implement pattern detection: query SwipeEvent table, group by attribute (company, location, remote, salary range), find attributes with 3+ dismissals and >60% dismiss rate → create LearnedPreference if not already exists
  - [x] 3.3: Implement `apply_learned_preferences(user_id, base_score, job, db)` function that adjusts score based on acknowledged/pending learned preferences (dismissed patterns: -15 per high-confidence match, saved patterns: +10)
  - [x] 3.4: Write unit tests for pattern detection (mock swipe events, verify correct patterns detected)
  - [x] 3.5: Write unit tests for score adjustment (mock learned preferences, verify score changes)

- [x] Task 4: Create learned preferences API endpoints (AC: #3, #4)
  - [x] 4.1: Create `backend/app/api/v1/learned_preferences.py` with router prefix `/preferences/learned`
  - [x] 4.2: Implement `GET /preferences/learned` — returns list of learned preferences for authenticated user
  - [x] 4.3: Implement `PATCH /preferences/learned/{id}` — update status to acknowledged/rejected
  - [x] 4.4: Register router in `backend/app/api/v1/router.py`
  - [x] 4.5: Write backend tests for both endpoints

- [x] Task 5: Add frontend types and API service (AC: #3, #4, #5)
  - [x] 5.1: Add `LearnedPreference` interface to `frontend/src/types/matches.ts`
  - [x] 5.2: Create `frontend/src/services/learnedPreferences.ts` with `useLearnedPreferences()` query hook and `useUpdateLearnedPreference()` mutation hook
  - [x] 5.3: Write service tests

- [x] Task 6: Add Learned Preferences UI to Matches page (AC: #5)
  - [x] 6.1: Create `frontend/src/components/matches/LearnedPreferenceBanner.tsx` — shows pending learned preferences as dismissible suggestion cards
  - [x] 6.2: Integrate banner into `frontend/src/pages/Matches.tsx` above the swipe card area
  - [x] 6.3: Write frontend tests for LearnedPreferenceBanner (renders suggestions, accept button works, dismiss button works, hidden when no pending preferences)

## Dev Notes

### Architecture Compliance

**CRITICAL — Follow these patterns EXACTLY:**

1. **DB Models:** Add `SwipeEvent` and `LearnedPreference` to the EXISTING `backend/app/db/models.py`. Follow the same patterns as `Match` and `UserPreference` — UUID primary keys, `user_id` FK with CASCADE, `SoftDeleteMixin` + `TimestampMixin` on LearnedPreference, `TimestampMixin` only on SwipeEvent (events are append-only, never soft-deleted).
   [Source: backend/app/db/models.py:289-309 — Match model pattern]

2. **SwipeEvent is denormalized:** Store job attributes directly on the event (company, location, salary_min, salary_max, remote, employment_type) rather than joining through match→job. This makes pattern detection queries fast without needing joins and ensures data survives if jobs are updated.
   [Source: Architecture decision — hybrid schema with denormalization for query performance]

3. **Preference Learning Service:** Create as a standalone module `backend/app/services/preference_learning.py` following the same pattern as `job_scoring.py` — pure functions that take `db` session and user context, no class hierarchy. Keep it simple.
   [Source: backend/app/services/job_scoring.py:1-11 — service module pattern]

4. **Learned Preferences API:** Create a NEW router file `backend/app/api/v1/learned_preferences.py` following the same patterns as `matches.py` — Pydantic schemas at top, `ensure_user_exists` dependency, async endpoints. Register in `router.py`.
   [Source: backend/app/api/v1/matches.py — router pattern]
   [Source: backend/app/api/v1/router.py — router registration]

5. **Frontend Hooks:** Follow the exact pattern from `frontend/src/services/matches.ts` — typed API functions, TanStack Query hooks with query keys, optimistic updates where appropriate.
   [Source: frontend/src/services/matches.ts — hook pattern]

6. **Frontend Component:** `LearnedPreferenceBanner` goes in `frontend/src/components/matches/` directory. Keep it simple — a horizontal card with suggestion text + Accept/Dismiss buttons. Use existing Tailwind patterns from SwipeCard/MatchDetail.
   [Source: frontend/src/components/matches/MatchDetail.tsx — component styling pattern]

7. **Scoring Integration (Task 3.3):** The `apply_learned_preferences` function is NOT called from within `job_scoring.py` in this story. It is a separate utility that can be called by the orchestrator or Job Scout agent in future stories. For this story, just implement and test the function. Integration into the live scoring pipeline is a future concern.

8. **Pattern Detection Thresholds:** Use conservative thresholds to avoid false positives:
   - Minimum 3 occurrences of the same attribute value in dismissed matches
   - At least 60% dismiss rate for that attribute (3 dismissed out of 5 total with that attribute)
   - Confidence = dismiss_count / total_count (capped at 0.95)

### Previous Story Intelligence (4-8)

**Key learnings from Story 4-8 that MUST be applied:**

1. **`_match_to_response` is the single serialization point:** Adding swipe event recording should happen AFTER the status update in `update_match_status`, not inside `_match_to_response`.
   [Source: backend/app/api/v1/matches.py:228-257 — update_match_status endpoint]

2. **Test mock pattern:** Backend tests use `SimpleNamespace` mock objects. Frontend tests use typed mock data objects. Follow the same patterns established in test_matches.py, test_top_pick.py, and test_job_detail_fields.py.
   [Source: backend/tests/unit/test_api/test_matches.py — _make_job, _make_match helpers]

3. **data-testid convention:** All interactive/display elements get `data-testid` attributes. Use: `learned-preference-banner`, `learned-pref-{id}`, `accept-pref-{id}`, `dismiss-pref-{id}`.

4. **hasattr guards are unnecessary on ORM models:** The Job ORM model always has all columns. Access them directly, don't use `hasattr` checks.
   [Source: review(4-8) — finding #1 fix]

### Technical Requirements

**Backend — New Models (models.py):**

```python
class LearnedPreferenceStatus(str, enum.Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"

class SwipeEvent(TimestampMixin, Base):
    __tablename__ = "swipe_events"
    id = Column(UUID, primary_key=True, default=uuid4)
    user_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    match_id = Column(UUID, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    action = Column(Text, nullable=False)  # "saved" | "dismissed"
    job_company = Column(Text, nullable=True)
    job_location = Column(Text, nullable=True)
    job_remote = Column(Boolean, nullable=True)
    job_salary_min = Column(Integer, nullable=True)
    job_salary_max = Column(Integer, nullable=True)
    job_employment_type = Column(Text, nullable=True)

class LearnedPreference(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "learned_preferences"
    id = Column(UUID, primary_key=True, default=uuid4)
    user_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    pattern_type = Column(Text, nullable=False)  # "company" | "location" | "remote" | "salary_range" | "employment_type"
    pattern_value = Column(Text, nullable=False)  # e.g. "Acme Corp", "San Francisco", "true", "0-80000"
    confidence = Column(Numeric(3, 2), nullable=False, default=0.0)
    occurrences = Column(Integer, nullable=False, default=0)
    status = Column(Enum(LearnedPreferenceStatus), nullable=False, default=LearnedPreferenceStatus.PENDING)
    # user, swipe_events relationships
```

**Backend — Swipe Event Recording (matches.py):**

```python
# In update_match_status, AFTER db.refresh(match):
swipe_event = SwipeEvent(
    user_id=user.id,
    match_id=match.id,
    action=body.status,
    job_company=match.job.company,
    job_location=match.job.location,
    job_remote=match.job.remote,
    job_salary_min=match.job.salary_min,
    job_salary_max=match.job.salary_max,
    job_employment_type=match.job.employment_type,
)
db.add(swipe_event)
await db.flush()
```

**Backend — Pattern Detection (preference_learning.py):**

```python
async def detect_patterns(user_id: UUID, db: AsyncSession) -> list[LearnedPreference]:
    """Analyze swipe events and detect preference patterns.

    Returns newly created LearnedPreference records.
    """
    # 1. Query all swipe events for user
    # 2. Group by attribute (company, location, etc.)
    # 3. For each attribute value:
    #    - Count total events and dismiss events
    #    - If dismiss_count >= 3 and dismiss_rate >= 0.60:
    #      - Check if LearnedPreference already exists for this pattern
    #      - If not, create one with confidence = dismiss_rate
    # 4. Return new preferences
```

**Frontend — LearnedPreference Type:**

```typescript
export interface LearnedPreference {
  id: string;
  pattern_type: string;
  pattern_value: string;
  confidence: number;
  occurrences: number;
  status: 'pending' | 'acknowledged' | 'rejected';
  created_at: string;
}
```

### Library/Framework Requirements

**No new dependencies needed.**

**Existing dependencies used:**
- `sqlalchemy` — new models, queries
- `pydantic` — new API schemas
- `@tanstack/react-query` — new hooks
- `framer-motion` — banner animation (optional)
- `tailwindcss` — styling

### File Structure Requirements

**Files to CREATE:**
```
backend/app/services/preference_learning.py        # Pattern detection + score adjustment
backend/app/api/v1/learned_preferences.py          # GET + PATCH endpoints
backend/tests/unit/test_api/test_learned_prefs.py  # API endpoint tests
backend/tests/unit/test_services/test_preference_learning.py  # Service tests
frontend/src/services/learnedPreferences.ts        # API hooks
frontend/src/components/matches/LearnedPreferenceBanner.tsx   # UI component
frontend/src/components/matches/__tests__/LearnedPreferenceBanner.test.tsx  # Component tests
supabase/migrations/00002_swipe_events_learned_preferences.sql  # DB migration
```

**Files to MODIFY:**
```
backend/app/db/models.py                           # Add SwipeEvent, LearnedPreference, LearnedPreferenceStatus
backend/app/api/v1/matches.py                      # Add swipe event recording after status update
backend/app/api/v1/router.py                       # Register learned_preferences router
frontend/src/types/matches.ts                      # Add LearnedPreference interface
frontend/src/pages/Matches.tsx                     # Integrate LearnedPreferenceBanner
```

**Files to NOT TOUCH:**
```
backend/app/services/job_scoring.py                # Score integration is future work
backend/app/api/v1/preferences.py                  # Explicit preferences are separate
frontend/src/components/matches/SwipeCard.tsx       # Swipe card is stable
frontend/src/components/matches/MatchDetail.tsx     # Detail view is stable
frontend/src/components/matches/TopPickCard.tsx     # Top pick is stable
```

### Testing Requirements

- **Backend Coverage Target:** >80% line coverage for new code
- **Backend Framework:** pytest with FastAPI TestClient, mock database session
- **Backend Tests:**
  - SwipeEvent created on save action (verify all job attributes captured)
  - SwipeEvent created on dismiss action
  - Pattern detection finds company pattern (3+ dismissals, >60% rate)
  - Pattern detection ignores patterns below threshold
  - Pattern detection doesn't duplicate existing LearnedPreference
  - Score adjustment applies negative penalty for dismissed patterns
  - Score adjustment applies positive boost for saved patterns
  - GET /preferences/learned returns user's learned preferences
  - PATCH /preferences/learned/{id} updates status to acknowledged
  - PATCH /preferences/learned/{id} updates status to rejected
  - PATCH returns 404 for nonexistent preference
- **Frontend Framework:** Vitest + React Testing Library
- **Frontend Tests:**
  - LearnedPreferenceBanner renders pending suggestions
  - Accept button calls mutation with "acknowledged"
  - Dismiss button calls mutation with "rejected"
  - Banner hidden when no pending preferences
  - Service hooks fetch and mutate correctly (mock API)
- **Key Mock Strategy:**
  - Backend: Mock async session, return SimpleNamespace objects for SwipeEvent/LearnedPreference
  - Frontend: Mock useLearnedPreferences/useUpdateLearnedPreference hooks, render component with mock data

### Project Structure Notes

- SwipeEvent is append-only (no soft-delete) — events are immutable audit records
- LearnedPreference uses SoftDeleteMixin — rejected preferences are soft-deleted to exclude from future detection
- Pattern detection is a batch operation (called periodically or on-demand), not triggered on every swipe
- The scoring integration function (`apply_learned_preferences`) is implemented but not wired into the live pipeline in this story — that integration happens when the Job Scout Agent calls it in future stories
- The `detect_patterns` function should be idempotent — safe to call multiple times, only creates new preferences for newly detected patterns

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 4, Story 4.9]
- [Source: _bmad-output/planning-artifacts/architecture.md — Hybrid schema, agent framework]
- [Source: backend/app/db/models.py:289-309 — Match model pattern]
- [Source: backend/app/db/models.py:458-531 — UserPreference model pattern]
- [Source: backend/app/api/v1/matches.py:228-257 — update_match_status endpoint]
- [Source: backend/app/services/job_scoring.py:23-63 — ScoringResult, SCORING_PROMPT]
- [Source: frontend/src/services/matches.ts — TanStack Query hook patterns]
- [Source: frontend/src/types/matches.ts — MatchData, JobSummary interfaces]
- [Source: frontend/src/pages/Matches.tsx — Matches page integration]
- [Source: 4-8-job-detail-expansion.md — Previous story intelligence]

## Dev Agent Record

### Agent Model Used

### Route Taken

### GSD Subagents Used

### Debug Log References

### Completion Notes List

### Change Log

### File List
