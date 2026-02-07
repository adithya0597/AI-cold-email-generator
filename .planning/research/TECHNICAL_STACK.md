# Technical Stack & Ecosystem Research

**Project:** JobPilot
**Researched:** 2026-01-30
**Focus:** Technical stack evaluation, dependency versions, AI agent orchestration, job board APIs, email integration
**Overall Confidence:** MEDIUM-HIGH

---

## Executive Summary

The existing codebase is a brownfield FastAPI + React application with severely outdated dependencies. The architecture document specifies a solid technology direction, but several pinned versions are 2+ years behind current releases, creating security and compatibility risks. The most critical decisions revolve around: (1) the AI agent orchestration approach, where the landscape has shifted dramatically since the architecture was written; (2) job board data acquisition, which is harder than the PRD assumes; and (3) the mandatory CRA-to-Vite migration on the frontend.

This research covers current versions, upgrade paths, ecosystem options, and concrete recommendations for each stack layer.

---

## 1. Current Dependency Audit

### Backend: Critical Version Gaps

| Package | Current Version | Latest Version | Gap | Risk |
|---------|----------------|----------------|-----|------|
| `fastapi` | 0.104.1 | ~0.115.x | ~11 minor versions | MEDIUM - Python 3.8 dropped, Pydantic v1 deprecated |
| `openai` | 1.3.0 | **2.16.0** | **Major version jump (v1 -> v2)** | **HIGH** - v1.x no longer supported, Responses API is now primary |
| `anthropic` | 0.7.0 | **0.77.0** | 70 minor versions | **HIGH** - Massive API changes, new features (tool use, batching) |
| `langchain` | 0.0.340 | 1.0.x (langchain-core) | **Major version + package rename** | **HIGH** - Pre-1.0 langchain is effectively deprecated |
| `supabase` | 2.3.0 | 2.27.2 | 24 minor versions | MEDIUM - Bug fixes, new features |
| `pydantic` | 2.5.0 | 2.10.x | ~5 minor versions | LOW - Compatible within v2 |
| `sqlalchemy` | 2.0.23 | 2.0.36+ | Minor patches | LOW |
| `selenium` | 4.15.2 | 4.27.x | ~12 versions | LOW-MEDIUM |
| `httpx` | 0.25.1 | 0.28.x | 3 minor versions | LOW |
| `celery` | Not installed | 5.6.2 | N/A - New addition | Needs fresh install |
| `redis` | Commented out | 5.2.x | N/A - New addition | Needs fresh install |
| `pytest` | 7.4.3 | 8.3.x | Major version | LOW |

**Confidence:** HIGH - versions verified via PyPI search results and official releases.

### Frontend: Critical Version Gaps

| Package | Current Version | Latest Version | Gap | Risk |
|---------|----------------|----------------|-----|------|
| `react` | 18.2.0 | 18.3.x / 19.x | Minor or major | LOW (18.x is fine for now) |
| `react-scripts` (CRA) | 5.0.1 | **DEPRECATED** | **Dead project** | **CRITICAL** - No security patches since Feb 2025 |
| `tailwindcss` | 3.3.6 | 4.x | Major version | MEDIUM - v4 is new, v3 still works |
| `@tanstack/react-query` | Not installed | 5.90.x | N/A - New addition | Needs fresh install |
| `zustand` | Not installed | 5.0.10 | N/A - New addition | Needs fresh install |
| `zod` | Not installed | 3.x | N/A - New addition | Needs fresh install |
| TypeScript | Not installed | 5.7.x | **Missing entirely** | **HIGH** - Architecture requires strict TS |

**Confidence:** HIGH - verified via npm registry and web search results.

### Verdict: Upgrade Before Building

The codebase needs a dependency modernization pass before new feature development begins. The OpenAI SDK v1->v2 migration and the CRA->Vite migration are the two largest efforts. Both are well-documented with migration guides.

---

## 2. AI Agent Orchestration Framework

### The Landscape Has Changed

The architecture document (dated 2026-01-25) specifies "Custom + langchain-core only." Since the architecture was written, the agent framework landscape has matured significantly. Here are the current options:

### Option A: LangGraph (Recommended)

**What:** Graph-based stateful agent orchestration by LangChain. Reached v1.0 in October 2025.

