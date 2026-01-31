# Roadmap: JobPilot

## Overview

JobPilot transforms a cold-email-generator codebase into an AI-powered multi-agent job search platform with tiered autonomy (L0-L3), daily briefings, resume tailoring, pipeline tracking, and H1B sponsorship intelligence. The roadmap progresses from foundation modernization through agent framework, then individual agents ordered by ascending complexity, with the MVP boundary at Phase 6. Each phase delivers a coherent, verifiable capability that unblocks the next.

**Source Material:** 11 BMAD Epics (0-10), 114 Stories, 4 research streams
**Current State:** Story 0-1 (Database Schema Foundation) in review. CRA frontend, outdated deps, no auth/CI/CD.

## Milestones

- **MVP** - Phases 1-6 (Foundation through Pipeline Tracking)
- **Growth** - Phases 7-8 (H1B Intelligence, Auto-Apply)
- **Vision** - Phase 9 (Advanced Features + Production Hardening)

## Phases

- [ ] **Phase 1: Foundation Modernization** - Modern stack, auth, infra, CI/CD
- [ ] **Phase 2: Onboarding + Preferences** - User signup through preference configuration
- [ ] **Phase 3: Agent Framework Core** - Orchestrator, emergency brake, briefing pipeline
- [ ] **Phase 4: Job Scout Agent** - Job matching, daily briefings, swipe UI
- [ ] **Phase 5: Resume Agent + ATS** - Resume tailoring, diff view, ATS optimization
- [ ] **Phase 6: Pipeline Tracking** - Application tracking, email forwarding, kanban board
- [ ] **Phase 7: H1B Sponsorship Intelligence** - Government data ETL, sponsor scores, badges
- [ ] **Phase 8: Apply Agent + Approval Queue** - Auto-apply, cover letters, approval workflow
- [ ] **Phase 9: Advanced Features + Hardening** - Follow-up agent, stealth mode, network assistant, production ops

---

## Phase Details

### Phase 1: Foundation Modernization

**Goal**: Developers have a modern, buildable codebase with auth, background jobs, CI/CD, and resolved database architecture -- enabling all subsequent feature work.

**Depends on**: Nothing (first phase). Story 0-1 already in review.

**BMAD Stories**:
- Story 0-1: Database Schema Foundation (IN REVIEW)
- Story 0-2: Row-Level Security Policies
- Story 0-3: Clerk Authentication Integration
- Story 0-4: API Foundation with Versioning
- Story 0-5: Redis Cache and Queue Setup
- Story 0-6: Celery Worker Infrastructure
- Story 0-7: OpenTelemetry Tracing Setup
- Story 0-8: LLM Cost Tracking Middleware
- Story 0-9: Error Tracking Integration
- Story 0-10: WebSocket Infrastructure
- Story 0-11: Email Service Configuration
- Story 0-12: CI/CD Pipeline with Automated Tests
- Story 0-13: Supabase Storage Configuration
- Story 0-14: Performance Baseline Establishment
- Story 0-15: GDPR Data Portability Endpoints

**Additional Work (from research, not in BMAD stories)**:
- CRA-to-Vite migration (CRA is deprecated, no security patches)
- TypeScript adoption for frontend (mandatory per architecture)
- OpenAI SDK v1->v2 upgrade (breaking API changes)
- Remove langchain 0.0.340 (pre-1.0, dead)
- Resolve dual database abstraction: SQLAlchemy for ALL app data, Supabase SDK for auth/storage/realtime ONLY
- Python dependency modernization (FastAPI >=0.115.0, etc.)

**Success Criteria** (what must be TRUE):
1. Running `npm run dev` starts a Vite+React+TypeScript frontend that connects to the FastAPI backend
2. A user can sign up and log in via Clerk (LinkedIn OAuth) and see a protected dashboard page
3. A Celery worker can pick up a task from Redis, execute it, and record the result in PostgreSQL via SQLAlchemy
4. Pushing to main triggers a GitHub Actions CI pipeline that runs backend tests, frontend tests, and blocks on failure
5. The OpenTelemetry + Sentry stack captures a traced API request end-to-end and surfaces it in the observability backend

