---
phase: 02-onboarding-preferences
plans: 6
type: phase-plan
---

# Phase 2: Onboarding + Preferences -- Execution Plan

## Phase Goal

A new user can sign up, have their profile extracted from a resume upload (or LinkedIn data export), configure job preferences and deal-breakers, and be ready for agent activation.

## Success Criteria (all must be TRUE at phase end)

1. A new user can upload a PDF/DOCX resume and see their profile auto-populated with name, experience, skills, and education within 60 seconds
2. A user can complete the preference wizard (job type, location, salary, deal-breakers, autonomy level) in under 5 minutes
3. A user sees a first briefing preview ("magic moment") before finishing onboarding that shows what daily briefings will look like
4. Deal-breakers are stored and enforceable -- querying a user's preferences returns structured data including must-haves and never-haves

---

## Dependency Graph & Wave Structure

```
Wave 1 (parallel):
  Plan 01: Database Schema + Backend Models (migration, enums, UserPreference model, User/Profile column additions)
  Plan 02: Analytics Infrastructure (PostHog backend + frontend setup)

Wave 2 (parallel, depends on Wave 1):
  Plan 03: Resume Upload + Profile Extraction Backend (API endpoints, resume parser service, LLM extraction)
  Plan 04: Preferences Backend + Shared Frontend Components (preferences CRUD API, wizard shell, step indicator, Zod schemas, TypeScript types)

Wave 3 (depends on Wave 2):
  Plan 05: Onboarding Frontend Flow (resume upload UI, profile review UI, briefing preview, onboarding wizard controller)

Wave 4 (depends on Plans 04 + 05):
  Plan 06: Preference Wizard Frontend + Integration Wiring (all 7 preference steps, summary, onboarding guard, analytics events, route wiring)
```

---

## Plan 01: Database Schema + Backend Models

**Wave:** 1 (no dependencies)
**Stories:** Partial 1-2, 2-1 through 2-6 (schema foundation for all preference + profile work)
**Estimated effort:** 20-30 min Claude execution

### Objective

Create the Alembic migration and update SQLAlchemy models to support onboarding state tracking, enhanced profile fields, and the full `user_preferences` table with hybrid relational + JSONB schema. This is the foundation every other plan depends on.

### Tasks

**Task 1: Add enums and update SQLAlchemy models**
- Files: `backend/app/db/models.py`
- Action:
  - Add new enums at top of file:
    - `OnboardingStatus(str, enum.Enum)`: `NOT_STARTED`, `PROFILE_PENDING`, `PROFILE_COMPLETE`, `PREFERENCES_PENDING`, `COMPLETE`
    - `WorkArrangement(str, enum.Enum)`: `REMOTE`, `HYBRID`, `ONSITE`, `OPEN`
    - `AutonomyLevel(str, enum.Enum)`: `L0_SUGGESTIONS = "l0"`, `L1_DRAFTS = "l1"`, `L2_SUPERVISED = "l2"`, `L3_AUTONOMOUS = "l3"`
  - Add columns to `User` model:
    - `onboarding_status = Column(Text, nullable=False, server_default="not_started")` -- using Text, not Enum, for flexibility
    - `onboarding_started_at = Column(DateTime(timezone=True), nullable=True)`
    - `onboarding_completed_at = Column(DateTime(timezone=True), nullable=True)`
    - `display_name = Column(Text, nullable=True)`
    - Add relationship: `preferences = relationship("UserPreference", back_populates="user", uselist=False)`
  - Add columns to `Profile` model:
    - `headline = Column(Text, nullable=True)` -- professional summary
    - `phone = Column(Text, nullable=True)` -- from resume extraction
    - `resume_storage_path = Column(Text, nullable=True)` -- Supabase Storage path
    - `extraction_source = Column(Text, nullable=True)` -- 'resume' | 'linkedin' | 'manual'
    - `extraction_confidence = Column(Numeric(3, 2), nullable=True)` -- 0.00 to 1.00
  - Create new `UserPreference` model (class UserPreference(SoftDeleteMixin, TimestampMixin, Base)):
    - `__tablename__ = "user_preferences"`
    - `id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)`
    - `user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)`
    - Job type columns: `job_categories`, `target_titles`, `seniority_levels` (all `ARRAY(Text)`, default `[]`)
    - Location columns: `work_arrangement` (Text, nullable), `target_locations` (ARRAY(Text)), `excluded_locations` (ARRAY(Text)), `willing_to_relocate` (Boolean, default False)
    - Salary columns: `salary_minimum` (Integer, nullable), `salary_target` (Integer, nullable), `salary_flexibility` (Text, nullable), `comp_preference` (Text, nullable)
    - Deal-breaker columns: `min_company_size` (Integer, nullable), `excluded_companies` (ARRAY(Text)), `excluded_industries` (ARRAY(Text)), `must_have_benefits` (ARRAY(Text)), `max_travel_percent` (Integer, nullable), `no_oncall` (Boolean, default False)
    - H1B columns: `requires_h1b_sponsorship` (Boolean, default False), `requires_greencard_sponsorship` (Boolean, default False), `current_visa_type` (Text, nullable), `visa_expiration` (DateTime(timezone=True), nullable)
    - Autonomy: `autonomy_level = Column(Text, nullable=False, server_default="l0")`
    - Flexible: `extra_preferences = Column(JSONB, server_default="{}")`
    - Relationship: `user = relationship("User", back_populates="preferences")`
  - Import `Boolean, Numeric` from sqlalchemy if not already imported