**Why it fits JobPilot:**
- **Human-in-the-loop is first-class.** LangGraph has built-in patterns for pausing execution, getting human approval, and resuming. This maps directly to the L0-L3 autonomy tiers and the approval queue.
- **Durable state.** Agent execution state persists automatically. If a Celery worker restarts, the agent picks up where it left off. Critical for the "emergency brake" feature.
- **Checkpointing.** You can replay, roll back, or inspect any step. This directly enables the audit log and transparency requirements.
- **Multi-agent coordination.** The orchestrator pattern (one coordinator dispatching to specialized agents) is a core LangGraph pattern.
- **Provider-agnostic.** Works with OpenAI, Anthropic, and any other LLM. Supports the existing dual-model strategy.

**Tradeoffs:**
- Steeper learning curve than simpler alternatives
- Adds ~50-100MB to dependency tree (not just langchain-core)
- Lock-in to the LangChain ecosystem for agent structure

**Confidence:** MEDIUM-HIGH - based on multiple 2025-2026 comparisons and LangGraph documentation.

### Option B: OpenAI Agents SDK

**What:** Lightweight agent framework from OpenAI. Latest version 0.7.0.

**Why consider:**
- Extremely simple API, minimal boilerplate
- Native handoffs between agents
- Built-in guardrails
- Works with 100+ LLMs (not just OpenAI)

**Why NOT for JobPilot:**
- No built-in durable state or checkpointing
- Human-in-the-loop patterns must be built custom
- Less mature than LangGraph for production multi-agent systems
- Limited error recovery (no graph-based rollback)

**Confidence:** MEDIUM - SDK is only v0.7.0 and still pre-1.0.

### Option C: Custom Framework (Architecture's Current Recommendation)

**What:** Build orchestrator from scratch, use langchain-core only for model wrappers and output parsing.

**Why consider:**
- Maximum control over autonomy enforcement
- Minimal dependencies
- No framework lock-in

**Why NOT recommended:**
- Reinvents human-in-the-loop, checkpointing, state persistence
- The architecture already describes patterns that LangGraph provides out of the box
- Maintenance burden: every agent pattern must be built and tested
- The old `langchain` 0.0.340 package is completely different from langchain-core 1.0

**Confidence:** HIGH - this is a well-understood tradeoff.

### Recommendation: LangGraph + Custom Autonomy Layer

Use LangGraph as the execution engine (graph definition, checkpointing, human-in-the-loop), but build the autonomy tier enforcement (L0-L3) as a custom layer on top. This gives you:
- LangGraph's production-grade state management
- Custom business logic for tier enforcement
- The emergency brake implemented as a checkpoint interrupt
- Audit logging from LangGraph's built-in tracing

```python
# Conceptual: Custom autonomy on LangGraph
from langgraph.graph import StateGraph
from langgraph.checkpoint.postgres import PostgresSaver

class AutonomyGate:
    """Custom L0-L3 enforcement that wraps LangGraph nodes."""
    def __call__(self, state: AgentState) -> str:
        tier = state["user_tier"]
        action = state["proposed_action"]
        if requires_approval(tier, action):
            return "await_approval"  # LangGraph interrupt
        return "execute"
```

**Migration from architecture spec:** Replace "Custom + langchain-core only" with "LangGraph 1.0 + custom autonomy middleware." The project structure remains the same -- agents still live in `backend/app/agents/`, the orchestrator still coordinates, but the execution engine is LangGraph instead of hand-rolled.

---

## 3. Job Board API Landscape

### The Hard Truth

**There are no good public APIs for job search aggregation.** This is the single biggest technical risk in the project.

| Source | Official API? | Status | Notes |
|--------|--------------|--------|-------|
| **LinkedIn** | No public job search API | BLOCKED | LinkedIn aggressively blocks scraping. ToS prohibits automation. The architecture correctly flags this risk. |
| **Indeed** | Job Sync API (posting only) | PARTIAL | Indeed's API is for *posting* jobs, not *searching* them. No public search API exists for developers. |
| **Glassdoor** | No public API | BLOCKED | Glassdoor does not offer a public API for job listings. |
| **ZipRecruiter** | Partner API | RESTRICTED | Requires partnership agreement |
| **Google Jobs** | SerpAPI (paid) | AVAILABLE | $50/mo+ for structured Google Jobs results |
| **Adzuna** | Public API | AVAILABLE | Free tier: 250 calls/day. Good coverage in US/UK. |
| **The Muse** | Public API | AVAILABLE | Free. Limited to ~1,500 companies. |
| **Remotive** | Public API | AVAILABLE | Free. Remote jobs only. |
| **USAJobs** | Public API | AVAILABLE | Free. US government jobs only. |
| **JSearch (RapidAPI)** | Aggregator API | AVAILABLE | $0-50/mo. Aggregates from multiple sources. |
| **Apify scrapers** | Scraping-as-a-service | AVAILABLE | $49/mo+. Pre-built scrapers for Indeed, LinkedIn, Glassdoor. Legal gray area. |

