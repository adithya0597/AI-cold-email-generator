---
stepsCompleted: [1, 2, 3, 4]
partyModeEnhancements: 30
validationStatus: 'PASSED'
totalEpics: 11
totalStories: 114
frCoverage: '15/15'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/ux-design-specification.md'
workflowType: 'epics-and-stories'
project_name: 'JobPilot'
user_name: 'bala'
date: '2026-01-25'
---

# JobPilot - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for JobPilot, decomposing the requirements from the PRD, UX Design, and Architecture requirements into implementable stories.

---

## Requirements Inventory

### Functional Requirements

| ID | Feature | Priority | Tier | Agent Type | Description |
|----|---------|----------|------|------------|-------------|
| F1 | Zero-Setup Onboarding | P0 | All | - | 30-second profile extraction from LinkedIn URL or resume |
| F2 | Preference Wizard | P0 | All | - | Multi-step wizard for job preferences, locations, salary, deal-breakers |
| F3 | Daily Briefing | P0 | All | Orchestrator | Personalized daily digest delivered at user-configured time |
| F4 | Job Scout Agent | P0 | All | Research | 24/7 job board monitoring with AI-scored matching |
| F5 | Resume Agent | P0 | Pro+ | Action | Auto-tailors resume for each job with ATS optimization |
| F6 | Pipeline Agent | P0 | Pro+ | Tracking | Email parsing for status updates, auto-moves pipeline cards |
| F7 | Emergency Brake | P0 | All | - | One-tap instant pause for all agent activity |
| F8 | H1B Sponsor Database | P0 | H1B Pro | Research | Aggregated visa sponsor data from multiple sources |
| F9 | Apply Agent | P1 | Pro+ | Action | Autonomous application submission with tier-based approval |
| F10 | Cover Letter Generator | P1 | Pro+ | Action | AI-generated cover letters with company-specific references |
| F11 | Follow-up Agent | P1 | Pro+ | Tracking | Auto-timed follow-up drafts at optimal intervals |
| F12 | Stealth Mode | P1 | Career Insurance | - | Verified privacy mode with blocklists and proof of concealment |
| F13 | Interview Intel Agent | P2 | Pro+ | Research | Auto-generated interview prep briefings |
| F14 | Network Agent | P2 | H1B Pro | Action | Autonomous relationship warming and introduction requests |
| F15 | Enterprise Admin Dashboard | P1 | Enterprise | - | Aggregate metrics and controls for HR admins |

### Non-Functional Requirements

| ID | Category | Key Metrics | MVP Target |
|----|----------|-------------|------------|
| NFR1 | Performance | Page load <2s, Agent response <30s, Profile parse <60s | All targets must be met |
| NFR2 | Scalability | 10,000 DAU, 100K jobs/day, 50K applications/day | 1,000 users at launch |
| NFR3 | Availability | 99.5% uptime, >95% auto-apply success rate | 99% at launch |
| NFR4 | Security | OAuth 2.0, AES-256 encryption, RLS, audit logging | Basic auth + encryption |
| NFR5 | Privacy | GDPR/CCPA compliant, stealth verification, data minimization | GDPR/CCPA basics |
| NFR6 | LLM Constraints | <$6 LLM cost/user/month, 68%+ gross margin | Cost tracking from day 1 |
| NFR7 | Compliance | WCAG 2.1 AA, LinkedIn/Job Board ToS, H1B data attribution | ToS compliance |
| NFR8 | Observability | Real-time dashboards, error tracking, LLM cost tracking | Basic monitoring |
| NFR9 | Internationalization | English first, multi-timezone support | US English only |

### UX Requirements

| ID | Category | Key Elements |
|----|----------|--------------|
| UX1 | Design Principles | Agent-First, Transparency, Trust Through Control, Progressive Disclosure, Calm Technology |
| UX2 | Information Architecture | Home (Briefing) → Jobs → Pipeline → Documents → Settings |
| UX3 | Interaction Patterns | Daily Briefing, Approval Queue, Job Match Card, Resume Diff View, Emergency Brake |
| UX4 | Mobile-First | Swipe gestures, offline briefing cache, push notifications |
| UX5 | Tone & Voice | Friendly assistant for briefings, celebratory for success, honest for errors |
| UX6 | Accessibility | WCAG 2.1 AA, VoiceOver/TalkBack, keyboard navigation, 4.5:1 contrast |
| UX7 | Visual Design | Clean/professional, calm blues/greens, system fonts, Linear/Superhuman/Notion inspired |
| UX8 | Onboarding Flow | 8-step wizard, <5 minutes target, first briefing preview |
| UX9 | Empty States | Encouraging copy, actionable next steps, never dead ends |

### Technical Requirements

| ID | Category | Technology Choices |
|----|----------|-------------------|
| Tech1 | Existing Codebase | FastAPI backend, React frontend, LLM client abstraction (70% reusable) |
| Tech2 | New Infrastructure | Supabase (PostgreSQL), Clerk auth, Celery + Redis, SendGrid |
| Tech3 | Agent Architecture | Custom orchestrator, langchain-core only, shared memory via PostgreSQL |
| Tech4 | Data Schema | Hybrid relational + JSONB, soft-delete pattern, versioned agent outputs |
| Tech5 | API Design | REST + WebSockets, /api/v1/ versioned, JWT auth, rate limiting |
| Tech6 | LLM Optimization | GPT-3.5 for parsing (~$0.30), GPT-4 for quality (~$1.50), ~$5/user/month |
| Tech7 | Integrations | LinkedIn (scraping), Indeed, Gmail/Outlook OAuth, H1BGrader, Stripe |
| Tech8 | Security | Clerk OAuth, Supabase RLS, encrypted blocklists, immutable audit logs |
| Tech9 | Deployment | Vercel (FE) + Railway (BE) + Supabase (DB), K8s migration path |

### Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| State Management | TanStack Query + Zustand | Server state caching + lightweight UI state |
| Agent Control | Redis pub/sub + checkpoint flags | Real-time emergency brake, pause at logical steps |
| Auth Abstraction | AuthProvider interface | Future self-hosted option without vendor lock-in |
| Testing Strategy | pytest + Playwright + Schemathesis | Unit, E2E, API contract coverage |
| Observability | OpenTelemetry from day one | Distributed tracing, agent execution visibility |

---

## FR Coverage Map

| Feature ID | Epic | Description | Est. Stories |
|------------|------|-------------|--------------|
| F1 | Epic 1 | Lightning Onboarding - 30-second profile extraction | 5-6 |
| F2 | Epic 2 | Preference Configuration - Job preferences, deal-breakers | 6-8 |
| F3 | Epic 3 | Agent Orchestration Core - Daily briefing generation | 8-10 |
| F4 | Epic 4 | AI-Powered Job Matching - Job discovery with swipe UI | 8-10 |
| F5 | Epic 5 | Application Automation - Resume tailoring | 6-8 |
| F6 | Epic 6 | Pipeline & Privacy - Email parsing, auto-tracking | 8-10 |
| F7 | Epic 3 | Agent Orchestration Core - Emergency brake | 3-4 |
| F8 | Epic 7 | H1B Specialist Experience - Sponsor database | 8-10 |
| F9 | Epic 5 | Application Automation - Auto-apply with approval | 6-8 |
| F10 | Epic 5 | Application Automation - Cover letter generation | 4-5 |
| F11 | Epic 6 | Pipeline & Privacy - Follow-up automation | 4-5 |
| F12 | Epic 6 | Pipeline & Privacy - Stealth mode | 4-5 |
| F13 | Epic 8 | Interview Preparation - Auto-generated prep briefings | 6-8 |
| F14 | Epic 9 | Network Building - Relationship warming | 6-8 |
| F15 | Epic 10 | Enterprise Administration - Admin dashboard | 10-12 |

### NFR Coverage Map

| NFR ID | Primary Epic | Implementation |
|--------|--------------|----------------|
| NFR1 (Performance) | Epic 0 | Caching layer, async patterns, performance budgets |
| NFR2 (Scalability) | Epic 0 | Database indexes, connection pooling, worker scaling |
| NFR3 (Availability) | Epic 0 | Health checks, graceful degradation, retry logic |
| NFR4 (Security) | Epic 0 | Clerk auth, RLS policies, encrypted storage |
| NFR5 (Privacy) | Epic 6 | Stealth mode, data minimization, GDPR flows |
| NFR6 (LLM Constraints) | Epic 0 | Cost tracking middleware, model selection |
| NFR7 (Compliance) | All | WCAG in all epics, ToS compliance in Epic 4-7 |
| NFR8 (Observability) | Epic 0 | OpenTelemetry, error tracking, dashboards |
| NFR9 (i18n) | Epic 0 | Timezone handling, locale infrastructure |

---

## Epic List

### Epic 0: Platform Foundation
**User Outcome:** Infrastructure enabling all subsequent epics - users benefit from fast, secure, observable platform.

**Covers:** NFR1-NFR4, NFR6, NFR8-NFR9, Tech2, Tech4, Tech5, Tech8, Tech9
**Est. Stories:** 12-15
**Dependencies:** None (foundational)
**MVP Scope:** ✅ Required

**Definition of Done:**
- [ ] Supabase schema deployed with RLS policies
- [ ] Clerk authentication functional with LinkedIn OAuth
- [ ] Redis + Celery workers operational
- [ ] OpenTelemetry tracing active
- [ ] LLM cost tracking middleware deployed
- [ ] CI/CD pipeline with automated tests

---

### Epic 1: Lightning Onboarding
**User Outcome:** Users can sign up and have a complete profile extracted from LinkedIn URL or resume in 30 seconds.

**FRs Covered:** F1 (Zero-Setup Onboarding)
**Est. Stories:** 5-6
**Dependencies:** Epic 0
**MVP Scope:** ✅ Required

**Key Stories:**
- LinkedIn URL profile extraction
- Resume file upload and parsing
- Profile review and correction UI
- First briefing preview (magic moment)
- Empty state: "Your agent is getting ready..."

**Definition of Done:**
- [ ] Profile extraction completes in <60 seconds
- [ ] 95%+ field extraction accuracy
- [ ] First briefing preview shown before wizard completion
- [ ] Accessibility: keyboard navigation, screen reader support

---

### Epic 2: Preference Configuration
**User Outcome:** Users can configure job preferences, locations, salary expectations, and deal-breakers that guide agent behavior.

**FRs Covered:** F2 (Preference Wizard)
**Est. Stories:** 6-8
**Dependencies:** Epic 0, Epic 1
**MVP Scope:** ✅ Required

**Key Stories:**
- Job type and title preferences
- Location and remote work settings
- Salary range configuration
- Deal-breaker definition (must-haves, never-haves)
- H1B sponsorship requirement flag
- Autonomy level selection (L0-L3)

**Definition of Done:**
- [ ] Complete wizard in <5 minutes
- [ ] Preferences stored and retrievable
- [ ] Deal-breakers enforced in matching algorithm
- [ ] Autonomy level affects agent behavior

---

### Epic 3: Agent Orchestration Core
**User Outcome:** Users receive daily briefings summarizing agent activity and can pause all agents instantly with emergency brake.

**FRs Covered:** F3 (Daily Briefing), F7 (Emergency Brake)
**Est. Stories:** 11-14
**Dependencies:** Epic 0, Epic 1, Epic 2
**MVP Scope:** ✅ Required

**Key Stories:**
- Orchestrator agent infrastructure
- Daily briefing generation pipeline
- Briefing delivery (email + in-app)
- User-configurable delivery time
- Emergency brake button (always visible)
- Emergency brake state machine (running → pausing → paused)
- Agent activity feed
- Empty state: "Your agents are starting up..."

**Definition of Done:**
- [ ] Briefing delivered within 15 minutes of configured time
- [ ] Emergency brake pauses all agents within 30 seconds
- [ ] Agent activity visible in real-time via WebSocket
- [ ] Graceful degradation: "lite briefing" if agents fail

---

### Epic 4: AI-Powered Job Matching
**User Outcome:** Users wake up to AI-curated job matches with scores, rationale, and swipe-to-review interface.

**FRs Covered:** F4 (Job Scout Agent)
**Est. Stories:** 8-10
**Dependencies:** Epic 0, Epic 1, Epic 2, Epic 3
**MVP Scope:** ✅ Required