**Plans**: 8 plans in 4 waves
Plans:
- [ ] Plan 01 -- Backend Dependency Modernization (Wave 1)
- [ ] Plan 02 -- CRA-to-Vite + TypeScript Migration (Wave 1)
- [ ] Plan 03 -- Database Layer Resolution (Wave 2)
- [ ] Plan 04 -- API Foundation + Clerk Auth Backend (Wave 2)
- [ ] Plan 05 -- Celery + Redis Worker Infrastructure (Wave 3)
- [ ] Plan 06 -- Frontend Auth (Clerk React) + Protected Routes (Wave 3)
- [ ] Plan 07 -- Observability Stack (OTel + Sentry + Cost Tracking) (Wave 4)
- [ ] Plan 08 -- CI/CD Pipeline + Remaining Infrastructure (Wave 4)

**ADRs Resolved**:
- ADR-2: Database Access Pattern (SQLAlchemy primary, Supabase SDK for auth/storage/realtime only) -- documented in Plan 03
- ADR-6: Email service choice -- Resend (better DX, free tier sufficient) -- implemented in Plan 08

**Risks**:
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| CRA->Vite migration breaks existing frontend patterns | Medium | Medium | Vite has CRA migration guide; test thoroughly |
| Supabase + asyncpg DuplicatePreparedStatementError under load | Low | High | Use statement_cache_size=0 in connection string; test under burst |
| Clerk + FastAPI integration gaps | Low | Medium | fastapi-clerk-auth library exists; fallback to manual JWT validation |

**Key Notes**:
- Start Google OAuth app registration NOW (2-6 week verification lead time, needed for Phase 6)
- Start LinkedIn Partner API exploration (long lead time, may not be needed for MVP)
- This phase is estimated at 1-2 weeks per research

---

### Phase 2: Onboarding + Preferences

**Goal**: A new user can sign up, have their profile extracted from a resume upload (or LinkedIn data export), configure job preferences and deal-breakers, and be ready for agent activation.

**Depends on**: Phase 1

**BMAD Stories**:
- Story 1-1: LinkedIn URL Profile Extraction
- Story 1-2: Resume File Upload and Parsing
- Story 1-3: Profile Review and Correction UI
- Story 1-4: First Briefing Preview (Magic Moment)
- Story 1-5: Onboarding Empty State
- Story 1-6: Onboarding Analytics Events
- Story 2-1: Job Type and Title Preferences
- Story 2-2: Location and Remote Work Settings
- Story 2-3: Salary Range Configuration
- Story 2-4: Deal-Breaker Definition
- Story 2-5: H1B Sponsorship Requirement
- Story 2-6: Autonomy Level Selection
- Story 2-7: Preference Summary and Confirmation
- Story 2-8: Preference Empty States

**Research Adjustments**:
- Resume upload is PRIMARY onboarding path (not LinkedIn URL). LinkedIn URL extraction is secondary/fallback.
- LinkedIn data export (GDPR download) as tertiary path. Do NOT depend on LinkedIn scraping for core onboarding.
- Story 1-1 should use LinkedIn public data cautiously -- implement with clear failure handling and fallback to manual entry.

**Success Criteria** (what must be TRUE):
1. A new user can upload a PDF/DOCX resume and see their profile auto-populated with name, experience, skills, and education within 60 seconds
2. A user can complete the preference wizard (job type, location, salary, deal-breakers, autonomy level) in under 5 minutes
3. A user sees a first briefing preview ("magic moment") before finishing onboarding that shows what daily briefings will look like
4. Deal-breakers are stored and enforceable -- querying a user's preferences returns structured data including must-haves and never-haves

**Plans**: 6 plans in 4 waves
Plans:
- [ ] Plan 01 -- Database Schema + Backend Models (Wave 1)
- [ ] Plan 02 -- Analytics Infrastructure - PostHog (Wave 1)
- [ ] Plan 03 -- Resume Upload + Profile Extraction Backend (Wave 2)
- [ ] Plan 04 -- Preferences Backend + Shared Frontend Components (Wave 2)
- [ ] Plan 05 -- Onboarding Frontend Flow (Wave 3)
- [ ] Plan 06 -- Preference Wizard Frontend + Integration Wiring (Wave 4)

**Risks**:
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LinkedIn URL extraction blocked/unreliable | High | Medium | Resume upload is primary path; LinkedIn URL is secondary with graceful failure |
| Profile extraction accuracy below 95% target | Medium | Medium | LLM-powered extraction with user correction UI; track accuracy metrics from day 1 |

---

### Phase 3: Agent Framework Core