**Confidence:** MEDIUM - based on web search; specific API terms/pricing change frequently.

### Recommendation: Multi-Source Strategy

**Tier 1 (MVP):** Use legitimate aggregator APIs
- **JSearch via RapidAPI** - Aggregates Indeed, LinkedIn, Glassdoor data through an API. Starts free, scales to $50/mo.
- **Adzuna API** - Good US coverage, free tier available, well-documented REST API.
- **SerpAPI Google Jobs** - Structured data from Google's job aggregation. Paid but reliable.

**Tier 2 (Growth):** Add scrapers with caution
- **Apify pre-built scrapers** - For Indeed/Glassdoor data where APIs don't exist. Run on Apify's infrastructure (not your IP).
- **Custom scrapers** - Only for company career pages, not major job boards. Use the existing `httpx` + `beautifulsoup4` stack.

**Tier 3 (Scale):** Data partnerships
- At scale (10K+ users), negotiate data partnerships with job boards directly.
- Consider buying job data feeds from providers like Infotrie or TheirStack ($500-5000/mo).

**Critical Warning:** The PRD states "Monitors: LinkedIn, Indeed, Glassdoor, company career pages" as if these are straightforward integrations. They are not. LinkedIn in particular has zero legal path for automated job data access. The roadmap must account for this reality and avoid promising LinkedIn job monitoring in early phases.

---

## 4. Email Integration (Gmail/Outlook OAuth)

### Architecture: Pipeline Agent Email Parsing

The Pipeline Agent needs to:
1. Connect to user's email via OAuth
2. Parse job-related emails (confirmations, interview requests, rejections)
3. Auto-create/update pipeline entries

### Gmail Integration

**Official approach:** Google API Python Client
- Install: `google-auth`, `google-auth-oauthlib`, `google-api-python-client`
- OAuth 2.0 consent screen required (Google Cloud Console)
- Gmail API scopes: `gmail.readonly` (minimum), `gmail.modify` (for labels/marks)
- **Important:** Google requires app verification for sensitive scopes. For `gmail.readonly` on user data, you need OAuth consent screen verification, which can take 2-6 weeks.

**Email parsing stack:**
- Python's built-in `email.parser` module for MIME parsing
- LLM (GPT-3.5) for classification: "Is this job-related? What type? Extract company/role."
- Keyword pre-filter to avoid sending every email to the LLM (cost optimization)

**Confidence:** HIGH - well-documented official Google APIs.

### Outlook/Microsoft Integration

**Official approach:** Microsoft Authentication Library (MSAL)
- Install: `msal` (Microsoft Authentication Library for Python)
- Microsoft Graph API for email access
- OAuth 2.0 with Azure AD app registration
- Scope: `Mail.Read` (minimum)
- **Important:** O365 basic auth deprecated. OAuth 2.0 mandatory as of April 2026 for SMTP, already mandatory for IMAP.

**Confidence:** HIGH - well-documented Microsoft APIs.

### Recommendation

- Implement Gmail first (larger user base among job seekers)
- Use the Gmail API directly (not IMAP) for better reliability and metadata
- Build an abstraction layer (`EmailProvider`) so Outlook uses the same interface
- Add email keyword pre-filter before LLM classification to keep costs under budget
- Budget 2-6 weeks for Google OAuth verification process -- start this early

---

## 5. Authentication: Clerk

### Current State

The existing codebase uses custom JWT auth with `python-jose` and `passlib`. The architecture specifies migration to Clerk.

### Clerk + FastAPI Integration Options

| Option | Package | Latest | Notes |
|--------|---------|--------|-------|
| `fastapi-clerk-auth` | Community package | Nov 2025 | Lightweight JWT validation against Clerk JWKS. MIT licensed. Stable. |
| `clerk-backend-api` | Official Clerk SDK | Active | Full Clerk API access (user management, sessions, organizations). More features, more dependency. |
| Manual JWT validation | DIY with PyJWT | N/A | Decode Clerk JWTs manually. Most control, most work. |