**Key Stories:**
- Job Scout Agent implementation
- Job board integration (Indeed, LinkedIn scraping)
- AI matching algorithm with scoring
- Match rationale generation
- Swipe card interface (Tinder-style)
- Top Pick of the Day feature
- Job detail expansion
- Preference learning from swipe behavior
- Empty state: "Your agent is searching..."

**Definition of Done:**
- [ ] Minimum 3 quality matches in first briefing (Robinhood moment)
- [ ] Match scores with expandable rationale
- [ ] Swipe gestures functional on mobile
- [ ] Preference learning improves match quality over time

---

### Epic 5: Application Automation
**User Outcome:** Users can have resumes auto-tailored, cover letters generated, and applications submitted with one-tap approval.

**FRs Covered:** F5 (Resume Agent), F9 (Apply Agent), F10 (Cover Letter Generator)
**Est. Stories:** 16-21
**Dependencies:** Epic 0, Epic 1, Epic 2, Epic 3, Epic 4
**MVP Scope:** ✅ Partial (F5 required, F9/F10 P1)

**Key Stories:**
- Resume Agent implementation
- Resume diff view (side-by-side comparison)
- ATS optimization logic
- Cover letter generation
- Company-specific personalization
- Apply Agent implementation
- Approval queue with tier-based gates
- One-tap approve/reject from briefing
- Integration: Indeed Easy Apply
- Integration: Company career pages
- Batch approval for trusted users
- 30-second undo window
- Empty state: "No applications pending approval"

**Definition of Done:**
- [ ] Resume tailoring completes in <45 seconds
- [ ] Diff view shows clear before/after with rationale
- [ ] Apply Agent respects autonomy level gates
- [ ] >95% auto-apply success rate
- [ ] External integrations tested and rate-limited

---

### Epic 6: Pipeline & Privacy
**User Outcome:** Users can track all applications automatically, see status updates from email parsing, receive follow-up suggestions, and enable stealth mode for privacy.

**FRs Covered:** F6 (Pipeline Agent), F11 (Follow-up Agent), F12 (Stealth Mode)
**Est. Stories:** 16-20
**Dependencies:** Epic 0, Epic 1, Epic 2, Epic 3
**MVP Scope:** ✅ Partial (F6 required, F11/F12 P1)

**Key Stories:**
- Pipeline Agent implementation
- Gmail OAuth integration
- Outlook OAuth integration
- Email parsing for status detection
- Kanban pipeline view
- Auto-status updates (Applied → Interview → Offer)
- Follow-up Agent implementation
- Optimal follow-up timing algorithm
- Follow-up draft generation
- Stealth mode activation
- Employer blocklist (encrypted)
- Privacy proof documentation
- Passive mode settings
- Empty state: "Your pipeline is empty - let's find some matches!"

**Definition of Done:**
- [ ] >90% email parsing accuracy
- [ ] Pipeline cards auto-move based on detected events
- [ ] Follow-ups timed to optimal intervals
- [ ] Stealth mode: blocklists encrypted, privacy proof available
- [ ] GDPR/CCPA data flows implemented

---

### Epic 7: H1B Specialist Experience
**User Outcome:** H1B visa holders can research any company's sponsorship history, approval rates, and get verified sponsor badges on job matches.

**FRs Covered:** F8 (H1B Sponsor Database)
**Est. Stories:** 8-10
**Dependencies:** Epic 0, Epic 4
**MVP Scope:** ✅ Required for H1B tier

**Key Stories:**
- H1B data aggregation pipeline
- H1BGrader integration
- MyVisaJobs integration
- USCIS public data integration
- Sponsor scorecard UI
- Approval rate visualization
- Data freshness infrastructure (scheduled scraping)
- Verified Sponsor badge on job cards
- LCA wage data display
- Empty state: "No sponsor data found - contribute if you know!"

**Definition of Done:**
- [ ] 500,000+ company records in database
- [ ] Data freshness: updated weekly
- [ ] Source attribution on all sponsor data
- [ ] Sponsor badge visible on all job matches

---

### Epic 8: Interview Preparation (P2)
**User Outcome:** Users get auto-generated interview prep briefings with company research, interviewer background, and STAR response suggestions.

**FRs Covered:** F13 (Interview Intel Agent)
**Est. Stories:** 6-8
**Dependencies:** Epic 0, Epic 3, Epic 6
**MVP Scope:** ❌ P2 (post-MVP)

**Key Stories:**
- Interview Intel Agent implementation
- Company research synthesis
- Interviewer LinkedIn research
- Common questions for role type
- STAR response suggestions
- Prep briefing delivery (24h before interview)
- Calendar integration for interview detection
- Empty state: "No interviews scheduled yet"

**Definition of Done:**
- [ ] Prep briefing delivered 24 hours before interview
- [ ] Company research includes culture, news, challenges
- [ ] Interviewer background from public sources only

---

### Epic 9: Network Building (P2)
**User Outcome:** Users have autonomous relationship warming with target contacts, including warm path mapping and introduction request drafts.

**FRs Covered:** F14 (Network Agent)
**Est. Stories:** 6-8
**Dependencies:** Epic 0, Epic 3, Epic 4
**MVP Scope:** ❌ P2 (post-MVP)

**Key Stories:**
- Network Agent implementation
- Warm path finder (2nd degree connections)
- Introduction request message drafts
- Content engagement tracking (likes, comments)
- Relationship temperature scoring
- Human approval for direct outreach
- Empty state: "Building your network map..."

**Definition of Done:**
- [ ] Warm paths identified to target companies
- [ ] All direct outreach requires human approval
- [ ] Relationship temperature tracked over time

---

### Epic 10: Enterprise Administration
**User Outcome:** HR admins can onboard employees in bulk, monitor aggregate metrics, configure per-employee autonomy levels, and track ROI.

**FRs Covered:** F15 (Enterprise Admin Dashboard)
**Est. Stories:** 10-12
**Dependencies:** Epic 0, Epic 1, Epic 3
**MVP Scope:** ❌ P1 (parallel track)

**Key Stories:**
- Enterprise admin role and permissions
- Bulk onboarding via CSV upload
- Aggregate metrics dashboard
- Per-employee autonomy configuration
- At-risk employee alerts (low engagement)
- ROI reporting vs industry benchmarks
- PII detection alerts
- Empty state: "No employees onboarded yet"

**Definition of Done:**
- [ ] CSV bulk onboarding for 100+ employees
- [ ] Aggregate metrics: active users, applications, interviews, placements
- [ ] Per-employee autonomy overrides functional
- [ ] ROI calculation methodology documented

---

## Epic Dependencies

```
Epic 0: Platform Foundation
    │
    ├── Epic 1: Lightning Onboarding
    │       │
    │       └── Epic 2: Preference Configuration
    │               │
    │               └── Epic 3: Agent Orchestration Core
    │                       │
    │                       ├── Epic 4: AI-Powered Job Matching
    │                       │       │
    │                       │       ├── Epic 5: Application Automation
    │                       │       │
    │                       │       └── Epic 7: H1B Specialist Experience
    │                       │
    │                       ├── Epic 6: Pipeline & Privacy
    │                       │       │
    │                       │       └── Epic 8: Interview Preparation (P2)
    │                       │
    │                       └── Epic 9: Network Building (P2)
    │
    └── Epic 10: Enterprise Administration (parallel track)
```

---

## MVP Slice Definition

**MVP = Epic 0 + Epic 1 + Epic 2 + Epic 3 + Epic 4 + Epic 5 (partial) + Epic 6 (partial) + Epic 7**

| Epic | MVP Stories | Post-MVP Stories |
|------|-------------|------------------|
| Epic 0 | 12-15 | - |
| Epic 1 | 5-6 | - |
| Epic 2 | 6-8 | - |
| Epic 3 | 11-14 | - |
| Epic 4 | 8-10 | - |
| Epic 5 | 12-15 (F5 only) | 4-6 (F9, F10) |
| Epic 6 | 8-10 (F6 only) | 8-10 (F11, F12) |
| Epic 7 | 8-10 | - |
| **MVP Total** | **70-88** | - |
| Epic 8 | - | 6-8 |
| Epic 9 | - | 6-8 |
| Epic 10 | - | 10-12 |
| **Full Total** | **70-88** | **34-44** |

**Total Estimated Stories: 104-132**

---

## Step 2 Complete: Epic Structure Designed

**Summary:**
- **11 Epics** (Epic 0-10) covering all 15 FRs and 9 NFRs
- **16 Party Mode enhancements** incorporated
- **Epic dependencies** documented
- **MVP slice** defined (~70-88 stories)
- **Definition of Done** per epic

**Key Enhancements Applied:**
1. ✅ Epic 0: Platform Foundation added
2. ✅ Epic 1/2 split (Lightning Onboarding + Preferences)
3. ✅ Epic 3 renamed to "Agent Orchestration Core"
4. ✅ Epic 4 renamed to "AI-Powered Job Matching"
5. ✅ Epic 5 integration stories added
6. ✅ Epic 6 merged with Stealth Mode (Pipeline & Privacy)
7. ✅ Epic 7 data freshness infrastructure included
8. ✅ Epic 8/9 split (Interview Prep + Network Building)
9. ✅ Dependencies documented with diagram
10. ✅ NFR coverage map added
11. ✅ Story count estimates per epic
12. ✅ MVP slice defined
13. ✅ Definition of Done per epic
14. ✅ First briefing preview in Epic 1
15. ✅ Empty state stories in all epics
16. ✅ Swipe interface in Epic 4

---

---

# EPIC STORIES

---

## Epic 0: Platform Foundation

**Goal:** Infrastructure enabling all subsequent epics - users benefit from fast, secure, observable platform.

**Covers:** NFR1-NFR4, NFR6, NFR8-NFR9, Tech2, Tech4, Tech5, Tech8, Tech9
**Party Mode Enhancements:** 14
**Total Stories:** 15

**Definition of Done (applies to all stories):**
- All acceptance criteria pass
- Code reviewed and approved
- Unit tests written (>80% line, >70% branch coverage)
- Deployed to staging environment
- No critical security vulnerabilities

---

### Story 0.1: Database Schema Foundation

As a **developer**,
I want **the core database schema deployed with all foundational tables**,
So that **subsequent features have persistent storage available**.

**Acceptance Criteria:**

**Given** a fresh Supabase instance
**When** migrations are applied
**Then** the following tables exist with proper relationships:
- `users` (id, email, clerk_id, tier, timezone, created_at, updated_at)
- `profiles` (id, user_id, linkedin_data, skills[], experience[], education[])
- `jobs` (id, source, url, title, company, description, h1b_sponsor_status)
- `applications` (id, user_id, job_id, status, applied_at, resume_version_id)
- `matches` (id, user_id, job_id, score, rationale, status)
- `documents` (id, user_id, type, version, content, job_id)
- `agent_actions` (id, user_id, agent_type, action, rationale, status, timestamp)
- `agent_outputs` (id, agent_type, user_id, schema_version, output JSONB)
**And** all tables have UUID primary keys with `gen_random_uuid()` defaults
**And** `created_at` and `updated_at` timestamps are auto-populated
**And** soft-delete columns (`deleted_at`, `deleted_by`, `deletion_reason`) exist on user-facing tables
**And** `users.timezone` defaults to 'UTC'
**And** migration rollback is tested and verified working

---

### Story 0.2: Row-Level Security Policies

As a **user**,
I want **my data protected so only I can access it**,
So that **my career information remains private**.

**Acceptance Criteria:**

**Given** RLS is enabled on all user-scoped tables
**When** a user queries `profiles` table
**Then** only rows where `user_id = auth.uid()` are returned
**And** development bypass policy exists with environment safeguards
**And** policy violations return 403 Forbidden, not empty results
**And** RLS policies exist for: profiles, applications, matches, documents, agent_actions, agent_outputs

---

### Story 0.3: Clerk Authentication Integration ⚡ (Parallelizable with 0.4)

As a **user**,
I want **to sign up and log in using my LinkedIn account**,
So that **I can access JobPilot quickly without creating another password**.

**Acceptance Criteria:**

