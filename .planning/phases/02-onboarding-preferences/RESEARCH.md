# Phase 2: Onboarding + Preferences - Research

**Researched:** 2026-01-31
**Domain:** Resume parsing, onboarding UX, preference storage, LLM extraction, Clerk auth integration
**Confidence:** HIGH

## Summary

Phase 2 transforms a signed-in user into an active JobPilot user by extracting their professional profile from a resume (primary) or LinkedIn (secondary), walking them through a preference wizard, and showing a "magic moment" first briefing preview. The phase spans 14 BMAD stories across Epics 1 and 2 (Stories 1-1 through 1-6, 2-1 through 2-8).

The codebase already has strong foundations: Clerk auth with `@clerk/clerk-react` and `fastapi-clerk-auth`, Supabase Storage with file upload/validation (`storage_service.py`), PyPDF2 and python-docx for document processing, react-hook-form for forms, react-dropzone for file uploads, and TanStack Query + Zustand + Zod for state management. The main new work is (1) LLM-powered resume extraction via OpenAI structured outputs, (2) new database tables for preferences and onboarding state, (3) a multi-step wizard UI, and (4) analytics event tracking.

**Primary recommendation:** Use OpenAI's native structured output (`response_format` with Pydantic models) via GPT-4o-mini for resume extraction at ~$0.001/resume. Build a custom multi-step wizard with react-hook-form + Zod (per-step schemas) rather than adopting a library. Store deal-breakers in a dedicated `user_preferences` table with a hybrid relational + JSONB schema for efficient querying.

---

## Standard Stack

The established libraries/tools for this domain. Most are already installed in Phase 1.

### Core (Already Installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `openai` | >=2.16.0 | LLM-powered resume extraction with structured outputs | Native Pydantic support, cheapest structured extraction |
| `pypdf2` | >=3.0.1 | PDF text extraction | Already in codebase, handles most resume PDFs |
| `python-docx` | >=1.1.0 | DOCX text extraction | Already in codebase |
| `react-hook-form` | ^7.48.2 | Multi-step wizard form state | Already installed, industry standard for React forms |
| `zod` | ^3.24.0 | Per-step validation schemas | Already installed, pairs with react-hook-form |
| `react-dropzone` | ^14.2.3 | Resume file upload UI | Already installed |
| `@tanstack/react-query` | ^5.90.0 | Server state for profile/preferences | Already installed |
| `zustand` | ^5.0.0 | Wizard step state, onboarding progress | Already installed |
| `@clerk/clerk-react` | ^5.0.0 | Auth integration, user metadata | Already installed |

### New Dependencies Needed

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pydantic-ai` or `instructor` | latest | LLM structured output helpers | OPTIONAL - OpenAI SDK has native Pydantic support, so these are not strictly needed |
| `posthog-python` | >=3.0.0 | Backend analytics event tracking | For onboarding funnel analytics (Story 1-6) |
| `posthog-js` | >=1.130.0 | Frontend analytics event tracking | For onboarding funnel analytics (Story 1-6) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| OpenAI structured outputs | LangChain + PydanticOutputParser | Adds heavy dependency; OpenAI native is simpler and cheaper |
| Custom wizard | rhf-wizard library | Library is small/unmaintained; custom gives full control over UX |
| PostHog | Mixpanel | Mixpanel has better non-technical user UX; PostHog is open-source, self-hostable, includes feature flags |
| Separate preferences table | JSONB on profiles table | Dedicated table is cleaner, allows RLS, easier to query for agent matching |

**Installation (new packages only):**
```bash
# Backend
pip install posthog

# Frontend
npm install posthog-js
```

---

## Architecture Patterns

### Recommended Project Structure (New Files)

```
backend/app/
  api/v1/
    onboarding.py          # POST /resume/upload, POST /linkedin-extract, GET/PUT /profile
    preferences.py         # GET/PUT /preferences, GET/PUT /deal-breakers
  services/
    resume_parser.py       # PDF/DOCX text extraction + LLM structured extraction
    profile_extractor.py   # Orchestrates extraction from resume or LinkedIn
    linkedin_extractor.py  # LinkedIn URL public profile fetch (secondary path)
    analytics_service.py   # PostHog event tracking wrapper
  db/
    models.py              # Add UserPreference, OnboardingState models

frontend/src/
  pages/
    Onboarding.tsx         # Onboarding shell/layout
  components/onboarding/
    OnboardingWizard.tsx   # Multi-step wizard controller
    ResumeUpload.tsx       # Step 1: Upload resume or paste LinkedIn URL
    ProfileReview.tsx      # Step 2: Review/edit extracted profile
    BriefingPreview.tsx    # Step 3: Magic moment first briefing preview
  components/preferences/
    PreferenceWizard.tsx   # Preference wizard controller
    JobTypeStep.tsx        # Step 1: Job type and title preferences
    LocationStep.tsx       # Step 2: Location and remote work
    SalaryStep.tsx         # Step 3: Salary range
    DealBreakerStep.tsx    # Step 4: Deal-breakers
    H1BStep.tsx            # Step 5: Visa sponsorship (conditional)
    AutonomyStep.tsx       # Step 6: Autonomy level
    SummaryStep.tsx        # Step 7: Review and confirm
  components/shared/
    StepIndicator.tsx      # Progress bar for wizard steps
    EmptyState.tsx         # Reusable empty state component
  hooks/
    useOnboarding.ts       # Onboarding state and navigation
    useAnalytics.ts        # Analytics event tracking hook