**Goal**: The agent orchestration infrastructure is operational -- orchestrator routes tasks, autonomy tiers are enforced, the emergency brake works, daily briefings are generated and delivered, and real-time activity is visible via WebSocket.

**Depends on**: Phase 2

**BMAD Stories**:
- Story 3-1: Orchestrator Agent Infrastructure
- Story 3-2: Daily Briefing Generation Pipeline
- Story 3-3: Briefing Delivery - In-App
- Story 3-4: Briefing Delivery - Email
- Story 3-5: User-Configurable Briefing Time
- Story 3-6: Emergency Brake Button
- Story 3-7: Emergency Brake State Machine
- Story 3-8: Resume Agents After Pause
- Story 3-9: Agent Activity Feed
- Story 3-10: Briefing Empty State
- Story 3-11: Briefing Reliability Fallback

**Research Adjustments**:
- Must resolve ADR-1 (LangGraph vs. custom orchestrator) at the START of this phase via a 2-day time-boxed prototype
- BaseAgent class must include: brake check at every step, tier enforcement as decorator, cost tracking per call, structured output (action, rationale, confidence, alternatives)
- Approval queue schema must be created here (missing from current schema) even if not used until Phase 8
- **Replace custom `cost_tracker.py` with Langfuse** for LLM observability. Langfuse provides per-call cost/latency/token tracking, multi-step agent trace visualization, and built-in evaluation scoring -- all of which the custom Redis solution would need to be extended to support. Use `@observe()` decorator on agent methods. Self-host for GDPR compliance. Keep OpenTelemetry for HTTP/Celery tracing and Sentry for error tracking.

**Success Criteria** (what must be TRUE):
1. The emergency brake button is visible on every page, and pressing it pauses all agent activity for that user within 30 seconds
2. A daily briefing is generated at the user's configured time and delivered both in-app and via email within 15 minutes
3. The agent activity feed shows real-time updates via WebSocket when agents are running
4. Autonomy level (L0-L3) is enforced -- an L0 user's agents only suggest, an L2 user's agents act but surface in approval digest, and this is verifiable via test
5. If the briefing pipeline fails, a "lite briefing" from cache is shown instead of an error

**Plans**: 6 plans in 4 waves
Plans:
- [ ] Plan 01 -- Database Schema + Backend Models (Wave 1)
- [ ] Plan 02 -- Analytics Infrastructure - PostHog (Wave 1)
- [ ] Plan 03 -- Resume Upload + Profile Extraction Backend (Wave 2)
- [ ] Plan 04 -- Preferences Backend + Shared Frontend Components (Wave 2)
- [ ] Plan 05 -- Onboarding Frontend Flow (Wave 3)
- [ ] Plan 06 -- Preference Wizard Frontend + Integration Wiring (Wave 4)

**ADRs to Resolve**:
- ADR-1: Agent Orchestration Framework (LangGraph vs. custom) -- resolve with 2-day prototype before committing
- LLM mock strategy for deterministic agent testing (VCR-style recorded responses vs. templated vs. low-temp actual LLM)

**Risks**:
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LangGraph 1.0 too immature for production autonomy patterns | Medium | High | Time-boxed prototype; if it doesn't map cleanly to L0-L3, go custom |
| Orchestrator becomes god object | Medium | High | Split into TaskRouter + StateManager + TierEnforcer from day 1 |
| WebSocket scaling issues at load | Low | Medium | Redis Pub/Sub as message bus; REST fallback for missed events |

---

### Phase 4: Job Scout Agent (First Agent)

**Goal**: Users wake up to AI-curated job matches with scores, rationale, and a swipe-to-review interface. This is the first agent proving the end-to-end pipeline: API fetch -> match -> store -> briefing -> notify.

**Depends on**: Phase 3

**BMAD Stories**:
- Story 4-1: Job Scout Agent Implementation
- Story 4-2: Indeed Job Board Integration
- Story 4-3: LinkedIn Job Scraping Integration
- Story 4-4: AI Job Matching Algorithm
- Story 4-5: Match Rationale Generation
- Story 4-6: Swipe Card Interface
- Story 4-7: Top Pick of the Day Feature
- Story 4-8: Job Detail Expansion
- Story 4-9: Preference Learning from Swipe Behavior
- Story 4-10: Job Matches Empty State