- Verify: `cd backend && python -c "from app.db.models import User, Profile, UserPreference, OnboardingStatus, WorkArrangement, AutonomyLevel; print('OK')"` prints OK
- Done: All Phase 2 models and enums exist and are importable

**Task 2: Create Alembic migration for Phase 2 schema**
- Files: `backend/alembic/versions/xxxx_phase2_onboarding_preferences.py` (NEW, auto-generated then edited)
- Action:
  - Run `cd backend && alembic revision --autogenerate -m "phase2_onboarding_preferences"` to auto-detect model changes
  - Review the generated migration. It should include:
    - ALTER TABLE users ADD COLUMN onboarding_status, onboarding_started_at, onboarding_completed_at, display_name
    - ALTER TABLE profiles ADD COLUMN headline, phone, resume_storage_path, extraction_source, extraction_confidence
    - CREATE TABLE user_preferences with all columns from the model
    - CREATE INDEX on user_preferences(user_id), user_preferences(requires_h1b_sponsorship), user_preferences(autonomy_level)
  - If autogenerate misses ARRAY or JSONB columns (common issue), add them manually
  - Add `from sqlalchemy.dialects.postgresql import ARRAY, JSONB` to the migration imports if needed
  - Run `cd backend && alembic upgrade head` to apply migration
  - If Alembic upgrade fails because the DB is not running locally, ensure the migration file is syntactically correct by reviewing it manually. The migration will be applied when the DB is available.
- Verify: `cd backend && alembic heads` shows the new migration as head; `cd backend && python -c "from app.db.models import UserPreference; print(UserPreference.__tablename__)"` prints "user_preferences"
- Done: Migration file exists and is syntactically valid; models match the migration

### Acceptance Criteria
- `UserPreference` model has all columns defined in RESEARCH.md Pattern 3
- `User` model has `onboarding_status`, `display_name`, and timestamp columns
- `Profile` model has `headline`, `phone`, `resume_storage_path`, `extraction_source`, `extraction_confidence`
- Migration file exists at `backend/alembic/versions/`
- All models importable without errors

---

## Plan 02: Analytics Infrastructure (PostHog)

**Wave:** 1 (no dependencies, parallel with Plan 01)
**Stories:** 1-6 (Onboarding Analytics Events -- infrastructure only, events added in Plan 06)
**Estimated effort:** 15-20 min Claude execution

### Objective

Install PostHog (backend + frontend), create reusable analytics service and hook, and configure initialization. This is pure infrastructure -- actual event tracking is wired in Plan 06.

### Tasks

**Task 1: Backend PostHog setup**
- Files: `backend/requirements.txt`, `backend/app/config.py`, `backend/app/services/analytics_service.py` (NEW)
- Action:
  - Add `posthog>=3.0.0` to `backend/requirements.txt`
  - Add to `Settings` class in `backend/app/config.py`:
    - `POSTHOG_API_KEY: str = ""`
    - `POSTHOG_HOST: str = "https://us.i.posthog.com"` (PostHog Cloud default)
  - Create `backend/app/services/analytics_service.py`:
    ```python
    """PostHog analytics event tracking. Fire-and-forget -- never breaks user flow."""
    import posthog
    from app.config import settings

    _initialized = False

    def _ensure_init():
        global _initialized
        if not _initialized and settings.POSTHOG_API_KEY:
            posthog.project_api_key = settings.POSTHOG_API_KEY
            posthog.host = settings.POSTHOG_HOST
            _initialized = True

    def track_event(user_id: str, event: str, properties: dict | None = None):
        """Track an analytics event. Silent on failure."""
        try:
            _ensure_init()
            if not settings.POSTHOG_API_KEY:
                return  # Analytics disabled
            posthog.capture(distinct_id=user_id, event=event, properties=properties or {})
        except Exception:
            pass  # Analytics must never break user flow

    def identify_user(user_id: str, properties: dict | None = None):
        """Identify a user with properties."""
        try:
            _ensure_init()
            if not settings.POSTHOG_API_KEY:
                return
            posthog.identify(distinct_id=user_id, properties=properties or {})
        except Exception:
            pass
    ```
  - Add `POSTHOG_API_KEY=` and `POSTHOG_HOST=https://us.i.posthog.com` to `backend/.env.example`
- Verify: `cd backend && python -c "from app.services.analytics_service import track_event, identify_user; print('OK')"` prints OK
- Done: Backend analytics service exists and is importable; gracefully does nothing when API key is empty

**Task 2: Frontend PostHog setup**
- Files: `frontend/package.json` (install posthog-js), `frontend/src/hooks/useAnalytics.ts` (NEW), `frontend/src/providers/AnalyticsProvider.tsx` (NEW), `frontend/src/main.jsx`
- Action:
  - Run `cd frontend && npm install posthog-js`
  - Create `frontend/src/providers/AnalyticsProvider.tsx`:
    ```tsx
    import posthog from 'posthog-js';
    import { useEffect } from 'react';
    import { useUser } from '@clerk/clerk-react';

    const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY || '';
    const POSTHOG_HOST = import.meta.env.VITE_POSTHOG_HOST || 'https://us.i.posthog.com';

    let initialized = false;

    export function AnalyticsProvider({ children }: { children: React.ReactNode }) {
      const { user } = useUser();

      useEffect(() => {
        if (!initialized && POSTHOG_KEY) {
          posthog.init(POSTHOG_KEY, {
            api_host: POSTHOG_HOST,
            loaded: (ph) => {
              if (import.meta.env.DEV) ph.debug();
            },
          });
          initialized = true;
        }
      }, []);

      useEffect(() => {
        if (user && POSTHOG_KEY) {
          posthog.identify(user.id, {
            email: user.primaryEmailAddress?.emailAddress,
            name: user.fullName,
          });
        }
      }, [user]);

      return <>{children}</>;
    }
    ```
  - Create `frontend/src/hooks/useAnalytics.ts`:
    ```typescript
    import posthog from 'posthog-js';

    export function useAnalytics() {
      return {
        track: (event: string, properties?: Record<string, unknown>) => {
          try {
            posthog.capture(event, properties);
          } catch {
            // Analytics must never break user flow
          }
        },
      };
    }
    ```
  - Add `<AnalyticsProvider>` wrapper inside the ClerkProvider in the app entry point (either `main.jsx` or `App.tsx` -- whichever wraps providers). Place it after ClerkProvider but before QueryProvider.
  - Add to `frontend/.env.example`: `VITE_POSTHOG_KEY=` and `VITE_POSTHOG_HOST=https://us.i.posthog.com`