```

### Pattern 1: LLM-Powered Resume Extraction with OpenAI Structured Outputs

**What:** Extract structured profile data from raw resume text using OpenAI's native Pydantic structured output mode.

**When to use:** Every time a user uploads a resume (Story 1-2).

**Example:**
```python
# backend/app/services/resume_parser.py
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from pypdf2 import PdfReader
from docx import Document
import io

class WorkExperience(BaseModel):
    company: str = Field(description="Company name")
    title: str = Field(description="Job title")
    start_date: str | None = Field(description="Start date as YYYY-MM or YYYY")
    end_date: str | None = Field(description="End date as YYYY-MM or 'Present'")
    description: str | None = Field(description="Brief description of role")

class Education(BaseModel):
    institution: str = Field(description="School or university name")
    degree: str | None = Field(description="Degree type (BS, MS, PhD, etc.)")
    field: str | None = Field(description="Field of study")
    graduation_year: str | None = Field(description="Graduation year")

class ExtractedProfile(BaseModel):
    """Structured profile extracted from a resume."""
    name: str = Field(description="Full name of the candidate")
    email: str | None = Field(description="Email address if present")
    phone: str | None = Field(description="Phone number if present")
    headline: str | None = Field(description="Professional headline or summary, 1-2 sentences")
    skills: list[str] = Field(default_factory=list, description="Technical and professional skills")
    experience: list[WorkExperience] = Field(default_factory=list, description="Work experience, most recent first")
    education: list[Education] = Field(default_factory=list, description="Education history")

def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def extract_text_from_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)

async def extract_profile_from_resume(
    file_bytes: bytes,
    filename: str,
) -> ExtractedProfile:
    """Extract structured profile from resume file using LLM."""
    # Step 1: Extract raw text
    if filename.lower().endswith(".pdf"):
        raw_text = extract_text_from_pdf(file_bytes)
    elif filename.lower().endswith(".docx"):
        raw_text = extract_text_from_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {filename}")

    if not raw_text.strip():
        raise ValueError("Could not extract text from file. The file may be image-based.")

    # Step 2: LLM structured extraction
    client = AsyncOpenAI()
    completion = await client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a resume parser. Extract structured information from the "
                    "resume text provided. Be accurate -- only include information that "
                    "is explicitly present in the resume. Do not infer or fabricate."
                ),
            },
            {"role": "user", "content": raw_text[:8000]},  # Truncate to ~2K tokens
        ],
        response_format=ExtractedProfile,
    )
    return completion.choices[0].message.parsed
```

**Cost estimate:** A typical resume is ~1,500 input tokens + ~500 output tokens. At GPT-4o-mini pricing ($0.15/1M input, $0.60/1M output): **~$0.0005 per resume extraction** (less than a tenth of a cent).

### Pattern 2: Multi-Step Wizard with react-hook-form + Zod

**What:** A reusable multi-step form pattern where each step has its own Zod schema and the wizard maintains state across steps.

**When to use:** Both the onboarding wizard (3 steps) and the preference wizard (7 steps).

**Example:**
```typescript
// frontend/src/hooks/useOnboarding.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface OnboardingState {
  currentStep: number;
  totalSteps: number;
  profileData: Partial<ProfileData> | null;
  preferencesData: Partial<PreferencesData> | null;
  completedSteps: Set<number>;
  setStep: (step: number) => void;
  nextStep: () => void;
  prevStep: () => void;
  setProfileData: (data: Partial<ProfileData>) => void;
  setPreferencesData: (data: Partial<PreferencesData>) => void;
  markStepComplete: (step: number) => void;
  reset: () => void;
}

export const useOnboardingStore = create<OnboardingState>()(
  persist(
    (set, get) => ({
      currentStep: 0,
      totalSteps: 3,  // Onboarding: Upload -> Review -> Briefing Preview
      profileData: null,
      preferencesData: null,
      completedSteps: new Set(),
      setStep: (step) => set({ currentStep: step }),
      nextStep: () => set((s) => ({ currentStep: Math.min(s.currentStep + 1, s.totalSteps - 1) })),
      prevStep: () => set((s) => ({ currentStep: Math.max(s.currentStep - 1, 0) })),
      setProfileData: (data) => set({ profileData: data }),
      setPreferencesData: (data) => set({ preferencesData: data }),
      markStepComplete: (step) => set((s) => {
        const newSet = new Set(s.completedSteps);
        newSet.add(step);
        return { completedSteps: newSet };
      }),
      reset: () => set({ currentStep: 0, profileData: null, preferencesData: null, completedSteps: new Set() }),
    }),
    { name: 'jobpilot-onboarding' }
  )
);