**Research Adjustments (CRITICAL)**:
- Story 4-2 becomes "Aggregator API Integration (JSearch + Adzuna)" -- NOT Indeed direct integration. Indeed has no public API.
- Story 4-3 (LinkedIn Job Scraping) is REMOVED/REPLACED. LinkedIn actively blocks scraping. Replace with SerpAPI Google Jobs as tertiary source.
- Use aggregator APIs exclusively: JSearch (RapidAPI) primary, Adzuna secondary, SerpAPI Google Jobs tertiary.
- Budget needed: $50-200/month for API access at scale.
- Three-layer caching: Redis (L1) -> Materialized Views (L2) -> TanStack Query (L3)
- Validate LLM cost tracking works end-to-end with this first agent (<$6/user/month budget)

**Success Criteria** (what must be TRUE):
1. A user with completed preferences sees at least 3 quality job matches in their first briefing after the Job Scout runs
2. Each job match displays a score (0-100), expandable rationale explaining why it matched, and deal-breaker compliance status
3. The swipe card interface works on mobile (swipe right = interested, left = pass) and user actions feed back into preference learning
4. Job data is deduplicated across sources -- the same job from JSearch and Adzuna appears as one listing
5. LLM cost for job matching stays under $0.50/user/day as measured by the cost tracking middleware

**Plans**: 6 plans in 4 waves
Plans:
- [ ] Plan 01 -- Database Schema + Backend Models (Wave 1)
- [ ] Plan 02 -- Analytics Infrastructure - PostHog (Wave 1)
- [ ] Plan 03 -- Resume Upload + Profile Extraction Backend (Wave 2)
- [ ] Plan 04 -- Preferences Backend + Shared Frontend Components (Wave 2)
- [ ] Plan 05 -- Onboarding Frontend Flow (Wave 3)
- [ ] Plan 06 -- Preference Wizard Frontend + Integration Wiring (Wave 4)

**Research Flags**: Job board API rate limits, deduplication strategy, match scoring algorithm approach

**Risks**:
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Aggregator API data quality/coverage insufficient | Medium | High | Multi-source strategy (3 APIs); monitor coverage gaps by metro area |
| Job matching LLM costs exceed budget | Medium | High | Start with keyword matching, use LLM only for rationale generation; GPT-3.5 for scoring |
| Rate limits on free API tiers block development | Low | Medium | Budget for paid tiers early; cache aggressively (24h TTL for job listings) |

---

### Phase 5: Resume Agent + ATS Optimization

**Goal**: Users can have their resume auto-tailored for specific jobs with keyword gap analysis, ATS optimization, and a clear diff view showing what changed and why -- without ever fabricating qualifications.

**Depends on**: Phase 4

**BMAD Stories**:
- Story 5-1: Resume Agent Implementation
- Story 5-2: Master Resume Management
- Story 5-3: Resume Diff View
- Story 5-4: ATS Optimization Logic
- Story 5-5: Cover Letter Generator (DEFER to Phase 8)
- Story 5-6: Cover Letter Personalization (DEFER to Phase 8)
- Story 5-13: Application History and Materials
- Story 5-14: Application Empty State

**Research Adjustments**:
- Cover letter stories (5-5, 5-6) deferred to Phase 8 (grouped with Apply Agent)
- Apply Agent stories (5-7 through 5-12) deferred to Phase 8
- Master resume uses copy-on-write pattern -- tailored versions never modify the original
- NEVER fabricate qualifications. Enforce with DeepEval hallucination testing (threshold 0.9) in CI
- ATS output format: single-column DOCX, standard headings, no images/tables/headers-footers
- Existing codebase already has resume parsing (PyPDF2 + python-docx) -- extend, don't rewrite

**Success Criteria** (what must be TRUE):
1. A user can select a job match and see an auto-tailored resume within 45 seconds, with a side-by-side diff view highlighting what was changed
2. The tailored resume passes ATS format checks: single-column layout, standard section headings, no images, parseable by common ATS systems
3. Keyword gap analysis shows which job posting keywords are present/missing in the resume and how they were addressed
4. The system NEVER invents qualifications not present in the master resume -- verified by automated hallucination testing