- Verify: `cd frontend && npx tsc --noEmit src/hooks/useAnalytics.ts src/providers/AnalyticsProvider.tsx 2>&1 | head -5` -- should have no errors (or minimal existing errors unrelated to new files). If tsc is not configured for type checking, verify via `npm run build` or `npm run dev` starts without errors.
- Done: PostHog initialized on app load; `useAnalytics` hook available for all components; gracefully no-ops when key is empty

### Acceptance Criteria
- `posthog` in backend requirements.txt and frontend package.json
- Analytics service and hook both gracefully no-op when API keys are not set
- Provider wraps the app tree
- `.env.example` files document the new env vars

---

## Plan 03: Resume Upload + Profile Extraction Backend

**Wave:** 2 (depends on Plan 01 -- needs UserPreference model, Profile columns, User onboarding_status)
**Stories:** 1-1 (LinkedIn URL -- secondary), 1-2 (Resume Upload), 1-3 (Profile Confirm -- backend), 1-5 (Empty State -- error responses)
**Estimated effort:** 30-45 min Claude execution

### Objective

Build the backend API endpoints and services for resume upload, LLM-powered profile extraction (OpenAI structured outputs via GPT-4o-mini), profile confirmation/save, LinkedIn URL extraction (secondary path with graceful failure), and the "ensure user exists" middleware. This is the core backend for the onboarding flow.

### Tasks

**Task 1: Resume parser service with OpenAI structured outputs**
- Files: `backend/app/services/resume_parser.py` (NEW)
- Action:
  - Create Pydantic models for structured extraction:
    - `WorkExperience(BaseModel)`: company (str), title (str), start_date (str | None), end_date (str | None), description (str | None)
    - `Education(BaseModel)`: institution (str), degree (str | None), field (str | None), graduation_year (str | None)
    - `ExtractedProfile(BaseModel)`: name (str), email (str | None), phone (str | None), headline (str | None), skills (list[str]), experience (list[WorkExperience]), education (list[Education])
  - Implement `extract_text_from_pdf(file_bytes: bytes) -> str` using PyPDF2 (already installed):
    - Use `PdfReader(io.BytesIO(file_bytes))` and join all page text
    - If total extracted text < 50 chars, raise `ValueError("This file appears to be image-based. Please upload a text-based PDF or DOCX file.")`
  - Implement `extract_text_from_docx(file_bytes: bytes) -> str` using python-docx (already installed)
  - Implement `async def extract_profile_from_resume(file_bytes: bytes, filename: str) -> ExtractedProfile`:
    - Determine file type from filename extension (.pdf or .docx)
    - Extract raw text, validate non-empty
    - Call OpenAI `client.beta.chat.completions.parse()` with:
      - `model="gpt-4o-mini"`
      - System prompt: "You are a resume parser. Extract structured information from the resume text provided. Be accurate -- only include information explicitly present in the resume. Do not infer or fabricate any details."
      - User message: `raw_text[:8000]` (truncate to ~2K tokens)
      - `response_format=ExtractedProfile`
    - Return parsed profile
    - Use `AsyncOpenAI()` client (reads OPENAI_API_KEY from env automatically)
  - Raise `ValueError` for unsupported file types
- Verify: `cd backend && python -c "from app.services.resume_parser import ExtractedProfile, extract_text_from_pdf, extract_text_from_docx, extract_profile_from_resume; print('OK')"` prints OK
- Done: Resume parser service handles PDF and DOCX extraction via LLM structured outputs

**Task 2: LinkedIn extractor service (secondary path)**
- Files: `backend/app/services/linkedin_extractor.py` (NEW)
- Action:
  - Create `async def extract_from_linkedin_url(url: str) -> ExtractedProfile | None`:
    - Validate URL contains "linkedin.com/in/"
    - Use `httpx.AsyncClient(timeout=15.0)` to fetch public profile page
    - Set User-Agent header
    - If status != 200 or any exception, return None (graceful failure)
    - Attempt to parse JSON-LD structured data from meta tags using BeautifulSoup (already installed: `beautifulsoup4`)
    - If meaningful data found, construct and return `ExtractedProfile`
    - If parsing yields too little data, return None
    - Wrap entire function in try/except that returns None on any error
  - This function MUST be designed to fail gracefully. LinkedIn blocking is expected behavior, not an error.
- Verify: `cd backend && python -c "from app.services.linkedin_extractor import extract_from_linkedin_url; print('OK')"` prints OK
- Done: LinkedIn extractor exists and returns None on any failure