**Given** I am on the login page
**When** I click "Continue with LinkedIn"
**Then** I am redirected to LinkedIn OAuth flow
**And** upon successful auth, a JWT token is issued
**And** my `users` record is created or updated
**And** I am redirected to the onboarding flow (new users) or dashboard (returning users)
**And** JWT tokens auto-refresh before expiration (within 5 minutes of expiry)
**And** refresh token rotation is enabled for security

---

### Story 0.4: API Foundation with Versioning ⚡ (Parallelizable with 0.3)

As a **developer**,
I want **a versioned REST API structure with health checks and rate limiting**,
So that **the backend is production-ready and maintainable**.

**Acceptance Criteria:**

**Given** the FastAPI application is running
**When** I call `GET /api/v1/health`
**Then** I receive `{"status": "healthy", "version": "1.0.0"}`
**And** all endpoints are prefixed with `/api/v1/`
**And** CORS is configured for frontend origins
**And** JWT authentication middleware is active on protected routes
**And** rate limiting middleware enforces tier-based limits:
- Free: 100 requests/hour
- Pro: 1000 requests/hour
- H1B Pro: 1000 requests/hour
**And** rate limit exceeded returns 429 Too Many Requests with retry-after header

---

### Story 0.5: Redis Cache and Queue Setup

As a **system**,
I want **Redis configured for caching, job queuing, and real-time agent control**,
So that **agent tasks can be scheduled and emergency brake functions instantly**.

**Acceptance Criteria:**

**Given** Redis is deployed and connected
**When** a cache operation is performed
**Then** data is stored with configurable TTL
**And** Celery can connect to Redis as broker
**And** connection pooling is configured for performance
**And** health check includes Redis connectivity status
**And** pub/sub channels exist for agent control:
- `agent:pause:{user_id}` - emergency brake signal
- `agent:resume:{user_id}` - resume signal
- `agent:status:{user_id}` - status updates

---

### Story 0.6: Celery Worker Infrastructure

As a **system**,
I want **Celery workers configured for background task processing with reliability guarantees**,
So that **agent tasks run asynchronously without blocking user requests**.

**Acceptance Criteria:**

**Given** Celery workers are deployed
**When** a task is enqueued
**Then** a worker picks up and executes the task
**And** task timeout is set to 5 minutes (hard limit), 4 minutes (soft limit)
**And** heartbeat monitoring is active (30-second intervals)
**And** failed tasks are retried up to 3 times with exponential backoff
**And** zombie task cleanup runs every 5 minutes
**And** tasks failing after max retries are sent to dead letter queue
**And** dead letter queue is monitored with alerting

---

### Story 0.7: OpenTelemetry Tracing Setup

As an **operator**,
I want **distributed tracing for all API requests and agent executions**,
So that **I can diagnose performance issues and errors**.

**Acceptance Criteria:**

**Given** OpenTelemetry is configured
**When** an API request is processed
**Then** a trace span is created with request metadata
**And** Celery tasks create child spans
**And** agent step execution creates nested spans with step names
**And** traces include: user_id, agent_type, duration, success/failure
**And** traces are exportable to observability backend (Jaeger/Honeycomb)

---

### Story 0.8: LLM Cost Tracking Middleware

As a **business owner**,
I want **per-request LLM cost tracking**,
So that **I can monitor costs and maintain margin targets**.

**Acceptance Criteria:**

**Given** an LLM request is made
**When** the request completes
**Then** token count (input + output) and cost are recorded with user_id
**And** costs are aggregated per user per month in Redis
**And** alert fires when user reaches 80% of $6 monthly budget
**And** cost dashboard endpoint `GET /api/v1/admin/llm-costs` returns:
- Total cost today/month
- Per-user breakdown
- Per-agent breakdown
- Projected month-end cost

---

### Story 0.9: Error Tracking Integration

As an **operator**,
I want **automated error tracking with alerts**,
So that **I'm notified of issues before users report them**.

**Acceptance Criteria:**

**Given** Sentry (or equivalent) is configured
**When** an unhandled exception occurs
**Then** the error is captured with stack trace and context
**And** user_id is attached (without PII like email)
**And** error rate exceeding 1% triggers PagerDuty alert
**And** errors are grouped by type for triage
**And** source maps are uploaded for frontend error debugging

---

### Story 0.10: WebSocket Infrastructure

As a **user**,
I want **real-time updates when agents complete actions**,
So that **I see activity without refreshing the page**.

**Acceptance Criteria:**

**Given** I have a valid JWT token
**When** I connect to WebSocket at `/api/v1/ws/agents/{user_id}`
**Then** connection is authenticated using JWT token
**And** when an agent completes a step, I receive: `{type: "agent.step_completed", data: {...}}`
**And** connection reconnects automatically on disconnect (exponential backoff)
**And** missed events are recoverable via REST fallback `GET /api/v1/agents/events?since={timestamp}`
**And** unauthenticated connections are rejected with 401

---

### Story 0.11: Email Service Configuration

As a **user**,
I want **to receive transactional emails from JobPilot**,
So that **I get briefings and notifications in my inbox**.

**Acceptance Criteria:**

**Given** SendGrid is configured
**When** a briefing email is triggered
**Then** email is delivered within 5 minutes
**And** emails use branded HTML templates
**And** bounce/complaint webhooks update user preferences
**And** unsubscribe link is included per CAN-SPAM
**And** email events (delivered, opened, clicked) are logged for analytics

---

### Story 0.12: CI/CD Pipeline with Automated Tests

As a **developer**,
I want **automated testing and deployment on merge**,
So that **code quality is enforced and deployments are safe**.

**Acceptance Criteria:**

**Given** a PR is merged to main
**When** CI pipeline runs
**Then** pytest runs all backend tests with coverage thresholds:
- >80% line coverage required
- >70% branch coverage required
**And** frontend tests run (Jest + React Testing Library)
**And** Schemathesis validates API contracts against OpenAPI spec
**And** successful builds auto-deploy to staging
**And** production deploys require manual approval
**And** failed tests block merge

---

### Story 0.13: Supabase Storage Configuration

As a **user**,
I want **to upload and store my resume and documents securely**,
So that **the system can tailor my materials for job applications**.

**Acceptance Criteria:**

**Given** Supabase Storage is configured
**When** I upload a resume file (PDF, DOCX)
**Then** the file is stored in a private bucket
**And** file is associated with my user_id
**And** maximum file size is 10MB
**And** only authenticated users can access their own files
**And** signed URLs are generated for temporary access (15 minute expiry)
**And** virus scanning is enabled on upload

---

### Story 0.14: Performance Baseline Establishment

As an **operator**,
I want **performance baselines established and monitored**,
So that **I can detect regressions and verify NFR1 targets**.

**Acceptance Criteria:**

**Given** the application is deployed to staging
**When** load tests run (k6 or similar)
**Then** baseline metrics are captured:
- Page load time (target: <2s)
- API response time p95 (target: <500ms)
- Agent response time (target: <30s)
**And** baselines are stored for comparison
**And** CI pipeline includes performance regression check
**And** >20% regression from baseline fails the build

---

### Story 0.15: GDPR Data Portability Endpoints

As a **user**,
I want **to export all my data and request account deletion**,
So that **I have control over my personal information per GDPR/CCPA**.

**Acceptance Criteria:**

**Given** I am authenticated
**When** I call `GET /api/v1/users/me/export`
**Then** I receive a JSON file containing all my data:
- Profile information
- Applications history
- Documents (as download links)
- Agent actions log
**And** export is generated asynchronously with email notification when ready

**Given** I am authenticated
**When** I call `DELETE /api/v1/users/me`
**Then** my account is scheduled for deletion within 30 days
**And** I receive confirmation email
**And** I can cancel deletion within 14 days
**And** after 30 days, all PII is permanently deleted
**And** audit logs are retained per compliance (anonymized)

---

## Epic 0 Complete ✅

| Metric | Value |
|--------|-------|
| Total Stories | 15 |
| Party Mode Enhancements | 14 |
| NFRs Covered | NFR1-6, NFR8-9 |
| Parallelizable Stories | 0.3 ⚡ 0.4 |

---

---

## Epic 1: Lightning Onboarding

**Goal:** Users can sign up and have a complete profile extracted from LinkedIn URL or resume in 30 seconds.

**FR Covered:** F1 (Zero-Setup Onboarding)
**Dependencies:** Epic 0
**Total Stories:** 6

**Definition of Done (applies to all stories):**
- All acceptance criteria pass
- Code reviewed and approved
- Unit tests written (>80% line, >70% branch coverage)
- Deployed to staging environment
- Accessibility: keyboard navigation, screen reader tested

---

### Story 1.1: LinkedIn URL Profile Extraction

As a **new user**,
I want **to paste my LinkedIn profile URL and have my profile auto-populated**,
So that **I can complete onboarding in 30 seconds without manual data entry**.

**Acceptance Criteria:**

**Given** I am on the onboarding screen
**When** I paste a valid LinkedIn URL (e.g., `linkedin.com/in/username`)
**Then** the system extracts and displays:
- Name and headline
- Current and past job titles
- Companies worked at
- Skills list
- Education history
**And** extraction completes within 60 seconds
**And** a loading indicator shows progress
**And** I can edit any extracted field before confirming
**And** invalid URLs show clear error message: "Please enter a valid LinkedIn profile URL"

---

### Story 1.2: Resume File Upload and Parsing

As a **new user**,
I want **to upload my resume and have my profile auto-populated**,
So that **I can onboard quickly if I don't want to use LinkedIn**.

**Acceptance Criteria:**

**Given** I am on the onboarding screen
**When** I upload a resume file (PDF or DOCX, max 10MB)
**Then** the system extracts and displays:
- Name and contact info
- Work experience with dates
- Skills mentioned
- Education
**And** extraction completes within 60 seconds
**And** original file is stored in Supabase Storage
**And** unsupported file types show: "Please upload a PDF or Word document"
**And** files over 10MB show: "File too large. Maximum size is 10MB"

---

### Story 1.3: Profile Review and Correction UI

As a **new user**,
I want **to review and correct my extracted profile before proceeding**,
So that **my profile accurately represents my experience**.

**Acceptance Criteria:**

**Given** my profile has been extracted (from LinkedIn or resume)
**When** I view the profile review screen
**Then** all extracted fields are displayed in editable form
**And** I can add missing information (skills, experience)
**And** I can remove incorrect extractions
**And** changes are highlighted visually
**And** "Confirm Profile" button saves to database
**And** I cannot proceed until at least name and one work experience exist

---

### Story 1.4: First Briefing Preview (Magic Moment)

As a **new user**,
I want **to see a preview of what my daily briefing will look like**,
So that **I understand the value I'll receive before completing onboarding**.

**Acceptance Criteria:**

**Given** I have confirmed my profile
**When** I reach the briefing preview step
**Then** I see a sample briefing with:
- "Good morning, [Name]!" personalized greeting
- 3 placeholder job matches (or real matches if available)
- "Your agent found 3 matches while you were away" message
- Preview of approval actions
**And** the preview is clearly labeled as "Preview - Your first real briefing arrives tomorrow"
**And** "Continue" button proceeds to preference wizard or dashboard

---

### Story 1.5: Onboarding Empty State

As a **new user**,
I want **encouraging feedback if extraction is slow or yields limited results**,
So that **I don't abandon onboarding due to uncertainty**.

**Acceptance Criteria:**

**Given** I have submitted a LinkedIn URL or resume
**When** extraction takes longer than 30 seconds
**Then** I see: "Your agent is reading your profile... this usually takes about a minute"
**And** progress indicator shows activity

**Given** extraction completes with limited data (<3 fields populated)
**When** I view the profile review screen
**Then** I see: "We found some info! Help your agent by adding more details below"
**And** suggested fields to complete are highlighted
**And** I can still proceed with minimal data (name required minimum)

---

### Story 1.6: Onboarding Analytics Events

As a **product manager**,
I want **analytics events tracked throughout onboarding**,
So that **I can measure funnel conversion and identify drop-off points**.

**Acceptance Criteria:**