**Recommendation:** Use `fastapi-clerk-auth` for route protection (it's simple and well-maintained), supplemented by `clerk-backend-api` for user management operations (create/update users, manage organizations for enterprise tier).

**Frontend:** Clerk's official React SDK (`@clerk/clerk-react`) is mature and well-documented. Handles login UI, session management, and LinkedIn OAuth out of the box.

**Migration path:** The architecture correctly includes an `AuthProvider` abstraction layer. This is important -- Clerk's pricing scales per-MAU, and at 10K+ users you may want to evaluate alternatives (Auth0, self-hosted Keycloak).

**Confidence:** MEDIUM-HIGH - `fastapi-clerk-auth` verified on PyPI; Clerk React SDK is well-established.

---

## 6. Frontend: CRA to Vite Migration (Mandatory)

### Create React App is Dead

CRA was officially deprecated in February 2025. It receives no security patches, no updates, and its webpack-based build is 10-30x slower than modern alternatives. The existing codebase uses `react-scripts` 5.0.1.

**This migration is non-negotiable and should happen in Phase 1.**

### Migration to Vite

**Why Vite:**
- Near-instant dev server cold start (vs 20-30s with CRA)
- Hot Module Replacement in milliseconds
- Rollup-based production builds (smaller, optimized bundles)
- Native ESM support
- Active ecosystem with Vitest for testing

**Key migration steps:**
1. Remove `react-scripts` dependency
2. Install `vite`, `@vitejs/plugin-react`
3. Move `index.html` from `public/` to project root
4. Rename `REACT_APP_*` env vars to `VITE_*` (or use compatibility plugin)
5. Replace Jest/react-scripts test runner with Vitest
6. Update `package.json` scripts

**TypeScript addition:** The architecture requires TypeScript strict mode. This should be added during the Vite migration. Install `typescript`, update `tsconfig.json`, and rename `.js/.jsx` files to `.ts/.tsx` incrementally.

**Real-world results:** Teams report 80% faster CI pipelines after CRA-to-Vite migration.

**Confidence:** HIGH - CRA deprecation is a documented fact; Vite migration is well-established.

---

## 7. Background Jobs: Celery + Redis

### Current State

Celery and Redis are not installed in the current codebase. Redis is commented out in `requirements.txt`.

### Celery 5.6.2 (Latest)

- Dropped Python 3.8 support (aligns with FastAPI's direction)
- Fixed critical memory leaks in task exception handling
- Fixed security issue with broker URLs logged in plaintext
- Requires Python 3.9+

### Redis

- `redis` Python package v5.2.x is current
- Railway (the planned host) offers managed Redis
- Alternative: Dragonfly (drop-in Redis replacement with better performance) or Upstash (serverless Redis)

### Alternatives Considered

| Tool | Verdict | Why |
|------|---------|-----|
| **RQ (Redis Queue)** | Not recommended | Simpler but 4x slower than Celery at scale (benchmarks: 51s vs 12s for 20K jobs). JobPilot needs to process 100K jobs/day. |
| **Huey** | Not recommended | Too lightweight for multi-agent coordination |
| **APScheduler** | Not recommended | Scheduler only, not a distributed task queue |
| **Dramatiq** | Worth watching | Simpler API than Celery, good performance, but smaller ecosystem |

**Recommendation:** Stick with Celery + Redis as specified in the architecture. It's the battle-tested choice for this workload profile. The architecture's Celery configuration (heartbeats, zombie cleanup, task timeouts) is well-designed.

**Confidence:** HIGH - Celery is the standard Python distributed task queue.

---

## 8. Database: Supabase

### Current State

Supabase Python SDK `2.3.0` is installed. Current version is `2.27.2`.

### Upgrade Notes

- Major improvements in auth, realtime, and storage between 2.3.0 and 2.27.2
- Version 2.23.3 was yanked (breaking change) -- target 2.24.0+
- Python SDK now supports Flask, Django, and FastAPI patterns
- Realtime data streaming support improved

### SQLAlchemy + Alembic

The codebase has SQLAlchemy 2.0.23 and Alembic 1.12.1 installed. These should be retained for:
- Database model definitions
- Migration management
- Complex query building

The Supabase Python client should be used for:
- Auth integration (Clerk JWT forwarding to Supabase RLS)
- Realtime subscriptions (optional, WebSocket alternative)
- File storage (resume PDFs)

**Recommendation:** Upgrade to `supabase>=2.24.0`. Keep SQLAlchemy for ORM/migrations. Use Supabase client for auth forwarding and storage.

**Confidence:** HIGH - standard pattern for Supabase + Python backends.

---

## 9. Frontend State Management

### TanStack Query v5 (Server State)

- Latest: 5.90.x
- Note: Despite mentions of "v6" online, TanStack Query v6 is Svelte-only. React stays on v5.
- Install: `@tanstack/react-query`
- Excellent React Server Components support
- The architecture's query key pattern and optimistic update examples are idiomatic v5.

### Zustand v5 (Client State)

- Latest: 5.0.10 (14M+ weekly downloads)
- Install: `zustand`
- The architecture's Zustand store pattern (emergency brake toggle, modals) is correct for v5.
- Zustand v5 uses `useSyncExternalStore` under the hood -- good React concurrent mode compatibility.

### Zod (Runtime Validation)

- Latest: 3.24.x
- Install: `zod`
- The architecture's Zod schema for agent output validation is the correct pattern.

**Recommendation:** Install as specified. These three libraries (TanStack Query + Zustand + Zod) are the current consensus "modern React" state management stack. The architecture document's usage patterns are all correct.

**Confidence:** HIGH - verified current versions; architecture patterns are idiomatic.

---

## 10. Testing Stack

### Backend

| Tool | Version | Status |
|------|---------|--------|
| `pytest` | 7.4.3 -> 8.3.x | Upgrade recommended (better async support) |
| `pytest-asyncio` | 0.21.1 -> 0.25.x | Upgrade recommended |
| `schemathesis` | Not installed | Needs installation for API contract testing |

### Frontend

| Tool | Current | Recommended | Notes |
|------|---------|-------------|-------|
| Jest (via CRA) | Bundled | **Vitest** | Must migrate with CRA -> Vite. Vitest is API-compatible with Jest. |
| React Testing Library | 14.1.2 | 16.x | Upgrade to match React 18.x patterns |
| Playwright | Not installed | 1.50.x | Install for E2E testing. Better than Cypress for multi-browser, parallel execution, and CI scalability. |

### Playwright over Cypress: Why

The architecture specifies Playwright, which is the right call:
- Native multi-browser support (Chromium, Firefox, WebKit)
- Built-in parallel execution (no paid tiers needed)
- Better CI performance (12 min vs 45 min in real-world comparisons)
- Multi-page/multi-domain support needed for OAuth flows
- Python bindings available (useful for testing agent workflows)

**Confidence:** HIGH - well-established tools with clear migration paths.

---

## 11. Email Service: SendGrid vs Alternatives

### SendGrid (Architecture's Choice)

SendGrid remains functional but has known issues:
- Pricing has increased significantly
- Only 3-day email log retention
- Customer support quality has declined
- Potential IP blacklisting issues

### Alternatives Worth Considering

| Service | Pros | Cons | Price |
|---------|------|------|-------|
| **Resend** | Developer-first, React email templates, clean API | Newer/smaller, less enterprise track record | Free up to 3K emails/mo |
| **Postmark** | Best deliverability, focused on transactional | No marketing email support | $15/mo for 10K emails |
| **Amazon SES** | Cheapest at scale ($0.10/1K emails) | More setup, AWS dependency | Pay-per-use |
| **SendGrid** | Established, full-featured | Expensive, declining DX | $20/mo for 50K emails |

### Recommendation

**For MVP:** Use **Resend**. It's developer-first, has a clean Python SDK, and React email templates align with the frontend stack. Free tier covers early development and beta.

**For scale:** Evaluate **Amazon SES** when volume exceeds 50K emails/month for cost optimization.

SendGrid is fine if the team has existing experience, but Resend is the better choice for a new project in 2026.

**Confidence:** MEDIUM - based on current pricing/features; these change frequently.

---

## 12. Payments: Stripe

### Current State

Stripe is not installed in the codebase. Architecture specifies Stripe for payments.

### Latest Version

- `stripe` Python SDK: v14.2.0 (latest)
- API version: 2026-01-28.clover
- Supports Python 3.9+ (3.7/3.8 deprecated)
- Async support available via `stripe[async]`

### Key Features for JobPilot

- **Subscription billing** for Pro ($19/mo), H1B Pro ($49/mo), Career Insurance ($29/mo)
- **Metered billing** potential for LLM cost pass-through at enterprise tier
- **Customer portal** for self-service subscription management
- **Webhook handling** for payment events (already planned in architecture)

**Recommendation:** Install `stripe>=14.0.0`. Well-documented, industry standard, no surprises.

**Confidence:** HIGH - Stripe is the standard for SaaS billing.

---

## 13. Observability Stack

### Architecture Specifies: OpenTelemetry

This is the right call. OpenTelemetry is now the industry standard for distributed tracing.

| Package | Purpose | Install |
|---------|---------|---------|
| `opentelemetry-api` | Core API | `pip install opentelemetry-api` |
| `opentelemetry-sdk` | SDK implementation | `pip install opentelemetry-sdk` |
| `opentelemetry-instrumentation-fastapi` | Auto-instrument FastAPI | `pip install opentelemetry-instrumentation-fastapi` |
| `opentelemetry-instrumentation-celery` | Auto-instrument Celery | `pip install opentelemetry-instrumentation-celery` |
| `opentelemetry-instrumentation-httpx` | Auto-instrument httpx calls | `pip install opentelemetry-instrumentation-httpx` |

### Export Targets

- **Development:** Console exporter (stdout)
- **Production:** OTLP exporter to Grafana Cloud, Datadog, or New Relic
- The architecture mentions Sentry + PostHog. These can complement OTel (Sentry for errors, PostHog for product analytics, OTel for traces).

**Confidence:** HIGH - OpenTelemetry is the standard; instrumentation packages are stable.

---

## Version Pinning Recommendations

### Backend `requirements.txt` Targets

```
# Core framework
fastapi>=0.115.0,<1.0.0
uvicorn[standard]>=0.34.0
pydantic>=2.10.0,<3.0.0
python-multipart>=0.0.18

# AI/LLM
openai>=2.16.0,<3.0.0
anthropic>=0.77.0,<1.0.0
langgraph>=0.3.0

# Agent orchestration
langchain-core>=0.3.0
langchain-openai>=0.3.0
langchain-anthropic>=0.3.0

# Web scraping
httpx>=0.28.0
beautifulsoup4>=4.12.0
selenium>=4.27.0
lxml>=5.0.0

# Document processing
pypdf2>=3.0.0
python-docx>=1.1.0

# Database
sqlalchemy>=2.0.36
alembic>=1.14.0
supabase>=2.27.0

# Background jobs
celery[redis]>=5.6.0
redis>=5.2.0

# Auth
fastapi-clerk-auth>=0.4.0
clerk-backend-api>=1.0.0

# Email
resend>=2.0.0  # or sendgrid>=6.11.0

# Payments
stripe[async]>=14.2.0

# Email integration
google-api-python-client>=2.150.0
google-auth-oauthlib>=1.2.0
msal>=1.31.0

# Observability
opentelemetry-api>=1.29.0
opentelemetry-sdk>=1.29.0
opentelemetry-instrumentation-fastapi>=0.50b0
opentelemetry-instrumentation-celery>=0.50b0

# Testing
pytest>=8.3.0
pytest-asyncio>=0.25.0
playwright>=1.50.0
schemathesis>=3.36.0

# Code quality
ruff>=0.9.0  # Replaces black + flake8
mypy>=1.14.0
```

### Frontend `package.json` Targets

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^7.0.0",
    "@tanstack/react-query": "^5.90.0",
    "zustand": "^5.0.0",
    "zod": "^3.24.0",
    "@clerk/clerk-react": "^5.0.0",
    "axios": "^1.7.0",
    "tailwindcss": "^3.4.0",
    "@headlessui/react": "^2.0.0",
    "@heroicons/react": "^2.2.0",
    "recharts": "^2.15.0",
    "react-hook-form": "^7.54.0"
  },
  "devDependencies": {
    "vite": "^6.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.7.0",
    "vitest": "^3.0.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.6.0",
    "@playwright/test": "^1.50.0",
    "eslint": "^9.0.0",
    "prettier": "^3.4.0"
  }
}
```

**Note:** These are target ranges, not exact pins. Use a lockfile (pip-compile or uv for Python, package-lock.json for Node) for reproducible builds.

---

## Roadmap Implications

### Phase 1 Priority: Foundation Modernization

Before building any new features, the codebase needs:

1. **CRA -> Vite migration** (frontend) - 1-2 days
2. **TypeScript adoption** (frontend) - incremental, start with new files
3. **OpenAI SDK v1 -> v2 migration** (backend) - 1-2 days, breaking API changes
4. **Anthropic SDK upgrade** (backend) - 1 day
5. **langchain removal, LangGraph installation** (backend) - during agent framework setup
6. **Supabase SDK upgrade** (backend) - 0.5 day

### Phase 1 Must Also Include:

- Clerk authentication setup (replaces custom JWT)
- Celery + Redis setup
- Database schema (Supabase migrations)
- Google OAuth app registration (start early -- 2-6 week verification)

### Job Board Integration Should Be Phase 2-3:

Job board data acquisition is harder than assumed. Start with API aggregators (JSearch, Adzuna), add scraping later. Do not promise LinkedIn data in MVP.

### Email Integration Should Be Phase 2:

Gmail OAuth verification takes weeks. Start the Google Cloud Console process in Phase 1, but actual email parsing should be Phase 2.

---

## Confidence Assessment

| Area | Confidence | Reasoning |
|------|-----------|-----------|
| Dependency versions | HIGH | Verified via PyPI, npm, GitHub releases |
| Agent framework (LangGraph) | MEDIUM-HIGH | v1.0 is new; production patterns still emerging |
| Job board APIs | MEDIUM | Landscape changes frequently; pricing/terms not fully verified |
| Email integration | HIGH | Well-documented Google/Microsoft APIs |
| Clerk + FastAPI | MEDIUM-HIGH | Community package verified; official SDK active |
| CRA deprecation | HIGH | Documented fact; industry consensus |
| Frontend state management | HIGH | Mature, widely-adopted libraries |
| Celery + Redis | HIGH | Battle-tested, well-documented |
| Email service (Resend) | MEDIUM | Newer service, less track record than SendGrid |
| Stripe | HIGH | Industry standard, well-documented |

---

## Open Questions

1. **LangGraph vs lighter approach:** Should we prototype with LangGraph before committing? The learning curve is non-trivial.
2. **Job board data budget:** What's the monthly budget for job data APIs? This determines which aggregators are viable.
3. **Google OAuth verification timing:** When can we submit for verification? This blocks email parsing features.
4. **Tailwind v3 vs v4:** Should we stay on v3 (stable, known) or migrate to v4 (new utility system)? Recommend v3 for now.
5. **React 18 vs 19:** React 19 has new features (Server Components, Actions) but the architecture doesn't require them. Recommend staying on 18.x for stability.

---

## Sources

- [FastAPI Release Notes](https://fastapi.tiangolo.com/release-notes/)
- [OpenAI Python SDK - GitHub Releases](https://github.com/openai/openai-python/releases)
- [Anthropic Python SDK - GitHub](https://github.com/anthropics/anthropic-sdk-python)
- [LangChain and LangGraph 1.0 Announcement](https://www.blog.langchain.com/langchain-langgraph-1dot0/)
- [LangChain vs LangGraph 2026 - Kanerika](https://kanerika.com/blogs/langchain-vs-langgraph/)
- [OpenAI Agents SDK vs LangGraph vs CrewAI - Composio](https://composio.dev/blog/openai-agents-sdk-vs-langgraph-vs-autogen-vs-crewai)
- [Top 5 Open-Source Agentic AI Frameworks 2026](https://research.aimultiple.com/agentic-frameworks/)
- [Indeed Job Sync API Docs](https://docs.indeed.com/job-sync-api)
- [Celery 5.6.2 - PyPI](https://pypi.org/project/celery/)
- [Supabase Python SDK - PyPI](https://pypi.org/project/supabase/)
- [fastapi-clerk-auth - PyPI](https://pypi.org/project/fastapi-clerk-auth/)
- [CRA Deprecation - DEV Community](https://dev.to/solitrix02/goodbye-cra-hello-vite-a-developers-2026-survival-guide-for-migration-2a9f)
- [TanStack Query - npm](https://www.npmjs.com/package/@tanstack/react-query)
- [Zustand - npm](https://www.npmjs.com/package/zustand)
- [Stripe Python SDK - PyPI](https://pypi.org/project/stripe/)
- [Gmail API Python Quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python)
- [Playwright vs Cypress 2026](https://bugbug.io/blog/test-automation-tools/cypress-vs-playwright/)
- [SendGrid Alternatives 2026 - Brevo](https://www.brevo.com/blog/sendgrid-alternatives/)