// frontend/src/components/preferences/JobTypeStep.tsx
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

const jobTypeSchema = z.object({
  categories: z.array(z.string()).min(1, "Select at least one job category"),
  targetTitles: z.array(z.string()).min(1, "Add at least one target job title"),
  seniorityLevels: z.array(z.enum([
    'entry', 'mid', 'senior', 'staff', 'principal', 'director', 'vp', 'c_level'
  ])).min(1, "Select at least one seniority level"),
});

type JobTypeFormData = z.infer<typeof jobTypeSchema>;
```

### Pattern 3: Hybrid Preference Schema

**What:** Use dedicated relational columns for frequently-queried deal-breaker fields plus JSONB for flexible/evolving preferences.

**When to use:** Storing user preferences that agents will query for job matching.

**Example:**
```python
# Addition to backend/app/db/models.py

class OnboardingStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    PROFILE_PENDING = "profile_pending"
    PROFILE_COMPLETE = "profile_complete"
    PREFERENCES_PENDING = "preferences_pending"
    COMPLETE = "complete"

class WorkArrangement(str, enum.Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    OPEN = "open"

class AutonomyLevel(str, enum.Enum):
    L0_SUGGESTIONS = "l0"
    L1_DRAFTS = "l1"
    L2_SUPERVISED = "l2"
    L3_AUTONOMOUS = "l3"

class UserPreference(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "user_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True
    )

    # --- Job Type Preferences (relational, frequently queried) ---
    job_categories = Column(ARRAY(Text), default=[])      # ["engineering", "product"]
    target_titles = Column(ARRAY(Text), default=[])        # ["Senior Software Engineer"]
    seniority_levels = Column(ARRAY(Text), default=[])     # ["senior", "staff"]

    # --- Location (relational) ---
    work_arrangement = Column(
        Enum(WorkArrangement, name="work_arrangement", create_type=False),
        nullable=True
    )
    target_locations = Column(ARRAY(Text), default=[])     # ["San Francisco, CA", "New York, NY"]
    excluded_locations = Column(ARRAY(Text), default=[])   # ["Los Angeles, CA"]
    willing_to_relocate = Column(Boolean, default=False)

    # --- Salary (relational, sensitive) ---
    salary_minimum = Column(Integer, nullable=True)        # USD, annual
    salary_target = Column(Integer, nullable=True)
    salary_flexibility = Column(Text, nullable=True)       # "firm" | "negotiable"
    comp_preference = Column(Text, nullable=True)          # "base_only" | "total_comp"

    # --- Deal-Breakers (relational for efficient filtering) ---
    min_company_size = Column(Integer, nullable=True)
    excluded_companies = Column(ARRAY(Text), default=[])
    excluded_industries = Column(ARRAY(Text), default=[])
    must_have_benefits = Column(ARRAY(Text), default=[])   # ["401k_match", "unlimited_pto"]
    max_travel_percent = Column(Integer, nullable=True)
    no_oncall = Column(Boolean, default=False)

    # --- H1B / Visa ---
    requires_h1b_sponsorship = Column(Boolean, default=False)
    requires_greencard_sponsorship = Column(Boolean, default=False)
    current_visa_type = Column(Text, nullable=True)
    visa_expiration = Column(DateTime(timezone=True), nullable=True)

    # --- Autonomy ---
    autonomy_level = Column(
        Enum(AutonomyLevel, name="autonomy_level", create_type=False),
        nullable=False,
        default=AutonomyLevel.L0_SUGGESTIONS,
    )

    # --- Flexible Extras (JSONB for evolving preferences) ---
    extra_preferences = Column(JSONB, default={})
    # e.g. {"preferred_industries": ["fintech", "healthtech"],
    #        "preferred_company_stage": "series_b_plus",
    #        "hybrid_days_per_week": 3}

    # Relationships
    user = relationship("User", backref="preferences")
```

### Pattern 4: Onboarding State Tracking

**What:** Track onboarding progress server-side so the app can redirect incomplete users.

**When to use:** Every authenticated route should check onboarding status.

**Example:**
```python
# Add to User model or create separate table
class User(TimestampMixin, Base):
    # ... existing fields ...
    onboarding_status = Column(
        Enum(OnboardingStatus, name="onboarding_status", create_type=False),
        nullable=False,
        default=OnboardingStatus.NOT_STARTED,
    )
    onboarding_started_at = Column(DateTime(timezone=True), nullable=True)
    onboarding_completed_at = Column(DateTime(timezone=True), nullable=True)
```

```typescript
// Frontend: redirect to onboarding if not complete
// frontend/src/hooks/useOnboardingGuard.ts
import { useUser } from '@clerk/clerk-react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useEffect } from 'react';

export function useOnboardingGuard() {
  const { user } = useUser();
  const navigate = useNavigate();

  const { data: profile } = useQuery({
    queryKey: ['user-profile', user?.id],
    queryFn: () => fetchProfile(),
    enabled: !!user,
  });

  useEffect(() => {
    if (profile && profile.onboarding_status !== 'complete') {
      navigate('/onboarding');
    }
  }, [profile, navigate]);
}
```

### Anti-Patterns to Avoid

- **Storing all preferences in a single JSONB blob:** Prevents efficient querying by the Job Scout Agent. Deal-breakers need dedicated columns with proper indexes.
- **Blocking onboarding on LinkedIn URL extraction:** LinkedIn fetch is unreliable (rate limits, blocks). Always offer resume upload as equal-prominence alternative.
- **Making every preference field required:** Users abandon long required forms. Only `name` and at least one work experience should be truly required. Use empty states for skipped preferences (Story 2-8).
- **Calling the LLM on every profile edit:** Only call the LLM once during initial extraction. Subsequent edits are user-driven and go directly to the database.
- **Using LangChain for simple extraction:** The OpenAI SDK has native Pydantic structured output support. Adding LangChain for this simple use case introduces unnecessary complexity.

---

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF text extraction | Custom PDF parser | PyPDF2 (already installed) | Handles 95%+ of resume PDFs; edge cases (scanned/image PDFs) need OCR which is a separate concern |
| DOCX text extraction | Custom XML parser | python-docx (already installed) | Handles all standard DOCX files |
| Structured data from unstructured text | Regex/rule-based parser | OpenAI structured outputs (GPT-4o-mini) | LLM handles layout variations, abbreviations, diverse formats that rules cannot |
| Form state management | Custom form state | react-hook-form (already installed) | Handles validation, dirty tracking, controlled/uncontrolled inputs |
| Validation schemas | Custom validators | Zod (already installed) | Type-safe, composable, integrates with react-hook-form via @hookform/resolvers |
| File upload UI | Custom drag-and-drop | react-dropzone (already installed) | Handles drag, click, keyboard, ARIA, file type filtering |
| Auth-gated routes | Custom auth check | Clerk SignedIn/SignedOut (already installed) | Already working in the codebase |
| Analytics funnel tracking | Custom event system | PostHog (recommended) | Funnels, retention, feature flags built in; self-hostable for GDPR |

**Key insight:** Phase 1 installed most of the needed libraries. Phase 2 is primarily about writing application code with the existing stack, plus adding OpenAI structured outputs for LLM extraction and PostHog for analytics.

---

## Common Pitfalls

### Pitfall 1: Image-Based PDFs Fail Silently

**What goes wrong:** PyPDF2 returns empty string for scanned/image-based PDFs. The LLM receives no text and returns empty or hallucinated data.

**Why it happens:** ~10-15% of resumes are scanned images or have image-based layouts that PyPDF2 cannot extract text from.

**How to avoid:** Check if extracted text length is below a threshold (e.g., <50 characters for a multi-page PDF). If so, return a clear error: "This file appears to be image-based. Please upload a text-based PDF or DOCX file." Do NOT attempt OCR in Phase 2 -- that is a separate complexity to add later.

**Warning signs:** `extract_text()` returns empty or very short strings for multi-page documents.

### Pitfall 2: LLM Hallucinating Resume Data

**What goes wrong:** The LLM adds skills, companies, or titles that are not in the resume.

**Why it happens:** LLMs are trained on many resumes and may "complete" partial information based on patterns.

**How to avoid:** Use explicit system prompt instructions: "Only include information explicitly present in the resume text. Do not infer or fabricate any details." The Profile Review UI (Story 1-3) is the critical safety net -- users MUST review and confirm before data is saved.

**Warning signs:** Skills appear that are common for the role type but not mentioned in the resume text.

### Pitfall 3: Onboarding Abandonment Due to Length

**What goes wrong:** Users drop off during a long onboarding flow (8+ steps combined).

**Why it happens:** The combined onboarding (3 steps) + preferences (7 steps) = 10 steps feels like too much.

**How to avoid:**
1. Make the preference wizard skippable with good defaults (Story 2-8 empty states).
2. Show a progress indicator with step count.
3. Let users save progress and return later (Zustand persist middleware handles this).
4. The briefing preview (Story 1-4) creates a "magic moment" BEFORE preferences, motivating completion.
5. Target: complete onboarding in <2 minutes, preferences in <3 minutes.

**Warning signs:** Analytics show >30% drop-off between onboarding start and preference completion.

### Pitfall 4: LinkedIn URL Extraction Fails Frequently

**What goes wrong:** LinkedIn blocks or rate-limits profile page fetches, leaving users stuck.

**Why it happens:** LinkedIn actively detects and blocks automated profile fetches (see DOMAIN_CONCERNS.md Section 5).

**How to avoid:** Per roadmap guidance -- resume upload is PRIMARY, LinkedIn URL is secondary. Design the UI to prominently show the upload option. If LinkedIn fetch fails, immediately show: "We couldn't access that profile. Try uploading your resume instead." Never make the user wait more than 15 seconds for a LinkedIn fetch before offering the fallback.

**Warning signs:** LinkedIn extraction success rate drops below 50%.

### Pitfall 5: Clerk User Sync Race Condition

**What goes wrong:** User signs up via Clerk, frontend redirects to onboarding, but the backend `users` record does not exist yet.

**Why it happens:** Clerk creates the user on their side, but the JobPilot backend creates the `users` row on first API call. If the onboarding page makes an API call before the user record is created, it fails.

**How to avoid:** Use an "ensure user exists" pattern: the first authenticated API call checks if a `users` row exists for the Clerk user ID. If not, create it. This should be a reusable dependency/middleware.

```python
async def ensure_user_exists(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await db.get(User, user_id)
    if not user:
        # Auto-create from Clerk data
        user = User(clerk_id=user_id, email="pending@setup.com")
        db.add(user)
        await db.commit()
    return user
```

### Pitfall 6: Preference Schema Too Rigid

**What goes wrong:** New preference types require database migrations every time.

**Why it happens:** Storing ALL preferences as relational columns means every new preference is a schema change.

**How to avoid:** The hybrid approach: relational columns for frequently-queried fields (deal-breakers, salary, location) and JSONB `extra_preferences` for evolving/optional fields. New preference types go into JSONB first, and get promoted to dedicated columns only when they need indexes or constraints.

---

## Code Examples

### Resume Upload API Endpoint

```python
# backend/app/api/v1/onboarding.py
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.auth.clerk import get_current_user_id
from app.services.storage_service import upload_file
from app.services.resume_parser import extract_profile_from_resume

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

@router.post("/resume/upload")
async def upload_and_parse_resume(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
):
    """Upload resume, store in Supabase, extract profile with LLM."""
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    file_bytes = await file.read()

    # 1. Store file in Supabase Storage (existing service)
    storage_path = await upload_file(
        user_id=user_id,
        file_bytes=file_bytes,
        filename=file.filename,
        content_type=file.content_type,
    )

    # 2. Extract structured profile via LLM
    try:
        profile = await extract_profile_from_resume(file_bytes, file.filename)
    except ValueError as e:
        raise HTTPException(422, str(e))

    # 3. Return extracted data for user review (NOT saved to DB yet)
    return {
        "storage_path": storage_path,
        "extracted_profile": profile.model_dump(),
        "field_count": sum(1 for v in profile.model_dump().values() if v),
    }
```

### Profile Confirmation Endpoint

```python
@router.put("/profile/confirm")
async def confirm_profile(
    profile_data: ProfileConfirmRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Save user-confirmed profile data to database."""
    profile = await db.execute(
        select(Profile).where(Profile.user_id == user_id)
    )
    existing = profile.scalar_one_or_none()

    if existing:
        existing.skills = profile_data.skills
        existing.experience = [exp.model_dump() for exp in profile_data.experience]
        existing.education = [edu.model_dump() for edu in profile_data.education]
        existing.linkedin_data = profile_data.linkedin_data
    else:
        new_profile = Profile(
            user_id=user_id,
            skills=profile_data.skills,
            experience=[exp.model_dump() for exp in profile_data.experience],
            education=[edu.model_dump() for edu in profile_data.education],
            linkedin_data=profile_data.linkedin_data,
        )
        db.add(new_profile)

    # Update onboarding status
    user = await db.get(User, user_id)
    user.onboarding_status = OnboardingStatus.PROFILE_COMPLETE
    await db.commit()

    return {"status": "confirmed"}
```

### Analytics Event Tracking

```python
# backend/app/services/analytics_service.py
import posthog
from app.config import settings

posthog.project_api_key = settings.POSTHOG_API_KEY  # Add to config
posthog.host = settings.POSTHOG_HOST  # Add to config

def track_event(user_id: str, event: str, properties: dict | None = None):
    """Track an analytics event. Fire-and-forget."""
    try:
        posthog.capture(
            distinct_id=user_id,
            event=event,
            properties=properties or {},
        )
    except Exception:
        pass  # Analytics should never break user flow
```

```typescript
// frontend/src/hooks/useAnalytics.ts
import posthog from 'posthog-js';

// Initialize once in main.tsx:
// posthog.init(POSTHOG_KEY, { api_host: POSTHOG_HOST })

export function useAnalytics() {
  return {
    track: (event: string, properties?: Record<string, unknown>) => {
      posthog.capture(event, properties);
    },
  };
}

// Onboarding events (Story 1-6):
// onboarding_started        { source: 'resume' | 'linkedin' }
// profile_extraction_started { source: 'resume' | 'linkedin' }
// profile_extraction_completed { field_count, duration_ms, source }
// profile_extraction_failed  { error, source }
// profile_confirmed          { fields_edited_count }
// briefing_preview_viewed    {}
// preference_step_completed  { step_name, step_number }
// preference_step_skipped    { step_name, step_number }
// preferences_confirmed      { autonomy_level, has_dealbreakers, has_h1b }
// onboarding_completed       { total_duration_ms, source }
// onboarding_abandoned       { last_step, duration_ms }
```

### Briefing Preview (Magic Moment)

```typescript
// frontend/src/components/onboarding/BriefingPreview.tsx
// Story 1-4: Show a preview of what daily briefings look like

interface BriefingPreviewProps {
  userName: string;
  onContinue: () => void;
}

// Use mock data for the preview - real briefings come in Phase 3
const MOCK_BRIEFING = {
  greeting: "Good morning",
  matchCount: 3,
  matches: [
    {
      title: "Senior Software Engineer",
      company: "Acme Corp",
      score: 92,
      location: "Remote",
      salary: "$180K - $220K",
    },
    {
      title: "Staff Engineer",
      company: "TechStart Inc",
      score: 87,
      location: "San Francisco, CA",
      salary: "$200K - $250K",
    },
    {
      title: "Senior Backend Developer",
      company: "DataFlow",
      score: 84,
      location: "Hybrid - NYC",
      salary: "$170K - $210K",
    },
  ],
};
```

**Decision: Use mock data for briefing preview (Story 1-4).** Real LLM-generated briefings require the Job Scout Agent (Phase 4). The preview is a UX tool to show value, not a functional feature. Use hardcoded but personalized mock data (user's name in greeting, placeholder matches relevant to their selected job titles).

---

## Schema Changes Required

### New Tables

1. **`user_preferences`** -- Stores all job preferences and deal-breakers (see Pattern 3 above)

### Modified Tables

1. **`users`** -- Add columns:
   - `onboarding_status` (enum: not_started, profile_pending, profile_complete, preferences_pending, complete)
   - `onboarding_started_at` (timestamp)
   - `onboarding_completed_at` (timestamp)
   - `display_name` (text) -- extracted from resume or entered manually

2. **`profiles`** -- Add columns:
   - `headline` (text) -- professional headline/summary
   - `phone` (text, nullable) -- contact info from resume
   - `resume_storage_path` (text, nullable) -- Supabase Storage path to original resume
   - `extraction_source` (text) -- 'resume' | 'linkedin' | 'manual'
   - `extraction_confidence` (numeric) -- LLM confidence score

### Alembic Migration

```python
# One migration for all Phase 2 schema changes
# backend/alembic/versions/xxxx_phase2_onboarding_preferences.py

def upgrade():
    # 1. Add onboarding columns to users
    op.add_column('users', sa.Column('onboarding_status', sa.Text(), server_default='not_started'))
    op.add_column('users', sa.Column('onboarding_started_at', sa.DateTime(timezone=True)))
    op.add_column('users', sa.Column('onboarding_completed_at', sa.DateTime(timezone=True)))
    op.add_column('users', sa.Column('display_name', sa.Text()))

    # 2. Add profile columns
    op.add_column('profiles', sa.Column('headline', sa.Text()))
    op.add_column('profiles', sa.Column('phone', sa.Text()))
    op.add_column('profiles', sa.Column('resume_storage_path', sa.Text()))
    op.add_column('profiles', sa.Column('extraction_source', sa.Text()))
    op.add_column('profiles', sa.Column('extraction_confidence', sa.Numeric(3, 2)))

    # 3. Create user_preferences table
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True),
        sa.Column('job_categories', sa.ARRAY(sa.Text()), server_default='{}'),
        sa.Column('target_titles', sa.ARRAY(sa.Text()), server_default='{}'),
        sa.Column('seniority_levels', sa.ARRAY(sa.Text()), server_default='{}'),
        sa.Column('work_arrangement', sa.Text()),
        sa.Column('target_locations', sa.ARRAY(sa.Text()), server_default='{}'),
        sa.Column('excluded_locations', sa.ARRAY(sa.Text()), server_default='{}'),
        sa.Column('willing_to_relocate', sa.Boolean(), server_default='false'),
        sa.Column('salary_minimum', sa.Integer()),
        sa.Column('salary_target', sa.Integer()),
        sa.Column('salary_flexibility', sa.Text()),
        sa.Column('comp_preference', sa.Text()),
        sa.Column('min_company_size', sa.Integer()),
        sa.Column('excluded_companies', sa.ARRAY(sa.Text()), server_default='{}'),
        sa.Column('excluded_industries', sa.ARRAY(sa.Text()), server_default='{}'),
        sa.Column('must_have_benefits', sa.ARRAY(sa.Text()), server_default='{}'),
        sa.Column('max_travel_percent', sa.Integer()),
        sa.Column('no_oncall', sa.Boolean(), server_default='false'),
        sa.Column('requires_h1b_sponsorship', sa.Boolean(), server_default='false'),
        sa.Column('requires_greencard_sponsorship', sa.Boolean(), server_default='false'),
        sa.Column('current_visa_type', sa.Text()),
        sa.Column('visa_expiration', sa.DateTime(timezone=True)),
        sa.Column('autonomy_level', sa.Text(), server_default='l0'),
        sa.Column('extra_preferences', sa.dialects.postgresql.JSONB(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        sa.Column('deleted_by', sa.UUID()),
        sa.Column('deletion_reason', sa.Text()),
    )

    # 4. Create indexes for agent querying
    op.create_index('ix_prefs_user_id', 'user_preferences', ['user_id'])
    op.create_index('ix_prefs_h1b', 'user_preferences', ['requires_h1b_sponsorship'])
    op.create_index('ix_prefs_autonomy', 'user_preferences', ['autonomy_level'])
```

---

## LinkedIn URL Extraction (Secondary Path)

**Confidence: MEDIUM** -- LinkedIn actively blocks scraping, this path WILL be unreliable.

### Realistic Implementation

Per DOMAIN_CONCERNS.md and ROADMAP.md, LinkedIn URL extraction is **secondary/fallback**, not primary.

**Approach (in order of preference):**

1. **LinkedIn Data Export (GDPR download):** Guide users to download their own data from LinkedIn Settings > Get a copy of your data. Parse the resulting CSV/JSON files. This is the most reliable approach but requires user effort.

2. **Public Profile Fetch (with caveats):** Fetch the public profile page via httpx, parse with BeautifulSoup. This is fragile -- LinkedIn changes their HTML frequently and blocks automated access.

3. **Accept failure gracefully:** If LinkedIn extraction fails (which it will ~50% of the time), immediately redirect to resume upload.

**Implementation:**
```python
# backend/app/services/linkedin_extractor.py
import httpx
from bs4 import BeautifulSoup

async def extract_from_linkedin_url(url: str) -> ExtractedProfile | None:
    """
    Attempt to extract profile from public LinkedIn URL.
    Returns None on failure -- caller should fall back to resume upload.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; JobPilot/1.0)"
            })
            if resp.status_code != 200:
                return None

        soup = BeautifulSoup(resp.text, "html.parser")
        # Parse structured data from meta tags (more stable than HTML)
        # LinkedIn includes JSON-LD structured data on public profiles
        # ... parsing logic ...
        # If parsing yields meaningful data, send to LLM for structuring
        # Otherwise return None

    except Exception:
        return None