**Given** a user goes through onboarding
**When** they complete each step
**Then** the following events are tracked:
- `onboarding_started` (with source: LinkedIn/resume)
- `profile_extraction_completed` (with field_count, duration_ms)
- `profile_confirmed` (with fields_edited_count)
- `briefing_preview_viewed`
- `onboarding_completed` (with total_duration_ms)
**And** events include user_id and session_id
**And** drop-off events tracked if user abandons mid-step

---

## Epic 1 Complete ✅

| Metric | Value |
|--------|-------|
| Total Stories | 6 |
| FR Covered | F1 |
| Key Outcome | 30-second onboarding |

---

---

## Epic 2: Preference Configuration

**Goal:** Users can configure job preferences, locations, salary expectations, and deal-breakers that guide agent behavior.

**FR Covered:** F2 (Preference Wizard)
**Dependencies:** Epic 0, Epic 1
**Total Stories:** 8

**Definition of Done (applies to all stories):**
- All acceptance criteria pass
- Code reviewed and approved
- Unit tests written (>80% line, >70% branch coverage)
- Deployed to staging environment
- Accessibility: keyboard navigation, screen reader tested

---

### Story 2.1: Job Type and Title Preferences

As a **user**,
I want **to specify what types of jobs I'm looking for**,
So that **my agent only shows me relevant opportunities**.

**Acceptance Criteria:**

**Given** I am in the preference wizard
**When** I reach the job type step
**Then** I can select from job categories (Engineering, Product, Design, etc.)
**And** I can specify target job titles (e.g., "Senior Software Engineer", "Staff Engineer")
**And** I can indicate seniority level preference (Entry, Mid, Senior, Staff, Principal)
**And** selections are saved to my profile
**And** I can select multiple titles and levels

---

### Story 2.2: Location and Remote Work Settings

As a **user**,
I want **to specify where I'm willing to work**,
So that **my agent filters out jobs in undesirable locations**.

**Acceptance Criteria:**

**Given** I am in the preference wizard
**When** I reach the location step
**Then** I can select work arrangement:
- Remote only
- Hybrid (specify days)
- On-site only
- Open to all
**And** I can add target cities/metro areas (autocomplete from list)
**And** I can specify "willing to relocate" with target locations
**And** I can exclude specific locations ("Not California")
**And** selections are saved to my profile

---

### Story 2.3: Salary Range Configuration

As a **user**,
I want **to specify my salary expectations**,
So that **my agent doesn't waste time on underpaying opportunities**.

**Acceptance Criteria:**

**Given** I am in the preference wizard
**When** I reach the salary step
**Then** I can set minimum acceptable salary (USD)
**And** I can set target/ideal salary
**And** I can indicate flexibility ("firm minimum" vs "negotiable")
**And** I can specify total comp preference (base only vs including equity/bonus)
**And** salary is stored but never shared externally
**And** jobs below minimum are deprioritized but not hidden (user choice)

---

### Story 2.4: Deal-Breaker Definition

As a **user**,
I want **to define absolute deal-breakers that my agent must respect**,
So that **I never waste time on fundamentally incompatible opportunities**.

**Acceptance Criteria:**

**Given** I am in the preference wizard
**When** I reach the deal-breakers step
**Then** I can define "must have" requirements:
- Minimum company size
- Industry preferences
- Specific benefits (401k match, unlimited PTO, etc.)
**And** I can define "never" rules:
- Excluded companies (competitors, bad experiences)
- Excluded industries (tobacco, gambling, etc.)
- Excluded job characteristics (travel >25%, on-call)
**And** deal-breakers are enforced strictly by agent (no exceptions)
**And** I see warning: "Jobs violating deal-breakers will be automatically rejected"

---

### Story 2.5: H1B Sponsorship Requirement

As an **international job seeker**,
I want **to indicate my visa sponsorship needs**,
So that **my agent prioritizes companies that sponsor visas**.

**Acceptance Criteria:**

**Given** I am in the preference wizard
**When** I reach the visa step (shown if user indicates non-citizen)
**Then** I can specify:
- Current visa type (H1B, OPT, L1, etc.)
- Visa expiration date (for urgency signals)
- "Requires H1B sponsorship" toggle
- "Requires green card sponsorship" toggle
**And** if sponsorship required, jobs without verified sponsorship are flagged
**And** H1B users are prompted to upgrade to H1B Pro tier

---

### Story 2.6: Autonomy Level Selection

As a **user**,
I want **to choose how much my agent can do without my approval**,
So that **I'm comfortable with the level of automation**.

**Acceptance Criteria:**

**Given** I am in the preference wizard
**When** I reach the autonomy step
**Then** I see clear descriptions of each level:
- **L0 (Suggestions Only)**: Agent suggests, you do everything
- **L1 (Draft Mode)**: Agent drafts, you review and send
- **L2 (Supervised)**: Agent acts, you approve daily digest
- **L3 (Autonomous)**: Agent acts freely within deal-breakers
**And** I can select my comfort level
**And** selection affects available features and pricing tier
**And** I can change autonomy level later in settings

---

### Story 2.7: Preference Summary and Confirmation

As a **user**,
I want **to review all my preferences before finalizing**,
So that **I can catch any mistakes before my agent starts working**.

**Acceptance Criteria:**

**Given** I have completed all preference steps
**When** I reach the summary screen
**Then** I see all preferences in a scannable format:
- Job targets
- Locations
- Salary range
- Deal-breakers
- Autonomy level
**And** I can edit any section by clicking on it
**And** "Start My Agent" button finalizes setup
**And** confirmation message: "Your agent is now active! Check back tomorrow for your first briefing."

---

### Story 2.8: Preference Empty States

As a **user**,
I want **guidance if I skip optional preferences**,
So that **I understand how it affects my agent's behavior**.

**Acceptance Criteria:**

**Given** I skip a preference step (e.g., no salary specified)
**When** I reach the summary screen
**Then** skipped sections show: "Not specified - agent will consider all options"
**And** I see a tip: "The more you tell your agent, the better your matches"
**And** I can proceed without all preferences filled
**And** I can always update preferences later in settings

---

## Epic 2 Complete ✅

| Metric | Value |
|--------|-------|
| Total Stories | 8 |
| FR Covered | F2 |
| Key Outcome | Preference-driven agent behavior |

---

---

## Epic 3: Agent Orchestration Core

**Goal:** Users receive daily briefings summarizing agent activity and can pause all agents instantly with emergency brake.

**FRs Covered:** F3 (Daily Briefing), F7 (Emergency Brake)
**Dependencies:** Epic 0, Epic 1, Epic 2
**Total Stories:** 11

**Definition of Done (applies to all stories):**
- All acceptance criteria pass
- Code reviewed and approved
- Unit tests written (>80% line, >70% branch coverage)
- Deployed to staging environment
- Agent outputs validated against schema

---

### Story 3.1: Orchestrator Agent Infrastructure

As a **system**,
I want **a central orchestrator that coordinates all specialized agents**,
So that **agent activities are synchronized and user context is shared**.

**Acceptance Criteria:**

**Given** the orchestrator is deployed
**When** a user's scheduled tasks are due
**Then** the orchestrator routes tasks to appropriate specialized agents
**And** shared memory (user profile, preferences, history) is accessible to all agents
**And** orchestrator enforces autonomy level gates before agent actions
**And** all agent outputs include required fields: action, rationale, confidence, alternatives_considered
**And** orchestrator logs all routing decisions for debugging

---

### Story 3.2: Daily Briefing Generation Pipeline

As a **user**,
I want **my daily briefing compiled from all agent activities**,
So that **I see a complete summary of what happened overnight**.

**Acceptance Criteria:**

**Given** it's time to generate a user's briefing
**When** the orchestrator compiles the briefing
**Then** it aggregates:
- New job matches from Job Scout Agent
- Applications sent (if autonomy allows)
- Pipeline status changes
- Follow-up reminders due
- Any errors or issues
**And** briefing is structured with sections: Summary → Actions Needed → New Matches → Activity Log
**And** briefing generation completes within 2 minutes
**And** briefing is stored in database with timestamp

---

### Story 3.3: Briefing Delivery - In-App

As a **user**,
I want **to see my daily briefing when I open JobPilot**,
So that **I can quickly review agent activity**.

**Acceptance Criteria:**

**Given** I open the JobPilot dashboard
**When** I have an unread briefing
**Then** the briefing is prominently displayed as the first thing I see
**And** briefing shows personalized greeting: "Good morning, [Name]!"
**And** summary cards show key metrics (new matches, pending approvals, pipeline updates)
**And** I can expand sections for detail
**And** "Mark as Read" action clears the notification badge
**And** I can access previous briefings from history

---

### Story 3.4: Briefing Delivery - Email

As a **user**,
I want **my daily briefing delivered to my email**,
So that **I can review it without logging into the app**.

**Acceptance Criteria:**

**Given** my briefing delivery preference includes email
**When** my briefing is generated
**Then** an email is sent within 15 minutes of configured time
**And** email includes full briefing content in readable HTML format
**And** email includes quick action buttons (Approve All, View in App)
**And** email respects user's timezone for delivery time
**And** unsubscribe link allows opting out of email delivery

---

### Story 3.5: User-Configurable Briefing Time

As a **user**,
I want **to choose when I receive my daily briefing**,
So that **it arrives when I'm ready to review it**.

**Acceptance Criteria:**

**Given** I am in settings
**When** I configure briefing delivery time
**Then** I can select hour (dropdown) in my local timezone
**And** I can select delivery channels (in-app, email, both)
**And** default is 8:00 AM local time
**And** changes take effect from the next day
**And** I see my timezone displayed for clarity

---

### Story 3.6: Emergency Brake Button

As a **user**,
I want **a prominent button to instantly pause all agent activity**,
So that **I can stop everything if something goes wrong**.

**Acceptance Criteria:**

**Given** I am anywhere in the JobPilot app
**When** I look at the header/navigation
**Then** I see an "Emergency Brake" button (red, always visible)
**And** button shows current state: "Agents Active" or "Agents Paused"

**Given** agents are active
**When** I tap the Emergency Brake button
**Then** a pause signal is sent immediately (no confirmation dialog - speed critical)
**And** UI updates to "Pausing..." state
**And** all agents stop at their next checkpoint within 30 seconds
**And** UI shows "Agents Paused" with timestamp

---

### Story 3.7: Emergency Brake State Machine

As a **system**,
I want **the emergency brake to handle in-flight operations gracefully**,
So that **pausing doesn't cause data corruption or lost work**.

**Acceptance Criteria:**

**Given** agents are running tasks when brake is pulled
**When** the pause signal is received
**Then** state transitions: RUNNING → PAUSING → PAUSED
**And** in-flight tasks complete their current step before pausing
**And** tasks that can't pause cleanly within 2 minutes are force-terminated
**And** partial state is saved for resume
**And** if any tasks fail to pause, state shows "PARTIAL" with list of stuck tasks

---

### Story 3.8: Resume Agents After Pause

As a **user**,
I want **to resume my agents after pausing them**,
So that **they can continue working for me**.

**Acceptance Criteria:**

**Given** agents are paused
**When** I tap the "Resume Agents" button
**Then** a resume signal is sent
**And** agents pick up from where they left off
**And** UI shows "Resuming..." then "Agents Active"
**And** any tasks that were interrupted are re-queued
**And** briefing notes: "Agents resumed at [time] after [duration] pause"

---

### Story 3.9: Agent Activity Feed

As a **user**,
I want **to see real-time activity when agents are working**,
So that **I know the system is active and what's happening**.

**Acceptance Criteria:**

**Given** I am on the dashboard
**When** agents are performing tasks
**Then** I see a live activity feed showing:
- "Job Scout is searching Indeed..."
- "Resume Agent is tailoring for [Company]..."
- "Application sent to [Company]!"
**And** feed updates in real-time via WebSocket
**And** I can click any item to see details
**And** feed shows last 20 activities with "View All" for history

---

### Story 3.10: Briefing Empty State

As a **new user**,
I want **an encouraging message if my first briefing has no results**,
So that **I understand the system is working and results are coming**.

**Acceptance Criteria:**

**Given** it's my first briefing
**When** the briefing has zero job matches
**Then** I see: "Your agent is still learning your preferences. Check back tomorrow!"
**And** I see tips to improve matching: "Add more skills to your profile"
**And** I see the agent activity showing work was done (searches performed)
**And** I don't see an empty state that looks like an error