**Task 3: Onboarding API endpoints**
- Files: `backend/app/api/v1/onboarding.py` (NEW), `backend/app/api/v1/__init__.py` (update to include router)
- Action:
  - Create FastAPI router with `prefix="/onboarding", tags=["onboarding"]`
  - Create Pydantic request/response schemas in the same file or a separate schemas file:
    - `ProfileConfirmRequest(BaseModel)`: name (str), headline (str | None), phone (str | None), skills (list[str]), experience (list[dict]), education (list[dict]), extraction_source (str)
    - `OnboardingStatusResponse(BaseModel)`: onboarding_status (str), display_name (str | None)
  - Implement `ensure_user_exists` dependency:
    ```python
    async def ensure_user_exists(clerk_user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)) -> User:
        result = await db.execute(select(User).where(User.clerk_id == clerk_user_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(clerk_id=clerk_user_id, email=f"pending-{clerk_user_id}@setup.jobpilot.com", onboarding_status="not_started")
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user
    ```
  - Endpoints:
    - `GET /onboarding/status` -- returns current onboarding_status + display_name. Uses `ensure_user_exists`.
    - `POST /onboarding/resume/upload` -- accepts `UploadFile`, validates file type (PDF/DOCX) and size (max 10MB), stores in Supabase Storage via existing `storage_service`, extracts profile via `extract_profile_from_resume`, returns extracted data for review (NOT saved to DB yet). Updates `onboarding_status` to "profile_pending". Tracks `profile_extraction_completed` or `profile_extraction_failed` analytics event.
    - `POST /onboarding/linkedin/extract` -- accepts `{"url": "..."}`, calls `extract_from_linkedin_url`. If None returned, return 422 with message "Could not extract profile from LinkedIn. Try uploading your resume instead." If successful, return extracted data for review.
    - `PUT /onboarding/profile/confirm` -- accepts `ProfileConfirmRequest`, upserts Profile record (skills, experience, education, headline, phone, extraction_source), updates User.display_name and onboarding_status to "profile_complete". Returns confirmed profile.
    - `GET /onboarding/profile` -- returns current profile data for the user (for profile review editing)
  - Register router in `backend/app/api/v1/__init__.py` (or wherever routers are aggregated). Check existing pattern -- likely in `backend/app/main.py` or a router aggregation file. Match the existing pattern for including API routers.
  - Use `from app.services.analytics_service import track_event` for event tracking in endpoints
- Verify: `cd backend && python -c "from app.api.v1.onboarding import router; print([r.path for r in router.routes])"` prints the route paths
- Done: All onboarding API endpoints exist and are registered; resume upload extracts via LLM; LinkedIn extraction fails gracefully; profile confirmation persists to DB

### Acceptance Criteria
- `POST /api/v1/onboarding/resume/upload` accepts PDF/DOCX, returns extracted profile JSON
- `POST /api/v1/onboarding/linkedin/extract` returns profile or 422 with fallback message
- `PUT /api/v1/onboarding/profile/confirm` saves profile to DB and updates onboarding status
- `GET /api/v1/onboarding/status` returns current onboarding state
- File size limit (10MB) and type validation enforced
- Image-based PDFs return clear error message (not hallucinated data)

---

## Plan 04: Preferences Backend + Shared Frontend Components

**Wave:** 2 (depends on Plan 01 -- needs UserPreference model; parallel with Plan 03)
**Stories:** 2-1 through 2-8 (backend), shared UI components for both wizards
**Estimated effort:** 30-40 min Claude execution

### Objective

Build the preferences CRUD API endpoints and the shared frontend components (TypeScript types, Zod schemas, wizard shell, step indicator, empty states) that both the onboarding wizard and preference wizard will use.

### Tasks

**Task 1: Preferences API endpoints**
- Files: `backend/app/api/v1/preferences.py` (NEW)
- Action:
  - Create FastAPI router with `prefix="/preferences", tags=["preferences"]`
  - Create Pydantic schemas:
    - `JobTypePreferences(BaseModel)`: categories (list[str]), target_titles (list[str]), seniority_levels (list[str])
    - `LocationPreferences(BaseModel)`: work_arrangement (str | None), target_locations (list[str]), excluded_locations (list[str]), willing_to_relocate (bool)
    - `SalaryPreferences(BaseModel)`: minimum (int | None), target (int | None), flexibility (str | None), comp_preference (str | None)
    - `DealBreakers(BaseModel)`: min_company_size (int | None), excluded_companies (list[str]), excluded_industries (list[str]), must_have_benefits (list[str]), max_travel_percent (int | None), no_oncall (bool)
    - `H1BPreferences(BaseModel)`: requires_h1b (bool), requires_greencard (bool), current_visa_type (str | None), visa_expiration (str | None)
    - `AutonomyPreference(BaseModel)`: level (str) -- one of "l0", "l1", "l2", "l3"
    - `FullPreferences(BaseModel)`: combines all above sections plus extra_preferences (dict)
    - `PreferenceSummaryResponse(BaseModel)`: all fields, plus computed `is_complete: bool` and `missing_sections: list[str]`
  - Endpoints (all use `ensure_user_exists` dependency from Plan 03):
    - `GET /preferences` -- returns full preferences for user (or defaults if none exist)
    - `PUT /preferences` -- accepts `FullPreferences`, upserts UserPreference record. Updates User.onboarding_status to "complete" if onboarding was in "preferences_pending" state. Returns saved preferences.
    - `PATCH /preferences/{section}` -- accepts partial update for a single section (job_type, location, salary, deal_breakers, h1b, autonomy). Useful for per-step saves.
    - `GET /preferences/summary` -- returns `PreferenceSummaryResponse` with completion status and missing sections
    - `GET /preferences/deal-breakers` -- returns ONLY deal-breakers in structured format for agent consumption. Returns `{must_haves: {...}, never_haves: {...}}` format.
  - Register router alongside the onboarding router