**Plans**: 6 plans in 4 waves
Plans:
- [ ] Plan 01 -- Database Schema + Backend Models (Wave 1)
- [ ] Plan 02 -- Analytics Infrastructure - PostHog (Wave 1)
- [ ] Plan 03 -- Resume Upload + Profile Extraction Backend (Wave 2)
- [ ] Plan 04 -- Preferences Backend + Shared Frontend Components (Wave 2)
- [ ] Plan 05 -- Onboarding Frontend Flow (Wave 3)
- [ ] Plan 06 -- Preference Wizard Frontend + Integration Wiring (Wave 4)

**Risks**:
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Resume fabrication slips through | Low | Critical | DeepEval hallucination test in CI (threshold 0.9); human review sample in first 100 generations |
| DOCX generation formatting inconsistencies across ATS platforms | Medium | Medium | Test against top 5 ATS parsers (Workday, Greenhouse, Lever, iCIMS, Taleo) |

---

### Phase 6: Pipeline Tracking + Email Forwarding

**Goal**: Users can track all their job applications in a kanban board, with status updates parsed from forwarded emails, manual entry, and follow-up reminders.

**Depends on**: Phase 4 (needs job data), Phase 5 (needs application materials)

**BMAD Stories**:
- Story 6-1: Pipeline Agent Implementation
- Story 6-4: Email Status Detection
- Story 6-5: Kanban Pipeline View
- Story 6-6: Pipeline List View
- Story 6-14: Pipeline Empty State

**Research Adjustments (CRITICAL)**:
- Stories 6-2 (Gmail OAuth) and 6-3 (Outlook OAuth) are DEFERRED to Phase 9. Gmail OAuth requires CASA assessment ($5K-$75K/year). Use email forwarding for MVP instead.
- Email forwarding flow: user forwards confirmation/rejection emails to a unique `user-id@pipeline.jobpilot.com` address. Server-side parsing extracts status updates.
- Design the `EmailProvider` abstraction layer now so OAuth can be added later without refactoring.
- Follow-up agent stories (6-7, 6-8, 6-9) deferred to Phase 9.
- Stealth mode stories (6-10, 6-11, 6-12, 6-13) deferred to Phase 9.

**Success Criteria** (what must be TRUE):
1. A user can view all their applications in a kanban board with columns: Saved / Applied / Interviewing / Offer / Rejected
2. When a user forwards a recruiter email to their unique pipeline address, the system parses it and updates the application status within 5 minutes
3. A user can manually add and update application entries (for jobs not tracked through agents)
4. The pipeline view shows application age, next action due, and last status change date

**Plans**: 6 plans in 4 waves
Plans:
- [ ] Plan 01 -- Database Schema + Backend Models (Wave 1)
- [ ] Plan 02 -- Analytics Infrastructure - PostHog (Wave 1)
- [ ] Plan 03 -- Resume Upload + Profile Extraction Backend (Wave 2)
- [ ] Plan 04 -- Preferences Backend + Shared Frontend Components (Wave 2)
- [ ] Plan 05 -- Onboarding Frontend Flow (Wave 3)
- [ ] Plan 06 -- Preference Wizard Frontend + Integration Wiring (Wave 4)

**ADRs to Resolve**:
- ADR-4: Email Pipeline Approach (email forwarding for MVP, OAuth when revenue justifies CASA) -- consensus, document

**Risks**:
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Email forwarding adoption rate low (users forget) | Medium | Medium | Daily briefing reminder "3 applications have no status update -- forward emails to update"; auto-track agent-submitted applications |
| Email parsing accuracy below 90% | Medium | Medium | Keyword pre-filter + LLM classification; manual correction UI; track accuracy metrics |

---

### ---- MVP BOUNDARY ----

Phases 1-6 deliver the core value proposition: "Your AI Career Agent that works 24/7." A user can sign up, configure preferences, receive daily briefings with matched jobs, get tailored resumes, and track their pipeline. Everything below is Growth and Vision features.

---

### Phase 7: H1B Sponsorship Intelligence

**Goal**: H1B visa holders can research any company's sponsorship history, approval rates, and wage data, with verified sponsor badges appearing on job matches.

**Depends on**: Phase 4 (needs job matching integration for badges)

**BMAD Stories**:
- Story 7-1: H1B Data Aggregation Pipeline
- Story 7-2: H1BGrader Integration
- Story 7-3: MyVisaJobs Integration
- Story 7-4: USCIS Public Data Integration
- Story 7-5: Sponsor Scorecard UI
- Story 7-6: Approval Rate Visualization
- Story 7-7: Verified Sponsor Badge on Job Cards
- Story 7-8: H1B Filter in Job Search
- Story 7-9: Sponsor Data Freshness Infrastructure
- Story 7-10: H1B Empty State