---

### Story 3.11: Briefing Reliability - Fallback

As a **user**,
I want **to always receive some briefing even if systems have issues**,
So that **I'm never left wondering what's happening**.

**Acceptance Criteria:**

**Given** briefing generation fails or times out
**When** the scheduled delivery time passes
**Then** a "lite briefing" is generated from cached data
**And** lite briefing shows: "We're having some trouble today. Here's what we know:"
**And** lite briefing includes last known pipeline status and any cached matches
**And** operations team is alerted to the failure
**And** full briefing is attempted again in 1 hour

---

## Epic 3 Complete ✅

| Metric | Value |
|--------|-------|
| Total Stories | 11 |
| FRs Covered | F3, F7 |
| Key Outcome | Daily briefings + Emergency control |

---

---

## Epic 4: AI-Powered Job Matching

**Goal:** Users wake up to AI-curated job matches with scores, rationale, and swipe-to-review interface.

**FR Covered:** F4 (Job Scout Agent)
**Dependencies:** Epic 0, Epic 1, Epic 2, Epic 3
**Total Stories:** 10

**Definition of Done (applies to all stories):**
- All acceptance criteria pass
- Code reviewed and approved
- Unit tests written (>80% line, >70% branch coverage)
- Deployed to staging environment
- Swipe gestures tested on mobile devices

---

### Story 4.1: Job Scout Agent Implementation

As a **system**,
I want **a Job Scout Agent that monitors job boards 24/7**,
So that **users receive fresh job matches without manual searching**.

**Acceptance Criteria:**

**Given** the Job Scout Agent is deployed
**When** scheduled to run (nightly batch)
**Then** it queries configured job sources for each user
**And** filters jobs based on user preferences (title, location, salary)
**And** excludes jobs from blocklisted companies
**And** stores raw job data in `jobs` table
**And** creates `matches` records linking users to relevant jobs
**And** agent outputs include rationale for why each job was selected

---

### Story 4.2: Indeed Job Board Integration

As a **Job Scout Agent**,
I want **to fetch jobs from Indeed**,
So that **users have access to a major job board's listings**.

**Acceptance Criteria:**

**Given** Indeed integration is configured
**When** the agent searches for jobs matching user preferences
**Then** jobs are fetched via Indeed's available methods (API or scraping)
**And** rate limits are respected (configurable delay between requests)
**And** job data includes: title, company, location, salary (if available), description, URL
**And** duplicate jobs are detected and skipped
**And** errors are logged but don't stop the entire batch

---

### Story 4.3: LinkedIn Job Scraping Integration

As a **Job Scout Agent**,
I want **to fetch jobs from LinkedIn job postings**,
So that **users see opportunities from professional network**.

**Acceptance Criteria:**

**Given** LinkedIn job search is configured
**When** the agent searches for jobs
**Then** public job listings are scraped (respecting ToS limitations)
**And** job data includes: title, company, location, description, posted date
**And** LinkedIn-specific fields captured: applicant count, company size
**And** rate limiting prevents detection/blocking
**And** scraping failures gracefully degrade (skip LinkedIn, continue with other sources)

---

### Story 4.4: AI Job Matching Algorithm

As a **user**,
I want **jobs scored by AI based on my profile and preferences**,
So that **I see the best matches first**.

**Acceptance Criteria:**

**Given** a job has been fetched
**When** the matching algorithm runs
**Then** job receives a score from 0-100 based on:
- Title match to preferences (weighted heavily)
- Skills overlap with job requirements
- Location match
- Salary range compatibility
- Company size preference
- Seniority level alignment
**And** jobs scoring below 40 are not shown (configurable threshold)
**And** scoring completes within 5 seconds per job
**And** algorithm uses GPT-3.5 for cost efficiency

---

### Story 4.5: Match Rationale Generation

As a **user**,
I want **to understand why each job was matched to me**,
So that **I can trust the agent's recommendations**.

**Acceptance Criteria:**

**Given** a job has been matched
**When** I view the job details
**Then** I see "Why this match?" section with:
- Top 3 reasons this job fits my profile
- Any potential concerns or gaps
- Confidence level (High/Medium/Low)
**And** rationale is generated by LLM and stored with match
**And** rationale references specific parts of my profile ("Your 5 years at [Company] align with...")

---

### Story 4.6: Swipe Card Interface

As a **user**,
I want **to review job matches with a Tinder-style swipe interface**,
So that **I can quickly process many jobs with minimal effort**.

**Acceptance Criteria:**

**Given** I am viewing my job matches
**When** I see a job card
**Then** card displays: Company logo, Title, Location, Salary range, Match score
**And** I can swipe right to "Save" the job
**And** I can swipe left to "Dismiss" the job
**And** I can swipe up to "Apply Now" (if Pro+ tier)
**And** I can tap to expand for full details
**And** swipe gestures work on mobile touch and desktop drag
**And** keyboard shortcuts available: → Save, ← Dismiss, ↑ Apply, Space for details

---

### Story 4.7: Top Pick of the Day Feature

As a **user**,
I want **my single best match highlighted as "Top Pick"**,
So that **I don't miss the most promising opportunity**.

**Acceptance Criteria:**

**Given** I have job matches
**When** I view my briefing or jobs page
**Then** the highest-scoring job is featured as "Top Pick of the Day"
**And** Top Pick has enhanced styling (larger card, special badge)
**And** Top Pick shows extended rationale ("Here's why this is your #1 match today")
**And** only one Top Pick per day
**And** if I've already dismissed/saved it, next highest becomes Top Pick

---

### Story 4.8: Job Detail Expansion

As a **user**,
I want **to see full job details without leaving the swipe interface**,
So that **I can make informed decisions quickly**.

**Acceptance Criteria:**

**Given** I tap on a job card
**When** the card expands
**Then** I see full job description
**And** I see company information (size, industry, funding if available)
**And** I see H1B sponsorship status (if applicable to my profile)
**And** I see "Similar jobs you've saved/dismissed" for context
**And** I can collapse back to card view
**And** expand/collapse is animated smoothly

---

### Story 4.9: Preference Learning from Swipe Behavior

As a **user**,
I want **my agent to learn from my swipe patterns**,
So that **matching improves over time without manual preference updates**.

**Acceptance Criteria:**

**Given** I swipe on jobs over time
**When** patterns emerge (e.g., always dismiss jobs at Company X)
**Then** the agent detects and stores implicit preferences
**And** future scoring incorporates learned preferences
**And** agent may surface: "I noticed you dismiss [pattern]. Should I add this as a deal-breaker?"
**And** learning is transparent: Settings shows "Learned preferences" section
**And** I can override/delete any learned preference

---

### Story 4.10: Job Matches Empty State

As a **user**,
I want **helpful guidance when no jobs match my criteria**,
So that **I can adjust preferences rather than feel stuck**.

**Acceptance Criteria:**

**Given** I have zero job matches
**When** I view the jobs page
**Then** I see: "No matches today. Your agent is still searching!"
**And** I see suggestions:
- "Try expanding your location preferences"
- "Consider adding more job titles"
- "Relax salary requirements temporarily"
**And** I see a button to "Adjust Preferences"
**And** if I've been at zero matches for 3+ days, I receive proactive notification

---

## Epic 4 Complete ✅

| Metric | Value |
|--------|-------|
| Total Stories | 10 |
| FR Covered | F4 |
| Key Outcome | AI-powered job discovery with swipe UX |

---

---

## Epic 5: Application Automation

**Goal:** Users can have resumes auto-tailored, cover letters generated, and applications submitted with one-tap approval.

**FRs Covered:** F5 (Resume Agent), F9 (Apply Agent), F10 (Cover Letter Generator)
**Dependencies:** Epic 0, Epic 1, Epic 2, Epic 3, Epic 4
**Total Stories:** 14

**Definition of Done (applies to all stories):**
- All acceptance criteria pass
- Code reviewed and approved
- Unit tests written (>80% line, >70% branch coverage)
- Deployed to staging environment
- LLM cost per operation tracked

---

### Story 5.1: Resume Agent Implementation

As a **system**,
I want **a Resume Agent that tailors resumes for specific jobs**,
So that **users have optimized applications without manual editing**.

**Acceptance Criteria:**

**Given** the Resume Agent is deployed
**When** triggered for a saved job
**Then** it analyzes the job description requirements
**And** identifies relevant experience from user's master resume
**And** generates a tailored resume version
**And** stores the tailored version in `documents` table with job_id reference
**And** agent output includes rationale for each major change
**And** tailoring completes within 45 seconds

---

### Story 5.2: Master Resume Management

As a **user**,
I want **to upload and manage my master resume**,
So that **the agent has a complete source to tailor from**.

**Acceptance Criteria:**

**Given** I am in the Documents section
**When** I upload a resume
**Then** it becomes my "Master Resume"
**And** previous master is archived (not deleted)
**And** I can have only one active master at a time
**And** master resume is parsed and stored as structured data
**And** I can edit the parsed content directly in the UI
**And** I can download my master resume at any time

---

### Story 5.3: Resume Diff View

As a **user**,
I want **to see a side-by-side comparison of original vs tailored resume**,
So that **I understand and approve the changes**.

**Acceptance Criteria:**

**Given** a tailored resume has been generated
**When** I view the diff
**Then** I see two columns: "Master Resume" | "Tailored for [Company]"
**And** additions are highlighted in green
**And** removals are highlighted in red
**And** modifications are highlighted in yellow
**And** I can hover over any change to see rationale tooltip
**And** I can accept all, reject all, or selectively approve changes

---

### Story 5.4: ATS Optimization Logic

As a **user**,
I want **my tailored resume optimized for ATS systems**,
So that **my application passes automated screening**.

**Acceptance Criteria:**

**Given** a resume is being tailored
**When** ATS optimization runs
**Then** keywords from job description are incorporated naturally
**And** formatting follows ATS-friendly guidelines (no tables, simple fonts)
**And** an "ATS Score" is calculated (0-100) based on keyword match
**And** score below 70 triggers warning: "Consider adding: [missing keywords]"
**And** user can see ATS score before submitting application

---

### Story 5.5: Cover Letter Generator

As a **user**,
I want **AI-generated cover letters tailored to each job**,
So that **I can apply with personalized materials quickly**.

**Acceptance Criteria:**

**Given** I want to apply to a job
**When** I request a cover letter
**Then** agent generates a cover letter including:
- Company-specific opening (references recent news, mission, or role specifics)
- Relevant experience highlights from my profile
- Connection between my skills and job requirements
- Professional closing with call to action
**And** cover letter is 250-400 words
**And** generation completes within 30 seconds
**And** I can edit before sending

---

### Story 5.6: Cover Letter Personalization

As a **user**,
I want **cover letters to include company-specific details**,
So that **they don't feel generic or AI-generated**.

**Acceptance Criteria:**

**Given** a cover letter is being generated
**When** company research is available
**Then** the letter references:
- Company's recent news or achievements (if found)
- Company mission or values
- Specific team or product mentioned in job posting
- Why I'm interested in THIS company specifically
**And** generic fallback is used gracefully if research unavailable
**And** I see "Personalization sources" showing what research was used

---

### Story 5.7: Apply Agent Implementation

As a **system**,
I want **an Apply Agent that submits applications autonomously**,
So that **users can apply to jobs without manual form filling**.

**Acceptance Criteria:**

**Given** Apply Agent is deployed and user has Pro+ tier
**When** a job is approved for application
**Then** agent attempts to submit via:
1. Direct API integration (if available)
2. Browser automation (Indeed Easy Apply, LinkedIn)
3. Email to HR (fallback with resume attachment)
**And** application status is tracked in `applications` table
**And** success/failure is reported with details
**And** agent respects daily application limits per tier

---

### Story 5.8: Approval Queue for Applications

As a **user**,
I want **to review and approve applications before they're sent**,
So that **I maintain control over what goes out in my name**.

**Acceptance Criteria:**

**Given** I have L1 or L2 autonomy level
**When** applications are ready
**Then** they appear in my approval queue
**And** each item shows: Job title, Company, Tailored resume preview, Cover letter preview
**And** I can Approve, Reject, or Edit & Approve
**And** batch "Approve All" available for trusted users (with confirmation)
**And** queue shows count badge in navigation