```

**Key design decision:** The LinkedIn extraction endpoint should return partial data or `null`. The frontend should ALWAYS show the resume upload option alongside LinkedIn, and handle LinkedIn failure by promoting the upload option.

---

## Clerk Auth Integration for Onboarding

**Confidence: HIGH** -- existing codebase already has working Clerk integration.

### How Onboarding Fits

The existing flow is:
1. User visits site -> sees LandingPage
2. User clicks Sign In -> Clerk handles OAuth (LinkedIn, Google, email)
3. Clerk redirects to `/dashboard` (existing protected route)

Phase 2 changes this to:
1. Same sign-in flow via Clerk
2. After first sign-in, check `onboarding_status` on the backend
3. If `not_started` -> redirect to `/onboarding`
4. If `complete` -> show dashboard
5. If intermediate state -> resume from where they left off

### Implementation Notes

- **Clerk metadata:** Store `onboarding_completed: true` in Clerk user metadata for fast client-side checks before API call completes.
- **Clerk webhook:** Use Clerk's `user.created` webhook to auto-create the `users` row in the database, avoiding the race condition described in Pitfall 5.
- **Session claims:** Add `onboarding_status` as a custom session claim in Clerk for instant frontend access.

```typescript
// frontend/src/providers/OnboardingGuard.tsx
import { useUser } from '@clerk/clerk-react';
import { Navigate, useLocation } from 'react-router-dom';