**Research Adjustments**:
- Use USCIS H-1B Employer Data Hub + DOL OFLC Performance Data as PRIMARY sources (government, free, reliable)
- H1BGrader and MyVisaJobs as SECONDARY validation (check their ToS before scraping)
- Data freshness: "within 48 hours of government release" NOT "<24 hours" (government data is quarterly)
- Employer name normalization is a hard problem -- fuzzy matching needed (e.g., "Google LLC" vs "Alphabet Inc." vs "Google")

**Success Criteria** (what must be TRUE):
1. A user can search any company and see its H1B sponsorship scorecard: total petitions, approval rate, wage ranges, and green card history
2. Job matches show a "Verified Sponsor" badge when the employer has confirmed H1B sponsorship history in government data
3. H1B Pro users can filter all job matches to show only verified sponsors
4. All sponsor data shows source attribution and a freshness badge (e.g., "Updated from USCIS Q3 2025 data")
5. The data pipeline refreshes automatically when new government data releases are detected

**Plans**: 6 plans in 4 waves
Plans:
- [ ] Plan 01 -- Database Schema + Backend Models (Wave 1)
- [ ] Plan 02 -- Analytics Infrastructure - PostHog (Wave 1)
- [ ] Plan 03 -- Resume Upload + Profile Extraction Backend (Wave 2)
- [ ] Plan 04 -- Preferences Backend + Shared Frontend Components (Wave 2)
- [ ] Plan 05 -- Onboarding Frontend Flow (Wave 3)
- [ ] Plan 06 -- Preference Wizard Frontend + Integration Wiring (Wave 4)

**Research Flags**: Employer name normalization strategy, USCIS/DOL data joining accuracy, H1BGrader/MyVisaJobs ToS compliance

**Risks**:
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Employer name normalization accuracy below 90% | High | High | Fuzzy matching + manual curation for top 500 employers; crowdsource corrections |
| Government data format changes without notice | Medium | Medium | Schema validation on ingestion; alert on parsing failures; manual fallback |

---

### Phase 8: Apply Agent + Approval Queue

**Goal**: Users can have applications auto-submitted to company career pages with tier-based approval, cover letter generation, and quality gates -- only for direct-apply positions, never platform apply.

**Depends on**: Phase 5 (needs tailored resumes), Phase 6 (needs pipeline tracking)

**BMAD Stories**:
- Story 5-5: Cover Letter Generator (deferred from Phase 5)
- Story 5-6: Cover Letter Personalization (deferred from Phase 5)
- Story 5-7: Apply Agent Implementation
- Story 5-8: Approval Queue for Applications
- Story 5-9: One-Tap Approval from Briefing
- Story 5-10: Application Submission Confirmation
- Story 5-11: Application Failure Handling
- Story 5-12: Indeed Easy Apply Integration (RESEARCH NEEDED -- may violate ToS)

**Research Adjustments (CRITICAL)**:
- Apply Agent ONLY automates Direct Apply (company career pages). NEVER Platform Apply (LinkedIn Easy Apply, Indeed Apply) -- violates ToS and will be detected.
- Story 5-12 (Indeed Easy Apply) needs legal review. Research says this violates Indeed ToS. Consider replacing with "Workday career page automation" or similar direct-apply target.
- Quality gate: minimum 70% match score before auto-apply
- Volume caps: 10 applications/day for L3, 5-7/day for L2
- Approval queue bridges L2 (human-approves) and L3 (autonomous within rules)
- Graceful manual fallback for unsupported ATS forms or CAPTCHA-blocked pages
- 30-second undo window after approval

**Success Criteria** (what must be TRUE):
1. An L2 user sees pending applications in their daily briefing and can approve/reject each with one tap
2. An L3 user has applications auto-submitted within their daily volume cap and deal-breaker rules, with confirmation in the next briefing
3. The Apply Agent successfully fills and submits applications on at least 3 of the top 5 ATS platforms (Workday, Greenhouse, Lever, iCIMS, Taleo)
4. A cover letter is auto-generated with company-specific references and can be reviewed/edited before submission
5. Failed applications surface clearly in the briefing with reason and manual fallback instructions