---

### Story 5.9: One-Tap Approval from Briefing

As a **user**,
I want **to approve applications directly from my daily briefing**,
So that **I don't need to navigate to a separate queue**.

**Acceptance Criteria:**

**Given** I have pending approvals in my briefing
**When** I view an approval card
**Then** I see job summary and tailored materials preview
**And** I can tap "Approve" directly
**And** I can tap "View Details" to see full diff
**And** approval is instant with optimistic UI update
**And** 30-second undo window after approval

---

### Story 5.10: Application Submission Confirmation

As a **user**,
I want **confirmation when my application is successfully submitted**,
So that **I know the agent completed its task**.

**Acceptance Criteria:**

**Given** an application has been submitted
**When** the submission succeeds
**Then** I receive notification: "Applied to [Company] - [Job Title]!"
**And** application appears in my pipeline as "Applied"
**And** confirmation includes:
- Timestamp
- Materials sent (resume version, cover letter)
- Submission method used
**And** I can view the exact materials that were sent

---

### Story 5.11: Application Failure Handling

As a **user**,
I want **clear feedback when an application fails**,
So that **I can take manual action if needed**.

**Acceptance Criteria:**

**Given** an application submission fails
**When** error occurs
**Then** I receive notification: "Couldn't complete application to [Company]"
**And** error reason is provided:
- "Job posting expired"
- "Application requires additional fields"
- "Rate limited by job board"
**And** I see option: "Apply Manually" with link to job posting
**And** failed applications don't count against daily limits
**And** agent retries once automatically after 1 hour

---

### Story 5.12: Indeed Easy Apply Integration

As an **Apply Agent**,
I want **to submit applications via Indeed Easy Apply**,
So that **users can apply to Indeed jobs seamlessly**.

**Acceptance Criteria:**

**Given** a job is from Indeed with Easy Apply
**When** application is triggered
**Then** agent fills required fields from user profile
**And** attaches tailored resume
**And** handles common additional questions (work authorization, etc.)
**And** submission is confirmed via Indeed's confirmation page
**And** rate limits are respected (max 50/day via automation)

---

### Story 5.13: Application History and Materials

As a **user**,
I want **to view all past applications and materials sent**,
So that **I can track what I've applied to and reference past materials**.

**Acceptance Criteria:**

**Given** I navigate to Application History
**When** I view the list
**Then** I see all applications sorted by date
**And** each entry shows: Company, Title, Date, Status, Materials link
**And** I can click to view the exact resume and cover letter versions sent
**And** I can filter by status, date range, or company
**And** I can export history as CSV

---

### Story 5.14: Application Empty State

As a **user**,
I want **guidance when I haven't applied to any jobs yet**,
So that **I know how to get started**.

**Acceptance Criteria:**

**Given** I have zero applications
**When** I view the applications/pipeline page
**Then** I see: "No applications yet. Let's change that!"
**And** I see CTA: "Review your matches" linking to job matches
**And** I see tip: "Save jobs you like, then approve applications in your briefing"
**And** empty state feels encouraging, not critical

---

## Epic 5 Complete ✅

| Metric | Value |
|--------|-------|
| Total Stories | 14 |
| FRs Covered | F5, F9, F10 |
| Key Outcome | Automated application with user control |

---

---

## Epic 6: Pipeline & Privacy

**Goal:** Users can track all applications automatically, see status updates from email parsing, receive follow-up suggestions, and enable stealth mode for privacy.

**FRs Covered:** F6 (Pipeline Agent), F11 (Follow-up Agent), F12 (Stealth Mode)
**Dependencies:** Epic 0, Epic 1, Epic 2, Epic 3
**Total Stories:** 14

**Definition of Done (applies to all stories):**
- All acceptance criteria pass
- Code reviewed and approved
- Unit tests written (>80% line, >70% branch coverage)
- Deployed to staging environment
- Privacy features security-reviewed

---

### Story 6.1: Pipeline Agent Implementation

As a **system**,
I want **a Pipeline Agent that tracks application status from email**,
So that **users have auto-updating application tracking**.

**Acceptance Criteria:**

**Given** the Pipeline Agent is deployed
**When** connected to user's email
**Then** it scans for job-related emails (recruiters, ATS systems)
**And** detects status changes: rejection, interview request, offer
**And** updates `applications` table with new status
**And** creates audit trail of all detected changes
**And** agent outputs include confidence level and evidence (email snippet)

---

### Story 6.2: Gmail OAuth Integration

As a **user**,
I want **to connect my Gmail account for email parsing**,
So that **my pipeline updates automatically from recruiter emails**.

**Acceptance Criteria:**

**Given** I am in Settings > Integrations
**When** I click "Connect Gmail"
**Then** I am taken through Google OAuth flow
**And** I see exactly what permissions are requested (read-only, job-related)
**And** upon success, my Gmail is connected and status shows "Connected"
**And** I can disconnect at any time
**And** only emails matching job-related patterns are accessed (not personal email)

---

### Story 6.3: Outlook OAuth Integration

As a **user**,
I want **to connect my Outlook account for email parsing**,
So that **users with Microsoft email can use pipeline tracking**.

**Acceptance Criteria:**

**Given** I am in Settings > Integrations
**When** I click "Connect Outlook"
**Then** I am taken through Microsoft OAuth flow
**And** I see exactly what permissions are requested
**And** upon success, my Outlook is connected
**And** same functionality as Gmail integration
**And** supports both personal Outlook and Office 365

---

### Story 6.4: Email Status Detection

As a **Pipeline Agent**,
I want **to accurately detect application status from emails**,
So that **pipeline cards move automatically**.

**Acceptance Criteria:**

**Given** an email is received from a recruiter or ATS
**When** the agent analyzes it
**Then** it detects status with >90% accuracy:
- "We'd like to schedule an interview" → Interview
- "We've decided to move forward with other candidates" → Rejected
- "We're pleased to offer you" → Offer
- "Thank you for applying" → Applied (confirmation)
**And** ambiguous emails are flagged for user review rather than auto-moved
**And** confidence score is stored with each detection

---

### Story 6.5: Kanban Pipeline View

As a **user**,
I want **to see my applications in a Kanban board**,
So that **I can visualize my job search pipeline at a glance**.

**Acceptance Criteria:**

**Given** I navigate to Pipeline
**When** I view the Kanban board
**Then** I see columns: Saved → Applied → Interview → Offer → Closed
**And** each card shows: Company, Title, Days in stage, Last update
**And** I can drag cards between columns manually
**And** auto-moved cards show "Updated by agent" indicator
**And** clicking a card opens details panel
**And** column counts are displayed in headers

---

### Story 6.6: Pipeline List View

As a **user**,
I want **an alternative list view of my pipeline**,
So that **I can sort and filter applications efficiently**.

**Acceptance Criteria:**

**Given** I am in Pipeline
**When** I toggle to List View
**Then** I see a table with columns: Company, Title, Status, Applied Date, Last Update
**And** I can sort by any column
**And** I can filter by: Status, Date range, Company
**And** I can search by keyword
**And** bulk actions available: Archive, Change Status

---

### Story 6.7: Follow-up Agent Implementation

As a **system**,
I want **a Follow-up Agent that suggests timely follow-ups**,
So that **users don't miss opportunities due to lack of follow-up**.

**Acceptance Criteria:**

**Given** Follow-up Agent is deployed
**When** an application reaches a follow-up milestone
**Then** agent calculates optimal follow-up timing:
- After application: 5-7 business days
- After interview: 1-2 business days
- After no response: 2 weeks
**And** agent generates a draft follow-up message
**And** follow-up appears in user's briefing as "suggested action"
**And** agent respects user preference for follow-up aggressiveness

---

### Story 6.8: Follow-up Draft Generation

As a **user**,
I want **AI-generated follow-up email drafts**,
So that **I can follow up professionally without writing from scratch**.

**Acceptance Criteria:**

**Given** a follow-up is suggested
**When** I view the suggestion
**Then** I see a draft email with:
- Appropriate subject line
- Reference to original application
- Polite status inquiry
- Restatement of interest
**And** tone matches my communication style (if learned)
**And** I can edit before sending
**And** "Send" triggers email via connected account (or copies to clipboard)

---

### Story 6.9: Follow-up Tracking

As a **user**,
I want **to track whether I've followed up on applications**,
So that **I don't accidentally follow up twice or miss follow-ups**.

**Acceptance Criteria:**

**Given** I view a pipeline card
**When** follow-ups have occurred
**Then** I see follow-up history: Date, Message preview
**And** "Last followed up: X days ago" indicator
**And** if follow-up is overdue, card shows reminder badge
**And** I can mark "Followed up manually" to dismiss suggestion
**And** excessive follow-ups trigger warning: "You've followed up 3 times - consider moving on"

---

### Story 6.10: Stealth Mode Activation

As a **Career Insurance user**,
I want **to enable Stealth Mode to hide my job search**,
So that **my current employer cannot discover I'm looking**.

**Acceptance Criteria:**

**Given** I have Career Insurance tier
**When** I navigate to Settings > Privacy
**Then** I see "Stealth Mode" toggle
**And** enabling shows explanation of what it does
**And** upon activation:
- My profile is hidden from public search
- Employer blocklist is activated
- All agent actions avoid public visibility
**And** UI shows "Stealth Mode Active" badge

---

### Story 6.11: Employer Blocklist

As a **Stealth Mode user**,
I want **to blocklist companies that should never see my activity**,
So that **I'm protected from discovery by current/past employers**.

**Acceptance Criteria:**

**Given** Stealth Mode is active
**When** I manage my blocklist
**Then** I can add companies by name (autocomplete from database)
**And** blocklisted companies:
- Never appear in job matches
- Never receive applications
- Are excluded from any network outreach
**And** blocklist is encrypted at rest (AES-256)
**And** I can add notes: "Current employer", "Competitor", etc.

---

### Story 6.12: Privacy Proof Documentation

As a **Stealth Mode user**,
I want **proof that my employer is blocked**,
So that **I can trust the system is actually protecting me**.

**Acceptance Criteria:**

**Given** I have companies blocklisted
**When** I view Privacy Proof
**Then** I see a dashboard showing:
- List of blocklisted companies
- "Last checked: [timestamp]" for each
- "0 exposures to [Company]" verification
- Log of any blocked actions (e.g., "Blocked match from [Company]")
**And** I can download a privacy report
**And** system proactively alerts if blocklist rule is ever violated

---

### Story 6.13: Passive Mode Settings

As a **Career Insurance user**,
I want **to configure passive job search behavior**,
So that **I stay ready without active effort**.

**Acceptance Criteria:**

**Given** I am a Career Insurance subscriber
**When** I configure Passive Mode
**Then** I can set:
- Search frequency (weekly vs daily)
- Minimum match score to surface (higher threshold = fewer, better matches)
- Notification preferences (weekly digest vs immediate for hot matches)
- Auto-save threshold (automatically save jobs above X score)
**And** passive mode briefings are condensed weekly summaries
**And** I can "activate" to Sprint mode instantly if situation changes

---

### Story 6.14: Pipeline Empty State

As a **user**,
I want **encouraging guidance when my pipeline is empty**,
So that **I know how to get started tracking applications**.

**Acceptance Criteria:**

**Given** I have zero applications in pipeline
**When** I view the Pipeline page
**Then** I see: "Your pipeline is empty. Let's fill it up!"
**And** I see illustration of Kanban flow
**And** CTA: "Find your first matches" linking to job matches
**And** tip: "Connect your email to auto-track existing applications"
**And** link to import existing applications manually

---

## Epic 6 Complete ✅

| Metric | Value |
|--------|-------|
| Total Stories | 14 |
| FRs Covered | F6, F11, F12 |
| Key Outcome | Auto-tracking pipeline with privacy controls |

---

---

## Epic 7: H1B Specialist Experience

**Goal:** H1B visa holders can research any company's sponsorship history, approval rates, and get verified sponsor badges on job matches.

**FR Covered:** F8 (H1B Sponsor Database)
**Dependencies:** Epic 0, Epic 4
**Total Stories:** 10

**Definition of Done (applies to all stories):**
- All acceptance criteria pass
- Code reviewed and approved
- Unit tests written (>80% line, >70% branch coverage)
- Deployed to staging environment
- Data attribution verified for all sources