- Verify: `cd backend && python -c "from app.api.v1.preferences import router; print([r.path for r in router.routes])"` prints route paths
- Done: Full preferences CRUD API with per-section and full-update endpoints; deal-breaker query endpoint returns structured must-haves/never-haves

**Task 2: Shared frontend TypeScript types, Zod schemas, and wizard components**
- Files:
  - `frontend/src/types/onboarding.ts` (NEW)
  - `frontend/src/types/preferences.ts` (NEW)
  - `frontend/src/components/shared/StepIndicator.tsx` (NEW)
  - `frontend/src/components/shared/EmptyState.tsx` (NEW)
  - `frontend/src/components/shared/WizardShell.tsx` (NEW)
  - `frontend/src/hooks/useOnboarding.ts` (NEW)
- Action:
  - Create `frontend/src/types/onboarding.ts`:
    - `ExtractedProfile` type matching backend Pydantic model (name, email, phone, headline, skills, experience[], education[])
    - `WorkExperience` type (company, title, startDate, endDate, description)
    - `Education` type (institution, degree, field, graduationYear)
    - `OnboardingStatus` type: 'not_started' | 'profile_pending' | 'profile_complete' | 'preferences_pending' | 'complete'
    - `ProfileConfirmRequest` type
  - Create `frontend/src/types/preferences.ts`:
    - Types for each preference section matching backend schemas
    - `FullPreferences` type combining all sections
    - `PreferenceSummary` type with is_complete and missing_sections
    - Zod schemas for each preference step (used by react-hook-form):
      - `jobTypeSchema`: categories min 1, targetTitles min 1, seniorityLevels min 1
      - `locationSchema`: workArrangement required, targetLocations (optional)
      - `salarySchema`: minimum (optional number), target (optional number), flexibility (optional)
      - `dealBreakerSchema`: all optional fields
      - `h1bSchema`: requiresH1b (boolean), related fields
      - `autonomySchema`: level required, one of l0/l1/l2/l3
  - Create `StepIndicator.tsx`:
    - Props: `currentStep: number`, `totalSteps: number`, `stepLabels: string[]`, `completedSteps: Set<number>`
    - Renders a horizontal progress bar with numbered steps
    - Current step highlighted, completed steps show checkmark
    - Responsive: collapses to "Step X of Y" on mobile
  - Create `EmptyState.tsx`:
    - Props: `icon?: ReactNode`, `title: string`, `description: string`, `action?: { label: string, onClick: () => void }`
    - Reusable empty state card with centered content
    - Used for Story 1-5 and Story 2-8 empty states
  - Create `WizardShell.tsx`:
    - Props: `children: ReactNode`, `currentStep: number`, `totalSteps: number`, `stepLabels: string[]`, `onBack?: () => void`, `onNext?: () => void`, `onSkip?: () => void`, `isNextDisabled?: boolean`, `isLastStep?: boolean`, `nextLabel?: string`
    - Renders StepIndicator at top, children in center, Back/Skip/Next buttons at bottom
    - Back hidden on step 0, Skip optional per step, Next shows "Finish" on last step
  - Create `frontend/src/hooks/useOnboarding.ts`:
    - Zustand store (with `persist` middleware, storage key 'jobpilot-onboarding'):
      - `currentStep: number`
      - `totalSteps: number`
      - `profileData: Partial<ExtractedProfile> | null`
      - `completedSteps: number[]` (use array, not Set -- Set doesn't serialize)
      - Actions: `setStep`, `nextStep`, `prevStep`, `setProfileData`, `markStepComplete`, `reset`
    - Separate `usePreferenceStore` in the same file or a separate file:
      - `currentStep: number`
      - `preferencesData: Partial<FullPreferences>`
      - Actions: `setStep`, `nextStep`, `prevStep`, `updateSection`, `reset`
- Verify: `cd frontend && npx tsc --noEmit 2>&1 | tail -5` -- check for any new type errors in the created files. Or run `npm run dev` and confirm it starts.
- Done: All shared types, schemas, and components exist; Zustand stores persist wizard progress; WizardShell renders step indicator and navigation buttons

### Acceptance Criteria
- Backend: `GET /api/v1/preferences/deal-breakers` returns structured must-haves and never-haves (Success Criterion 4)
- Backend: Per-section PATCH enables saving individual wizard steps
- Frontend: TypeScript types match backend Pydantic schemas
- Frontend: Zod schemas validate each preference step
- Frontend: WizardShell, StepIndicator, EmptyState are reusable across both wizards

---

## Plan 05: Onboarding Frontend Flow

**Wave:** 3 (depends on Plans 03 + 04 -- needs API endpoints, shared components, types)
**Stories:** 1-1, 1-2, 1-3, 1-4, 1-5
**Estimated effort:** 35-45 min Claude execution

### Objective

Build the complete onboarding frontend flow: resume upload with drag-and-drop, LinkedIn URL input (secondary), profile review/edit form, briefing preview "magic moment", and the onboarding page that ties it all together. After this plan, a user can go from sign-up to "profile complete" with a briefing preview shown.

### Tasks

**Task 1: Resume upload and LinkedIn URL input component**
- Files: `frontend/src/components/onboarding/ResumeUpload.tsx` (NEW)
- Action:
  - Create component with two input methods:
    1. **Primary: Resume Upload** -- Large drag-and-drop zone using `react-dropzone` (already installed). Accept `.pdf` and `.docx` only. Max 10MB. Show file name after selection.
    2. **Secondary: LinkedIn URL** -- Text input below the upload zone with "Or paste your LinkedIn profile URL" label. Validate URL contains "linkedin.com/in/".
  - On resume upload:
    - Show loading state with message "Your agent is reading your resume..." (Story 1-5)
    - Call `POST /api/v1/onboarding/resume/upload` with FormData
    - On success: call `onProfileExtracted(extractedProfile)` prop callback
    - On error: show error message in a toast or inline alert. For image-based PDFs: "This file appears to be image-based. Please upload a text-based PDF or DOCX."
  - On LinkedIn URL submit:
    - Show loading state with message "Your agent is reading your profile..."
    - Call `POST /api/v1/onboarding/linkedin/extract` with `{ url }`
    - On success: call `onProfileExtracted(extractedProfile)` prop callback
    - On 422/failure: show inline message "We couldn't access that profile. Try uploading your resume instead." and highlight the upload zone
    - If loading takes > 15 seconds, show timeout message suggesting resume upload
  - Props: `onProfileExtracted: (profile: ExtractedProfile) => void`
  - Track analytics events: `resume_uploaded`, `profile_extraction_method_chosen`
- Verify: Component renders without errors when imported; upload zone accepts drag-and-drop
- Done: Users can upload resume or paste LinkedIn URL; loading states and error handling per Story 1-5 specs

**Task 2: Profile review and briefing preview components**
- Files:
  - `frontend/src/components/onboarding/ProfileReview.tsx` (NEW)
  - `frontend/src/components/onboarding/BriefingPreview.tsx` (NEW)
- Action:
  - **ProfileReview.tsx** (Story 1-3):
    - Props: `initialProfile: ExtractedProfile`, `onConfirm: (profile: ProfileConfirmRequest) => void`, `onBack: () => void`
    - Use `react-hook-form` with the extracted profile as default values
    - Editable fields: name (required), headline, phone, skills (tag input -- add/remove), experience (list of editable cards with company/title/dates/description), education (list of editable cards)
    - "Add Experience" and "Add Education" buttons to add new entries
    - Remove button on each experience/education entry
    - Validation: name required, at least 1 work experience required (per Story 1-3: "I cannot proceed until at least name and one work experience exist")
    - If extraction yielded < 3 fields, show EmptyState inline: "We found some info! Help your agent by adding more details below" (Story 1-5)
    - "Confirm Profile" button calls `onConfirm` with the edited data
    - Track: `profile_confirmed` with `fields_edited_count`
  - **BriefingPreview.tsx** (Story 1-4):
    - Props: `userName: string`, `onContinue: () => void`
    - Display mock briefing data:
      - "Good morning, {userName}!" greeting
      - "Your agent found 3 matches while you were away" header
      - 3 mock job cards with title, company, score (92, 87, 84), location, salary range
      - Preview of approval actions (thumbs up/down icons, grayed out)
    - Clear label at top: "Preview -- Your first real briefing arrives tomorrow"
    - "Continue to Preferences" button calls `onContinue`
    - Use Tailwind for styling: card layout, subtle shadows, indigo/blue accent colors matching the app theme
    - Track: `briefing_preview_viewed`
- Verify: Both components render without errors when imported with mock props
- Done: Profile review allows editing all fields with validation; briefing preview shows personalized mock data with "magic moment" effect

**Task 3: Onboarding page and routing**
- Files:
  - `frontend/src/pages/Onboarding.tsx` (NEW)
  - `frontend/src/App.tsx` (update to add /onboarding route)
- Action:
  - **Onboarding.tsx**:
    - Multi-step controller using `useOnboarding` Zustand store
    - Steps: 0 = ResumeUpload, 1 = ProfileReview, 2 = BriefingPreview
    - On mount: call `GET /api/v1/onboarding/status` -- if already "complete", redirect to /dashboard. If "profile_complete" or "preferences_pending", redirect to step 2 or skip to preferences.
    - Step 0 (ResumeUpload): on profile extracted, save to Zustand store, advance to step 1
    - Step 1 (ProfileReview): on confirm, call `PUT /api/v1/onboarding/profile/confirm`, advance to step 2
    - Step 2 (BriefingPreview): on continue, navigate to preference wizard or /preferences route
    - Wrap in WizardShell with step labels: ["Upload Resume", "Review Profile", "First Look"]
    - Track `onboarding_started` on mount (only if status was "not_started")
  - **App.tsx updates**:
    - Import Onboarding page
    - Add route: `<Route path="/onboarding" element={<ProtectedRoute><Onboarding /></ProtectedRoute>} />`
    - The onboarding guard (redirecting non-onboarded users) will be added in Plan 06 to avoid breaking existing routes during development
- Verify: `npm run dev` starts; navigating to `/onboarding` shows the ResumeUpload step (when signed in)
- Done: Complete onboarding flow from resume upload through profile review to briefing preview; progress persists across page refreshes via Zustand persist

### Acceptance Criteria
- Resume upload accepts PDF/DOCX via drag-and-drop with loading state (Story 1-2)
- LinkedIn URL input with graceful failure and fallback to upload (Story 1-1)
- Profile review shows all extracted fields as editable, requires name + 1 experience (Story 1-3)
- Empty state messages for slow extraction and limited results (Story 1-5)
- Briefing preview shows personalized mock data with "magic moment" feel (Story 1-4)
- Progress survives page refresh (Zustand persist)
- `/onboarding` route is protected and accessible

---

## Plan 06: Preference Wizard Frontend + Integration Wiring

**Wave:** 4 (depends on Plans 04 + 05 -- needs preference API, shared components, onboarding flow complete)
**Stories:** 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 2-7, 2-8, 1-6
**Estimated effort:** 40-50 min Claude execution

### Objective

Build all 7 preference wizard steps plus summary/confirmation, wire the onboarding guard (redirect incomplete users), add all analytics events throughout the flow, and connect the onboarding -> preferences -> dashboard pipeline end-to-end. After this plan, the full Phase 2 user journey works.

### Tasks

**Task 1: Preference wizard step components (7 steps)**
- Files:
  - `frontend/src/components/preferences/JobTypeStep.tsx` (NEW)
  - `frontend/src/components/preferences/LocationStep.tsx` (NEW)
  - `frontend/src/components/preferences/SalaryStep.tsx` (NEW)
  - `frontend/src/components/preferences/DealBreakerStep.tsx` (NEW)
  - `frontend/src/components/preferences/H1BStep.tsx` (NEW)
  - `frontend/src/components/preferences/AutonomyStep.tsx` (NEW)
  - `frontend/src/components/preferences/SummaryStep.tsx` (NEW)
- Action:
  - Each step component follows the same pattern:
    - Uses `react-hook-form` with `zodResolver` and the corresponding Zod schema from `types/preferences.ts`
    - Props: `defaultValues: Partial<StepData>`, `onSubmit: (data: StepData) => void`, `onSkip?: () => void`
    - Renders form fields appropriate to the step
    - `onSubmit` saves data to Zustand preference store AND calls `PATCH /api/v1/preferences/{section}` to persist server-side
  - **JobTypeStep.tsx** (Story 2-1):
    - Multi-select chip picker for job categories: Engineering, Product, Design, Data Science, Marketing, Sales, Operations, Finance, HR, Legal, Other
    - Tag input for target job titles (free text, add on Enter)
    - Multi-select chip picker for seniority: Entry, Mid, Senior, Staff, Principal, Director, VP, C-Level
  - **LocationStep.tsx** (Story 2-2):
    - Radio group for work arrangement: Remote Only, Hybrid, On-site Only, Open to All
    - If Hybrid: number input for "days per week in office" (store in extra_preferences JSONB)
    - Tag input for target cities/metro areas
    - Tag input for excluded locations
    - Checkbox: "Willing to relocate"
  - **SalaryStep.tsx** (Story 2-3):
    - Number input for minimum salary (USD, annual) with dollar formatting
    - Number input for target salary
    - Radio: "Firm minimum" vs "Negotiable"
    - Radio: "Base salary only" vs "Total compensation (including equity/bonus)"
    - Note text: "Your salary info is private and never shared with employers"
  - **DealBreakerStep.tsx** (Story 2-4):
    - Section header "Must-Haves":
      - Number input for minimum company size (optional)
      - Multi-select chips for required benefits: 401k Match, Health Insurance, Unlimited PTO, Remote Option, Equity/Stock Options, Parental Leave, Professional Development Budget
    - Section header "Never-Haves":
      - Tag input for excluded companies
      - Tag input for excluded industries
      - Slider or number input for max travel percentage (0-100%)
      - Checkbox: "No on-call required"
    - Warning banner: "Jobs violating deal-breakers will be automatically filtered out"
  - **H1BStep.tsx** (Story 2-5):
    - Toggle: "I require H1B visa sponsorship"
    - Toggle: "I require green card sponsorship"
    - If either toggle on:
      - Dropdown for current visa type: H1B, OPT, OPT STEM, L1, J1, TN, Other
      - Date picker for visa expiration
    - Note: "H1B users can upgrade to H1B Pro for verified sponsor data"
  - **AutonomyStep.tsx** (Story 2-6):
    - 4 radio cards with icon, title, and description:
      - L0 Suggestions Only: "Your agent suggests, you do everything"
      - L1 Draft Mode: "Your agent drafts emails and resumes, you review and send"
      - L2 Supervised: "Your agent acts on your behalf, you approve via daily digest"
      - L3 Autonomous: "Your agent acts freely within your deal-breakers"
    - Visual emphasis on L0 as "Recommended for new users"
    - Note: "You can change this anytime in Settings"
  - **SummaryStep.tsx** (Story 2-7):
    - Displays all preferences in a read-only card layout organized by section
    - Each section has an "Edit" button that navigates back to that step
    - Skipped sections show: "Not specified -- agent will consider all options" (Story 2-8)
    - Tip banner: "The more you tell your agent, the better your matches" (Story 2-8)
    - "Start My Agent" button: calls `PUT /api/v1/preferences` with full preferences, updates onboarding status to "complete", navigates to /dashboard
    - Confirmation toast: "Your agent is now active! Check back tomorrow for your first briefing." (Story 2-7)
- Verify: Each step component renders without errors when imported with mock props
- Done: All 7 preference steps plus summary with inline edit capability; per-step server persistence; empty state handling for skipped steps

**Task 2: Preference wizard page, onboarding guard, and full flow wiring**
- Files:
  - `frontend/src/pages/Preferences.tsx` (NEW)
  - `frontend/src/providers/OnboardingGuard.tsx` (NEW)
  - `frontend/src/App.tsx` (update routes + add guard)
- Action:
  - **Preferences.tsx**:
    - Multi-step controller using `usePreferenceStore` Zustand store
    - Steps: 0=JobType, 1=Location, 2=Salary, 3=DealBreakers, 4=H1B, 5=Autonomy, 6=Summary
    - On mount: call `GET /api/v1/preferences` to load existing preferences (for users returning mid-wizard)
    - Each step's onSubmit: save to Zustand + PATCH server + advance to next step
    - Each step's onSkip: advance without saving (section remains empty/default)
    - Wrap in WizardShell with step labels: ["Job Type", "Location", "Salary", "Deal-Breakers", "Visa", "Autonomy", "Summary"]
    - H1B step (index 4) can be conditionally shown or always shown (keep it always shown for simplicity, users can skip)
    - Track `preference_wizard_started` on mount, `preference_step_completed` and `preference_step_skipped` per step, `preferences_confirmed` on final submit
  - **OnboardingGuard.tsx**:
    - Wraps protected app routes (not the onboarding/preferences pages themselves)
    - On mount: check Clerk user metadata `onboarding_completed` (fast) OR call `GET /api/v1/onboarding/status`
    - If onboarding_status is "not_started" or "profile_pending": redirect to `/onboarding`
    - If onboarding_status is "profile_complete" or "preferences_pending": redirect to `/preferences`
    - If "complete": render children
    - Skip guard for `/onboarding` and `/preferences` paths (check location.pathname)
  - **App.tsx updates**:
    - Add route: `<Route path="/preferences" element={<ProtectedRoute><Preferences /></ProtectedRoute>} />`
    - Wrap the `/dashboard` ProtectedRoute with OnboardingGuard: `<OnboardingGuard><Dashboard /></OnboardingGuard>`
    - Do NOT wrap legacy routes (email, linkedin, etc.) with the guard -- they remain public
  - Wire the full flow:
    - Sign up -> Clerk auth -> first visit to /dashboard -> OnboardingGuard redirects to /onboarding -> upload resume -> review profile -> briefing preview -> navigate to /preferences -> complete wizard -> navigate to /dashboard
- Verify: `npm run dev` starts; the full flow works when clicking through manually
- Done: Complete end-to-end onboarding + preference flow with guard redirects; analytics events tracked throughout

**Task 3: Analytics event wiring throughout the flow**
- Files: Update files from Tasks 1-2 of this plan + files from Plan 05 to add `useAnalytics` calls
- Action:
  - This task is about ensuring all Story 1-6 analytics events are tracked. Most will already be added inline during Tasks 1-2 of this plan and Tasks 1-3 of Plan 05. This task is a sweep to catch any missing events.
  - Required events (Story 1-6):
    - `onboarding_started` -- in Onboarding.tsx on mount (Plan 05)
    - `profile_extraction_method_chosen` -- in ResumeUpload.tsx (Plan 05)
    - `resume_uploaded` -- in ResumeUpload.tsx (Plan 05)
    - `profile_extraction_completed` -- in ResumeUpload.tsx on API success (Plan 05)
    - `profile_extraction_failed` -- in ResumeUpload.tsx on API error (Plan 05)
    - `profile_review_started` -- in ProfileReview.tsx on mount (Plan 05)
    - `profile_confirmed` -- in ProfileReview.tsx on confirm (Plan 05)
    - `briefing_preview_viewed` -- in BriefingPreview.tsx on mount (Plan 05)
    - `preference_wizard_started` -- in Preferences.tsx on mount (this plan)
    - `preference_step_completed` -- in each step's onSubmit (this plan)
    - `preference_step_skipped` -- in each step's onSkip (this plan)
    - `preferences_confirmed` -- in SummaryStep on "Start My Agent" (this plan)
    - `onboarding_completed` -- in SummaryStep after preferences confirmed (this plan)
  - Backend also tracks key events: the `POST /onboarding/resume/upload` and `PUT /onboarding/profile/confirm` endpoints should call `track_event` (added in Plan 03)
  - Verify each event includes the properties specified in RESEARCH.md analytics section (user_id comes from PostHog identify; add step_name, step_number, duration_ms, field_count as appropriate)
- Verify: Open browser dev tools network tab, go through onboarding flow, confirm PostHog capture calls are made for each event (if PostHog key is configured). Or grep the codebase: `grep -r "track(" frontend/src/` should show all events.
- Done: All 13 analytics events from Story 1-6 are tracked with correct properties

### Acceptance Criteria
- Preference wizard has all 7 steps rendering with proper form validation (Stories 2-1 through 2-6)
- Summary step shows all preferences with edit-in-place capability (Story 2-7)
- Skipped steps show "Not specified" empty state with encouragement (Story 2-8)
- OnboardingGuard redirects incomplete users to appropriate step
- Full flow works: sign-up -> onboarding -> preferences -> dashboard
- All 13 analytics events tracked (Story 1-6)
- "Start My Agent" completes onboarding and shows confirmation message (Story 2-7)

---

## Phase 2 Success Verification

After all 6 plans are complete, verify the 4 success criteria:

1. **Resume -> Profile (60 sec):** Upload a test PDF resume via `/onboarding`. Profile fields (name, experience, skills, education) are auto-populated. Entire extraction completes in < 60 seconds.

2. **Preference wizard (< 5 min):** Starting from the briefing preview "Continue" button, click through all 7 preference steps filling in sample data. Total time should be under 5 minutes for a deliberate user.

3. **Magic moment (briefing preview):** After confirming profile, the briefing preview step shows "Good morning, [Name]!" with 3 mock job matches and a "Preview" label. User feels the value proposition before entering preferences.

4. **Deal-breakers enforceable:** Call `GET /api/v1/preferences/deal-breakers` -- response includes structured `must_haves` (min_company_size, must_have_benefits) and `never_haves` (excluded_companies, excluded_industries, max_travel_percent, no_oncall) that agents can query programmatically.