**Plans**: 6 plans in 4 waves
Plans:
- [ ] Plan 01 -- Database Schema + Backend Models (Wave 1)
- [ ] Plan 02 -- Analytics Infrastructure - PostHog (Wave 1)
- [ ] Plan 03 -- Resume Upload + Profile Extraction Backend (Wave 2)
- [ ] Plan 04 -- Preferences Backend + Shared Frontend Components (Wave 2)
- [ ] Plan 05 -- Onboarding Frontend Flow (Wave 3)
- [ ] Plan 06 -- Preference Wizard Frontend + Integration Wiring (Wave 4)

**Research Flags**: ATS form-filling reliability per platform, CAPTCHA handling, EU AI Act compliance for applicant-side tools

**ADRs to Resolve**:
- EU AI Act applicability to applicant-side auto-apply tools (legal review needed)
- Indeed Easy Apply ToS compliance (likely must drop this integration)
- Auto-apply success rate metric: 95% target only for direct apply, not platform apply

**Risks**:
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| ATS form structures change frequently, breaking automation | High | High | Target top 5 ATS only; graceful manual fallback; monitor success rates per platform |
| Legal risk from automated job applications | Medium | High | Direct apply only; clear user consent; comply with EU AI Act if applicable |
| CAPTCHA blocks automation | High | Medium | Detect CAPTCHA, surface manual fallback; never attempt CAPTCHA bypass |

---

### Phase 9: Advanced Features + Production Hardening

**Goal**: Deliver remaining P1/P2 features (follow-up agent, stealth mode, network assistant) and production-harden the platform with Gmail OAuth, E2E testing, and operational dashboards.

**Depends on**: Phases 6-8

**BMAD Stories**:
- Story 6-2: Gmail OAuth Integration (deferred from Phase 6)
- Story 6-3: Outlook OAuth Integration (deferred from Phase 6)
- Story 6-7: Follow-up Agent Implementation (deferred from Phase 6)
- Story 6-8: Follow-up Draft Generation (deferred from Phase 6)
- Story 6-9: Follow-up Tracking (deferred from Phase 6)
- Story 6-10: Stealth Mode Activation (deferred from Phase 6)
- Story 6-11: Employer Blocklist (deferred from Phase 6)
- Story 6-12: Privacy Proof Documentation (deferred from Phase 6)
- Story 6-13: Passive Mode Settings (deferred from Phase 6)
- Story 8-1 through 8-8: Interview Preparation (Epic 8, all P2)
- Story 9-1 through 9-8: Network Building (Epic 9, all P2)
- Story 10-1 through 10-10: Enterprise Administration (Epic 10, all P1 parallel)

**Research Adjustments**:
- Gmail/Outlook OAuth only after CASA assessment is financially justified (~$50K ARR threshold)
- Network Agent (Epic 9) redesigned as suggestion-only -- NO LinkedIn automation (legal risk)
- Enterprise Admin (Epic 10) can be a parallel track if there is customer demand
- Add: Playwright E2E test suite, OWASP ZAP dynamic testing, Grafana dashboards, LLM cost alerting

**Success Criteria** (what must be TRUE):
1. Follow-up agent sends draft follow-up emails at optimal intervals (7-14 days post-application) for user approval
2. Stealth mode users have encrypted employer blocklists, no public agent footprint, and can generate a privacy proof document
3. Gmail/Outlook OAuth users can connect their email for automatic pipeline updates without forwarding (only if CASA is complete)
4. E2E test suite covers all critical user journeys (onboarding, job matching, resume tailoring, pipeline tracking)
5. Operational dashboards show real-time system health, LLM costs per user, and agent success rates

**Plans**: 6 plans in 4 waves
Plans:
- [ ] Plan 01 -- Database Schema + Backend Models (Wave 1)
- [ ] Plan 02 -- Analytics Infrastructure - PostHog (Wave 1)
- [ ] Plan 03 -- Resume Upload + Profile Extraction Backend (Wave 2)
- [ ] Plan 04 -- Preferences Backend + Shared Frontend Components (Wave 2)
- [ ] Plan 05 -- Onboarding Frontend Flow (Wave 3)
- [ ] Plan 06 -- Preference Wizard Frontend + Integration Wiring (Wave 4)

**Risks**:
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| CASA assessment too expensive at current revenue | High | Medium | Keep email forwarding as primary; OAuth is an upgrade, not a requirement |
| LinkedIn automation legal exposure | High | Critical | Network Agent is suggestion-only; user executes all LinkedIn actions manually |