---

### Story 7.1: H1B Data Aggregation Pipeline

As a **system**,
I want **a scheduled pipeline that aggregates H1B sponsor data**,
So that **users have comprehensive, up-to-date visa sponsorship information**.

**Acceptance Criteria:**

**Given** the H1B data pipeline is deployed
**When** the scheduled job runs (weekly)
**Then** it fetches data from:
- H1BGrader
- MyVisaJobs
- USCIS public LCA data
**And** data is normalized and deduplicated by company
**And** 500,000+ company records are maintained
**And** data freshness timestamp is stored per source
**And** pipeline failures trigger ops alerts

---

### Story 7.2: H1BGrader Integration

As an **H1B data pipeline**,
I want **to fetch sponsor data from H1BGrader**,
So that **users see approval rates and petition history**.

**Acceptance Criteria:**

**Given** H1BGrader is accessible
**When** the scraper runs
**Then** it extracts per company:
- Number of H1B petitions filed
- Approval rate percentage
- Denial rate percentage
- Historical trend (increasing/decreasing)
**And** rate limiting prevents blocking
**And** data is attributed: "Source: H1BGrader"

---

### Story 7.3: MyVisaJobs Integration

As an **H1B data pipeline**,
I want **to fetch sponsor data from MyVisaJobs**,
So that **users see LCA wage data and job titles sponsored**.

**Acceptance Criteria:**

**Given** MyVisaJobs is accessible
**When** the scraper runs
**Then** it extracts per company:
- LCA filings by year
- Average wages for sponsored positions
- Job titles commonly sponsored
- Office locations with H1B activity
**And** data is attributed: "Source: MyVisaJobs"

---

### Story 7.4: USCIS Public Data Integration

As an **H1B data pipeline**,
I want **to incorporate official USCIS data**,
So that **sponsor information is verified against government records**.

**Acceptance Criteria:**

**Given** USCIS public data is available
**When** the pipeline processes it
**Then** it extracts:
- Official approval/denial statistics
- PERM/Green Card sponsorship history
- Any public compliance issues
**And** official data is prioritized over scraped data
**And** data is attributed: "Source: USCIS"

---

### Story 7.5: Sponsor Scorecard UI

As an **H1B job seeker**,
I want **to view a company's sponsorship scorecard**,
So that **I can assess visa sponsorship likelihood**.

**Acceptance Criteria:**

**Given** I view a job or company
**When** I access the H1B Scorecard
**Then** I see:
- Overall sponsor score (A+ to F grade)
- Approval rate with trend arrow (↑↓)
- Number of H1B employees
- Common sponsored job titles
- Average LCA wage for my role type
- Last petition date
**And** scorecard explains scoring methodology
**And** "Data last updated: [date]" is displayed

---

### Story 7.6: Approval Rate Visualization

As an **H1B job seeker**,
I want **to see approval rate trends visually**,
So that **I can identify companies improving or declining in sponsorship**.

**Acceptance Criteria:**

**Given** I view a company's H1B scorecard
**When** historical data is available
**Then** I see a line chart showing:
- Approval rate by year (last 5 years)
- Number of petitions by year
- Industry average comparison line
**And** chart is interactive (hover for details)
**And** red flag icon if approval rate declining significantly

---

### Story 7.7: Verified Sponsor Badge on Job Cards

As an **H1B job seeker**,
I want **job cards to show H1B sponsorship status**,
So that **I can quickly identify visa-friendly opportunities**.

**Acceptance Criteria:**

**Given** I am viewing job matches
**When** a company has verified H1B sponsorship history
**Then** job card displays "✓ Verified H1B Sponsor" badge
**And** badge color indicates strength:
- Green: 80%+ approval rate
- Yellow: 50-79% approval rate
- Orange: <50% approval rate
**And** tapping badge shows mini-scorecard tooltip
**And** jobs without sponsorship data show "Sponsorship Unknown"

---

### Story 7.8: H1B Filter in Job Search

As an **H1B job seeker**,
I want **to filter jobs by sponsorship status**,
So that **I only see visa-friendly opportunities**.

**Acceptance Criteria:**

**Given** I am in job matches or search
**When** I apply the H1B filter
**Then** I can select:
- "Verified sponsors only" (hide unknown)
- "High approval rate (80%+)"
- "Any sponsorship history"
**And** filter persists across sessions
**And** filter can be combined with other filters (location, salary)

---

### Story 7.9: Sponsor Data Freshness Infrastructure

As a **system**,
I want **sponsor data to stay current with scheduled updates**,
So that **users don't make decisions on stale information**.

**Acceptance Criteria:**

**Given** the data pipeline is running
**When** data is older than 7 days
**Then** it is flagged for refresh in next pipeline run
**And** UI shows "Data may be outdated" warning if >14 days old
**And** critical companies (high user interest) are refreshed more frequently
**And** data freshness metrics are tracked in observability dashboard

---

### Story 7.10: H1B Empty State

As an **H1B job seeker**,
I want **helpful guidance when no sponsor data exists for a company**,
So that **I know what to do next**.

**Acceptance Criteria:**

**Given** I view a company with no H1B data
**When** I access the H1B section
**Then** I see: "No sponsorship data found for [Company]"
**And** I see suggestions:
- "This may be a new company or one that hasn't sponsored recently"
- "Check the company's careers page for sponsorship policy"
- "Ask during the interview process"
**And** I can request: "Notify me when data becomes available"
**And** I can contribute: "Know something? Share anonymous tip"

---

## Epic 7 Complete ✅

| Metric | Value |
|--------|-------|
| Total Stories | 10 |
| FR Covered | F8 |
| Key Outcome | Comprehensive H1B sponsor intelligence |

---

---

## Epic 8: Interview Preparation (P2)

**Goal:** Users get auto-generated interview prep briefings with company research, interviewer background, and STAR response suggestions.

**FR Covered:** F13 (Interview Intel Agent)
**Dependencies:** Epic 0, Epic 3, Epic 6
**Total Stories:** 8

**Definition of Done (applies to all stories):**
- All acceptance criteria pass
- Code reviewed and approved
- Unit tests written (>80% line, >70% branch coverage)
- Deployed to staging environment
- Privacy: only public data used for research

---

### Story 8.1: Interview Intel Agent Implementation

As a **system**,
I want **an Interview Intel Agent that generates prep briefings**,
So that **users are well-prepared for interviews automatically**.

**Acceptance Criteria:**

**Given** Interview Intel Agent is deployed
**When** an interview is detected (from email or calendar)
**Then** agent triggers research workflow:
1. Company research
2. Interviewer research (if name known)
3. Role-specific question generation
4. STAR response suggestions
**And** prep briefing is generated and stored
**And** briefing is delivered 24 hours before interview

---

### Story 8.2: Company Research Synthesis

As an **Interview Intel Agent**,
I want **to compile company research into interview-ready insights**,
So that **users can speak knowledgeably about the company**.

**Acceptance Criteria:**

**Given** an interview is scheduled
**When** company research runs
**Then** briefing includes:
- Company mission and values
- Recent news (last 6 months)
- Key products/services
- Competitors and market position
- Recent challenges or opportunities
- Company culture indicators (from Glassdoor, LinkedIn)
**And** each fact includes source link
**And** "Talk about this" suggestions highlight conversation hooks

---

### Story 8.3: Interviewer Background Research

As an **Interview Intel Agent**,
I want **to research interviewer backgrounds**,
So that **users can build rapport and anticipate perspectives**.

**Acceptance Criteria:**

**Given** interviewer name(s) are known
**When** interviewer research runs
**Then** briefing includes (from public sources only):
- Current role and tenure
- Career history highlights
- LinkedIn posts or articles (if public)
- Speaking topics or publications
- Shared connections or interests
**And** research respects privacy (public data only)
**And** "Conversation starters" are suggested based on common ground

---

### Story 8.4: Common Interview Questions

As a **user**,
I want **likely interview questions for my specific role**,
So that **I can prepare answers in advance**.

**Acceptance Criteria:**

**Given** I have an interview for a specific role type
**When** I view the prep briefing
**Then** I see 10-15 likely questions categorized as:
- Behavioral ("Tell me about a time...")
- Technical (role-specific)
- Company-specific ("Why [Company]?")
- Role-specific ("How would you approach...")
**And** questions are tailored to seniority level
**And** I can mark questions as "prepared" to track progress

---

### Story 8.5: STAR Response Suggestions

As a **user**,
I want **STAR-formatted response suggestions based on my experience**,
So that **I can answer behavioral questions effectively**.

**Acceptance Criteria:**

**Given** a behavioral question is suggested
**When** I view response suggestions
**Then** agent generates STAR outline using my profile:
- **Situation**: Relevant context from my experience
- **Task**: What I was responsible for
- **Action**: Specific steps I took
- **Result**: Quantified outcome if possible
**And** 2-3 experience options are suggested per question
**And** I can edit and save my preferred response

---

### Story 8.6: Prep Briefing Delivery

As a **user**,
I want **my interview prep briefing delivered proactively**,
So that **I have time to review before the interview**.

**Acceptance Criteria:**

**Given** an interview is scheduled
**When** 24 hours before the interview
**Then** prep briefing is delivered via:
- Push notification: "Interview prep ready for [Company]"
- Email with briefing summary
- In-app notification
**And** briefing is accessible from Pipeline card for that application
**And** reminder sent 2 hours before if briefing unopened

---

### Story 8.7: Calendar Integration for Interview Detection

As a **user**,
I want **interviews automatically detected from my calendar**,
So that **prep briefings are generated without manual input**.

**Acceptance Criteria:**

**Given** I have connected Google Calendar or Outlook Calendar
**When** a calendar event matches interview patterns
**Then** it is flagged as potential interview:
- Title contains "interview", "call with recruiter", company name
- Attendees include external domain
- Duration is 30-60 minutes
**And** user can confirm or dismiss detection
**And** confirmed interviews trigger prep briefing generation

---

### Story 8.8: Interview Prep Empty State

As a **user**,
I want **guidance when I have no upcoming interviews**,
So that **I understand this feature and stay motivated**.

**Acceptance Criteria:**

**Given** I have no scheduled interviews
**When** I view the Interview Prep section
**Then** I see: "No interviews scheduled yet. Keep applying!"
**And** I see tips:
- "Connect your calendar for automatic detection"
- "Interviews are detected from your pipeline"
**And** I see link to practice: "Browse common questions for your role"
**And** tone is encouraging, not discouraging

---

## Epic 8 Complete ✅

| Metric | Value |
|--------|-------|
| Total Stories | 8 |
| FR Covered | F13 |
| Key Outcome | Automated interview preparation |

---

---

## Epic 9: Network Building (P2)

**Goal:** Users have autonomous relationship warming with target contacts, including warm path mapping and introduction request drafts.

**FR Covered:** F14 (Network Agent)
**Dependencies:** Epic 0, Epic 3, Epic 4
**Total Stories:** 8

**Definition of Done (applies to all stories):**
- All acceptance criteria pass
- Code reviewed and approved
- Unit tests written (>80% line, >70% branch coverage)
- Deployed to staging environment
- Human approval required for all outreach

---

### Story 9.1: Network Agent Implementation

As a **system**,
I want **a Network Agent that helps users build professional relationships**,
So that **users can leverage warm introductions for job opportunities**.

**Acceptance Criteria:**

**Given** Network Agent is deployed
**When** user has target companies identified
**Then** agent performs:
1. Warm path analysis (2nd degree connections)
2. Relationship opportunity identification
3. Introduction request draft generation
**And** all direct outreach requires human approval
**And** agent respects autonomy level settings

---

### Story 9.2: Warm Path Finder

As a **user**,
I want **to discover connections who can introduce me to target companies**,
So that **I can leverage my network for warm introductions**.

**Acceptance Criteria:**

**Given** I have saved jobs or target companies
**When** the Network Agent analyzes my connections
**Then** I see warm paths:
- 1st degree: Direct connections at target company
- 2nd degree: Connections who know someone at target
- Alumni: Same school/company alumni at target
**And** path strength is scored (strong/medium/weak)
**And** suggested action: "Ask [Connection] for intro to [Target]"