export function OnboardingGuard({ children }: { children: React.ReactNode }) {
  const { user } = useUser();
  const location = useLocation();

  // Skip guard for onboarding pages themselves
  if (location.pathname.startsWith('/onboarding')) return <>{children}</>;

  // Check Clerk metadata first (fast, no API call)
  const onboardingComplete = user?.publicMetadata?.onboarding_completed;
  if (!onboardingComplete) {
    return <Navigate to="/onboarding" replace />;
  }

  return <>{children}</>;
}
```

---

## Analytics Events (Story 1-6)

**Confidence: HIGH** -- standard funnel tracking pattern.

### Recommended Events

| Event Name | Trigger | Properties |
|-----------|---------|------------|
| `onboarding_started` | User lands on onboarding page | `source: 'organic' \| 'invite'` |
| `profile_extraction_method_chosen` | User chooses resume or LinkedIn | `method: 'resume' \| 'linkedin'` |
| `resume_uploaded` | File upload completes | `file_type, file_size_kb` |
| `profile_extraction_completed` | LLM extraction returns | `field_count, duration_ms, source` |
| `profile_extraction_failed` | Extraction error | `error_type, source` |
| `profile_review_started` | User sees review screen | `field_count` |
| `profile_confirmed` | User clicks confirm | `fields_edited_count, total_fields` |
| `briefing_preview_viewed` | User sees magic moment | `duration_ms` |
| `preference_wizard_started` | User starts preferences | `{}` |
| `preference_step_completed` | Step form submitted | `step_name, step_number` |
| `preference_step_skipped` | Step explicitly skipped | `step_name, step_number` |
| `preferences_confirmed` | Final confirmation | `autonomy_level, has_dealbreakers, has_h1b, steps_completed, steps_skipped` |
| `onboarding_completed` | Full flow done | `total_duration_ms, extraction_source, steps_completed` |
| `onboarding_abandoned` | 5-min inactivity or close | `last_step, duration_ms` |

### Tool Recommendation: PostHog

PostHog is recommended over Mixpanel for this project because:
1. **Self-hostable** -- GDPR compliance without third-party data sharing
2. **Open source** -- No vendor lock-in
3. **Feature flags** -- Useful for rolling out onboarding improvements
4. **Session replay** -- Debug onboarding drop-offs visually
5. **Free tier** -- 1M events/month free, sufficient for early stage

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Rule-based resume parsing (regex) | LLM structured outputs | 2024-2025 | 95%+ extraction accuracy vs ~70% for rules |
| LangChain PydanticOutputParser | OpenAI native `response_format` | 2024 (GPT-4o) | No LangChain dependency needed for extraction |
| GPT-3.5 for extraction (~$0.002) | GPT-4o-mini (~$0.0005) | July 2024 | 4x cheaper AND better accuracy |
| Custom form libraries | react-hook-form + Zod | 2023+ | Industry standard, type-safe validation |
| Mixpanel/Amplitude (SaaS-only) | PostHog (self-hostable) | 2023+ | GDPR-compliant analytics with full data ownership |

**Deprecated/outdated:**
- `langchain 0.0.340`: Dead. Do not use for new features. Use OpenAI SDK directly.
- Rule-based resume parsers (e.g., `pyresparser`): Far less accurate than LLM extraction.
- `create-react-app`: Already removed in Phase 1.

---

## Open Questions

Things that could not be fully resolved:

1. **PostHog vs simpler analytics**
   - What we know: PostHog is the best open-source option with self-hosting
   - What's unclear: Whether the team wants to self-host or use PostHog Cloud
   - Recommendation: Start with PostHog Cloud (free tier), migrate to self-hosted later if GDPR requires it

2. **LinkedIn Data Export parsing format**
   - What we know: LinkedIn GDPR export includes CSVs with profile data
   - What's unclear: Exact CSV schema and how it maps to our `ExtractedProfile` model
   - Recommendation: Build this as a v2 feature after the main resume upload path works

3. **Onboarding + Preferences: One flow or two?**
   - What we know: Epics 1 and 2 are separate, but the user experience should feel like one continuous flow
   - What's unclear: Whether to combine into one wizard or have a clear break with "Continue to Preferences" CTA
   - Recommendation: One continuous wizard with a clear visual break (briefing preview acts as the divider between profile setup and preference configuration)

4. **OCR for image-based PDFs**
   - What we know: ~10-15% of resumes may be image-based
   - What's unclear: Whether to add OCR (Tesseract/pytesseract) in Phase 2 or defer
   - Recommendation: Defer OCR to a later enhancement. Show clear error message and suggest DOCX upload instead.

---

## Sources

### Primary (HIGH confidence)
- OpenAI Structured Outputs documentation - https://platform.openai.com/docs/guides/structured-outputs
- GPT-4o mini pricing - https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/
- Existing codebase: `backend/app/db/models.py`, `backend/app/services/storage_service.py`, `backend/app/auth/clerk.py`
- BMAD Epics (Stories 1-1 through 2-8) - `_bmad-output/planning-artifacts/epics.md`
- Phase 1 ROADMAP - `.planning/ROADMAP.md`

### Secondary (MEDIUM confidence)
- [Building a reusable multi-step form with React Hook Form and Zod](https://blog.logrocket.com/building-reusable-multi-step-form-react-hook-form-zod/)
- [Building a Resume Parser with LLMs](https://medium.com/@gk0415439/building-a-resume-parser-with-llms-a-step-by-step-guide-part-i-03682a68bc8b)
- [Structured outputs with OpenAI and Instructor](https://python.useinstructor.com/integrations/openai/)
- [PostgreSQL JSONB Best Practices](https://aws.amazon.com/blogs/database/postgresql-as-a-json-database-advanced-patterns-and-best-practices/)
- [PostHog vs Mixpanel](https://posthog.com/blog/posthog-vs-mixpanel)

### Tertiary (LOW confidence)
- LinkedIn public profile scraping reliability estimates - based on DOMAIN_CONCERNS.md research and general industry knowledge

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All core libraries already installed in Phase 1; OpenAI structured outputs are well-documented
- Architecture: HIGH - Patterns are standard React + FastAPI; schema design follows PostgreSQL best practices
- Resume extraction: HIGH - OpenAI structured outputs with Pydantic are production-proven
- LinkedIn extraction: LOW - Unreliable by design; documented as secondary path
- Analytics: MEDIUM - PostHog recommendation based on web search; exact integration needs validation
- Pitfalls: HIGH - Based on codebase analysis and established industry patterns

**Research date:** 2026-01-31
**Valid until:** 2026-03-31 (90 days -- this domain is stable; main risk is OpenAI API changes)