---

## Post-MVP / Deferred (Not Phased)

These items are explicitly deferred based on research findings:

- **pgvector semantic job matching** -- start with keyword matching, upgrade later
- **Full event sourcing** -- simple append-only audit log is sufficient for MVP
- **LinkedIn profile import as primary path** -- use resume upload + data export
- **K8s migration** -- Railway is sufficient until 5000+ DAU
- **Self-hosted auth** -- Clerk is fine for now; AuthProvider interface allows future migration

---

## Story Coverage Map

| BMAD Epic | Stories | Phase(s) | Notes |
|-----------|---------|----------|-------|
| Epic 0: Platform Foundation | 0-1 through 0-15 (15) | Phase 1 | 0-1 in review |
| Epic 1: Lightning Onboarding | 1-1 through 1-6 (6) | Phase 2 | Resume upload is primary path |
| Epic 2: Preference Configuration | 2-1 through 2-8 (8) | Phase 2 | |
| Epic 3: Agent Orchestration Core | 3-1 through 3-11 (11) | Phase 3 | |
| Epic 4: AI-Powered Job Matching | 4-1 through 4-10 (10) | Phase 4 | 4-2, 4-3 redesigned (aggregator APIs) |
| Epic 5: Application Automation | 5-1 through 5-4, 5-13, 5-14 (6) | Phase 5 | |
| Epic 5: Application Automation | 5-5 through 5-12 (8) | Phase 8 | Cover letters + Apply Agent |
| Epic 6: Pipeline & Privacy | 6-1, 6-4, 6-5, 6-6, 6-14 (5) | Phase 6 | Email forwarding, not OAuth |
| Epic 6: Pipeline & Privacy | 6-2, 6-3, 6-7 through 6-13 (9) | Phase 9 | OAuth + follow-up + stealth |
| Epic 7: H1B Specialist | 7-1 through 7-10 (10) | Phase 7 | Government data primary |
| Epic 8: Interview Prep (P2) | 8-1 through 8-8 (8) | Phase 9 | |
| Epic 9: Network Building (P2) | 9-1 through 9-8 (8) | Phase 9 | Suggestion-only, no automation |
| Epic 10: Enterprise Admin | 10-1 through 10-10 (10) | Phase 9 | Parallel track if demand exists |

**Total: 114 stories mapped across 9 phases. 0 orphaned stories.**

---

## ADR Summary

| ADR | Decision Point | Phase | Status |
|-----|---------------|-------|--------|
| ADR-1 | Agent Orchestration (LangGraph vs Custom) | Phase 3 | OPEN -- resolve via prototype |
| ADR-2 | Database Access (SQLAlchemy primary) | Phase 1 | RESOLVED -- documented in Plan 03 |
| ADR-3 | Job Data (Aggregator APIs only) | Phase 4 | CONSENSUS -- document it |
| ADR-4 | Email Pipeline (Forwarding for MVP) | Phase 6 | CONSENSUS -- document it |
| ADR-5 | LinkedIn Scope (Resume upload primary) | Phase 2 | CONSENSUS -- document it |
| ADR-6 | Email Service (Resend vs SendGrid) | Phase 1 | RESOLVED -- Resend chosen (Plan 08) |
| ADR-7 | EU AI Act applicability | Phase 8 | OPEN -- legal review needed |

---

## Progress

**Execution Order:** 1 -> 2 -> 3 -> 4 -> 5 -> 6 (MVP) -> 7 -> 8 -> 9

| Phase | Plans Complete | Status | Completed |
|-------|---------------|--------|-----------|
| 1. Foundation Modernization | 0/8 | Planned | - |
| 2. Onboarding + Preferences | 0/6 | Planned | - |
| 3. Agent Framework Core | 0/TBD | Not started | - |
| 4. Job Scout Agent | 0/TBD | Not started | - |
| 5. Resume Agent + ATS | 0/TBD | Not started | - |
| 6. Pipeline Tracking | 0/TBD | Not started | - |
| -- MVP BOUNDARY -- | | | |
| 7. H1B Intelligence | 0/TBD | Not started | - |
| 8. Apply Agent | 0/TBD | Not started | - |
| 9. Advanced + Hardening | 0/TBD | Not started | - |