---

### Story 9.3: Introduction Request Message Drafts

As a **user**,
I want **AI-generated introduction request messages**,
So that **I can reach out professionally without awkwardness**.

**Acceptance Criteria:**

**Given** I want to request an introduction
**When** I view the draft
**Then** message includes:
- Personalized opening referencing relationship
- Clear, specific ask ("Would you be open to introducing me to...")
- Context on why I'm interested in the target company
- Easy out ("No worries if not possible")
**And** message is appropriate length (3-5 sentences)
**And** I can edit before sending
**And** sending requires my explicit approval

---

### Story 9.4: Content Engagement Tracking

As a **Network Agent**,
I want **to track engagement with target contacts' content**,
So that **users build familiarity before direct outreach**.

**Acceptance Criteria:**

**Given** target contacts are identified
**When** they post public content (LinkedIn posts, articles)
**Then** agent surfaces engagement opportunities:
- "John posted about [topic] - good chance to comment"
- Suggested thoughtful comment draft
**And** engagement history is tracked
**And** "Relationship temperature" increases with engagement
**And** this feature is optional and user-controlled

---

### Story 9.5: Relationship Temperature Scoring

As a **user**,
I want **to see relationship strength with target contacts**,
So that **I know when relationships are warm enough for asks**.

**Acceptance Criteria:**

**Given** I have interacted with contacts
**When** I view my network dashboard
**Then** each contact shows temperature score:
- Cold: No interaction
- Warming: Some engagement
- Warm: Regular interaction
- Hot: Recent meaningful exchange
**And** temperature factors in: recency, frequency, depth of interaction
**And** "Ready for outreach" indicator when temperature is sufficient

---

### Story 9.6: Human Approval for Direct Outreach

As a **user**,
I want **all direct messages to require my approval**,
So that **I maintain control over my professional reputation**.

**Acceptance Criteria:**

**Given** the Network Agent drafts outreach
**When** the message is ready
**Then** it appears in my approval queue
**And** I can: Approve, Edit & Approve, or Reject
**And** agent NEVER sends messages without approval
**And** this is a hard constraint regardless of autonomy level
**And** approval queue shows: Recipient, Message preview, Relationship context

---

### Story 9.7: Network Dashboard

As a **user**,
I want **a dashboard showing my networking activity and opportunities**,
So that **I can manage relationship building strategically**.

**Acceptance Criteria:**

**Given** I navigate to Network section
**When** I view the dashboard
**Then** I see:
- Target companies with warm path count
- Contacts by relationship temperature
- Pending outreach drafts
- Recent engagement activity
- Suggested actions for the week
**And** I can drill into any section for details

---

### Story 9.8: Network Empty State

As a **user**,
I want **guidance when I haven't started networking**,
So that **I understand how to use this feature**.

**Acceptance Criteria:**

**Given** I have no network activity
**When** I view the Network section
**Then** I see: "Build your professional network strategically"
**And** I see explanation of how warm introductions work
**And** I see CTA: "Import your LinkedIn connections" (if not connected)
**And** I see CTA: "Save target companies to find warm paths"
**And** tone emphasizes quality over quantity

---

## Epic 9 Complete ✅

| Metric | Value |
|--------|-------|
| Total Stories | 8 |
| FR Covered | F14 |
| Key Outcome | Strategic relationship building |

---

## Epic 10: Enterprise Administration

**Goal:** Empower HR admins to manage outplacement at scale with aggregate visibility and per-employee controls.

**Functional Requirements Covered:** F15 (Enterprise Admin Dashboard)

**Target Tier:** Enterprise B2B

**Story Count:** 10

---

### Story 10.1: Enterprise Admin Role and Permissions

As an **enterprise admin**,
I want **a dedicated admin role with elevated privileges**,
So that **I can manage my organization's JobPilot deployment**.

**Acceptance Criteria:**

**Given** an enterprise purchases JobPilot for their organization
**When** the admin account is created
**Then** admin has permissions for:
- View aggregate org metrics (not individual PII)
- Invite/remove employees
- Set default autonomy levels
- Access billing management
- Configure org-wide settings
**And** admin CANNOT see individual job applications or pipeline details
**And** role is enforced at API level with RLS
**And** admin actions are logged in audit trail

---

### Story 10.2: Bulk Employee Onboarding via CSV

As an **enterprise admin**,
I want **to upload a CSV to bulk-invite employees**,
So that **I can onboard large groups efficiently**.

**Acceptance Criteria:**

**Given** I am on the admin dashboard
**When** I upload a CSV with employee emails
**Then** system validates: format, duplicates, existing accounts
**And** valid rows are queued for invitation
**And** invalid rows are reported with specific errors
**And** I can download error report
**And** progress indicator shows invitation status
**And** maximum batch size: 1,000 employees per upload

---

### Story 10.3: Employee Invitation Flow

As an **employee**,
I want **to receive a branded invitation from my company**,
So that **I know this is a legitimate benefit and not spam**.

**Acceptance Criteria:**

**Given** my employer has added me to JobPilot
**When** I receive the invitation email
**Then** email shows: Company logo, Admin name, benefit explanation
**And** I click to accept and create my account
**And** my tier is automatically set to enterprise allocation
**And** I see welcome message referencing my company
**And** I can opt out if I prefer not to use the service
**And** opt-out is reported to admin as "declined" (not details)

---

### Story 10.4: Aggregate Metrics Dashboard

As an **enterprise admin**,
I want **to see aggregate engagement metrics across my organization**,
So that **I can demonstrate ROI to leadership**.

**Acceptance Criteria:**

**Given** I am on the enterprise dashboard
**When** I view metrics
**Then** I see aggregate (not individual) metrics:
- Total employees enrolled vs. active
- Total jobs reviewed (org-wide)
- Total applications submitted (org-wide)
- Total interviews scheduled (org-wide)
- Placement rate (offers/active users)
- Average time-to-placement
**And** metrics update daily
**And** I can export as PDF or CSV report
**And** date range filter available

---

### Story 10.5: Per-Employee Autonomy Configuration

As an **enterprise admin**,
I want **to set default autonomy levels for employees**,
So that **I can balance automation with company policies**.

**Acceptance Criteria:**

**Given** I am managing organization settings
**When** I configure autonomy defaults
**Then** I can set: Default autonomy level (L1/L2/L3)
**And** employees can adjust within allowed range
**And** I can set maximum autonomy ceiling per employee tier
**And** special restrictions available:
- Block auto-apply to competitor companies
- Require approval for certain industries
**And** employees see their allowed range in settings

---

### Story 10.6: At-Risk Employee Alerts

As an **enterprise admin**,
I want **to know when employees aren't engaging with the service**,
So that **I can offer additional support**.

**Acceptance Criteria:**

**Given** employees have been onboarded
**When** any employee shows low engagement
**Then** admin dashboard shows "At-Risk" summary:
- Not logged in for 14+ days
- No applications in 30+ days
- Stalled pipeline with no updates
**And** admin can send re-engagement nudge (generic, not personalized)
**And** I do NOT see why they're not engaging (privacy)
**And** I can filter: At-risk, Active, Placed, Opted-out

---

### Story 10.7: ROI Reporting

As an **enterprise admin**,
I want **to generate reports showing JobPilot ROI**,
So that **I can justify continued investment**.

**Acceptance Criteria:**

**Given** my organization has been using JobPilot
**When** I generate an ROI report
**Then** report includes:
- Cost per placement (subscription / placements)
- Time-to-placement vs. industry benchmarks
- Engagement rates vs. traditional outplacement
- Employee satisfaction (if surveys enabled)
**And** report is branded with company logo
**And** I can schedule monthly automated reports
**And** report suitable for executive presentation

---

### Story 10.8: PII Detection Alerts

As an **enterprise admin**,
I want **to be alerted if company PII appears in public outputs**,
So that **I can protect company confidential information**.

**Acceptance Criteria:**

**Given** employees are generating resumes and cover letters
**When** agent detects potential company PII
**Then** generation is paused (not sent)
**And** employee sees: "Potential confidential information detected"
**And** admin receives anonymized alert: "PII detected in user [ID]"
**And** PII patterns configurable: Project names, client names, proprietary terms
**And** false positives can be whitelisted by admin

---

### Story 10.9: Enterprise Billing Management

As an **enterprise admin**,
I want **to manage billing and seat allocation**,
So that **I can control costs and scaling**.

**Acceptance Criteria:**

**Given** I have enterprise billing access
**When** I view billing management
**Then** I see: Current seats used/allocated, Monthly cost, Usage trends
**And** I can add seats (pro-rated billing)
**And** I can remove unused seats (next billing cycle)
**And** I can view invoices and payment history
**And** I can update payment method
**And** volume discounts automatically applied per contract

---

### Story 10.10: Enterprise Empty State

As an **enterprise admin**,
I want **clear guidance when first setting up my organization**,
So that **I can successfully deploy JobPilot to my team**.

**Acceptance Criteria:**

**Given** I have created an enterprise account
**When** I view the admin dashboard with no employees
**Then** I see: "Set up your organization's career transition program"
**And** I see step-by-step guide:
1. Upload company logo
2. Customize welcome message
3. Set default autonomy levels
4. Upload employee list or send invitations
**And** progress tracker shows completion percentage
**And** help link to enterprise onboarding guide

---

## Epic 10 Complete ✅

| Metric | Value |
|--------|-------|
| Total Stories | 10 |
| FR Covered | F15 |
| Key Outcome | Enterprise-scale outplacement management |

---

## Document Summary

### Epic Overview

| Epic | Name | Stories | FRs Covered | Priority |
|------|------|---------|-------------|----------|
| 0 | Platform Foundation | 15 | NFR1-9 | P0 |
| 1 | Lightning Onboarding | 6 | F1 | P0 |
| 2 | Preference Configuration | 8 | F2 | P0 |
| 3 | Agent Orchestration Core | 11 | F3, F7 | P0 |
| 4 | AI-Powered Job Matching | 10 | F4 | P0 |
| 5 | Application Automation | 14 | F5, F9, F10 | P0/P1 |
| 6 | Pipeline & Privacy | 14 | F6, F11, F12 | P0/P1 |
| 7 | H1B Specialist Experience | 10 | F8 | P0 |
| 8 | Interview Preparation | 8 | F13 | P2 |
| 9 | Network Building | 8 | F14 | P2 |
| 10 | Enterprise Administration | 10 | F15 | P1 |
| **TOTAL** | | **114** | **15 FRs** | |

### FR Coverage Verification

| FR | Feature | Epic | Stories |
|----|---------|------|---------|
| F1 | Zero-Setup Onboarding | 1 | 1.1-1.6 |
| F2 | Preference Wizard | 2 | 2.1-2.8 |
| F3 | Daily Briefing | 3 | 3.1-3.11 |
| F4 | Job Scout Agent | 4 | 4.1-4.10 |
| F5 | Resume Agent | 5 | 5.1-5.7 |
| F6 | Pipeline Agent | 6 | 6.1-6.8 |
| F7 | Emergency Brake | 3 | 3.7-3.8 |
| F8 | H1B Sponsor Database | 7 | 7.1-7.10 |
| F9 | Apply Agent | 5 | 5.8-5.12 |
| F10 | Cover Letter Generator | 5 | 5.13-5.14 |
| F11 | Follow-up Agent | 6 | 6.9-6.11 |
| F12 | Stealth Mode | 6 | 6.12-6.14 |
| F13 | Interview Intel Agent | 8 | 8.1-8.8 |
| F14 | Network Agent | 9 | 9.1-9.8 |
| F15 | Enterprise Admin Dashboard | 10 | 10.1-10.10 |

### MVP Slice Definition

**MVP (Epics 0-6, partial 7):** ~88 stories
- Platform Foundation (15)
- Lightning Onboarding (6)
- Preference Configuration (8)
- Agent Orchestration Core (11)
- AI-Powered Job Matching (10)
- Application Automation (14)
- Pipeline & Privacy (14)
- H1B Specialist Experience (10) - partial for H1B Pro tier

**Post-MVP (Epics 8-10):** ~26 stories
- Interview Preparation (8)
- Network Building (8)
- Enterprise Administration (10)

---

_Step 3 Complete. Proceeding to Final Validation._
