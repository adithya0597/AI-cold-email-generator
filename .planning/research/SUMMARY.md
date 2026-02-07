# Project Research Summary

**Project:** JobPilot
**Domain:** AI-powered multi-agent job search and career platform
**Researched:** 2026-01-30
**Confidence:** MEDIUM-HIGH

---

## Executive Summary

JobPilot is an AI agent orchestration platform that automates job search, resume tailoring, application submission, and pipeline tracking, differentiated by a tiered autonomy model (L0-L3) and H1B visa sponsorship intelligence. Research across technical stack, architecture, domain concerns, and quality strategy reveals a product that is architecturally ambitious but buildable -- provided the team resolves several critical blockers before feature development begins. The existing codebase (a cold email generator) provides a solid FastAPI + React foundation, but requires substantial modernization: the OpenAI SDK has jumped a major version, Create React App is deprecated, and the database layer has an unresolved dual-persistence split between Supabase SDK and SQLAlchemy.

The recommended approach is a phased build starting with foundation modernization (dependency upgrades, CRA-to-Vite migration, Clerk auth, Celery+Redis), followed by the agent orchestration framework, then individual agents ordered by ascending complexity. The most important architectural decision is the agent orchestration approach -- researchers disagree on LangGraph vs. custom orchestrator, and this must be resolved in Phase 1 via a time-boxed prototype. Job board data acquisition is significantly harder than the PRD assumes (no public APIs for LinkedIn, Indeed, or Glassdoor), and the email parsing feature triggers Google's most expensive compliance requirement (CASA assessment at $5K-$75K/year). Both of these realities must reshape the roadmap: use aggregator APIs (JSearch, Adzuna) instead of scraping, and start with email forwarding instead of Gmail OAuth.

The three highest risks are: (1) the agent orchestration framework choice affecting every subsequent phase, (2) job board data availability constraining the core value proposition, and (3) legal/compliance barriers around automated job applications and email access. All three have concrete mitigation strategies documented in the research, but none can be deferred -- they must be addressed in the earliest phases.

---

## Key Findings

### Recommended Stack

The existing codebase has severely outdated dependencies. Three upgrades are mandatory before any feature work: OpenAI SDK v1->v2 (breaking API changes), CRA->Vite (CRA is deprecated with no security patches), and langchain 0.0.340 removal (pre-1.0, effectively dead). The full stack modernization is estimated at 3-5 days.

**Core technologies:**
- **FastAPI + Uvicorn:** Backend API framework -- already in codebase, upgrade to >=0.115.0
- **React 18 + Vite + TypeScript:** Frontend -- CRA must die, TypeScript is mandatory per architecture
- **Celery + Redis:** Background job processing for agent tasks -- not installed yet, needed for all agent work
- **Supabase (PostgreSQL) + SQLAlchemy + Alembic:** Database layer -- SQLAlchemy as primary ORM, Supabase SDK only for auth/storage/realtime
- **Clerk:** Authentication -- replaces custom JWT auth, with `fastapi-clerk-auth` for backend
- **TanStack Query + Zustand + Zod:** Frontend state management -- modern consensus stack
- **OpenTelemetry + Sentry:** Observability -- from day one, not retrofitted
- **Stripe:** Payments -- standard, no surprises
- **Resend (or SendGrid):** Transactional email -- Resend recommended for new projects, free tier for MVP

**Version pinning targets:** See TECHNICAL_STACK.md for complete `requirements.txt` and `package.json` recommendations.

### Expected Features

**Must have (table stakes for an AI job search tool):**
- Resume upload and parsing (primary onboarding path -- NOT LinkedIn-dependent)
- Job matching with deal-breaker enforcement (salary floors, location, visa sponsorship)
- ATS-optimized resume tailoring (single-column DOCX, keyword gap analysis, never fabricate)
- Application pipeline tracking (manual + email-forwarding-based)
- Daily briefing with actionable items
- Emergency brake (pause all agent activity instantly)
- Tiered autonomy (L0: suggest only, L1: draft for user, L2: act with approval, L3: autonomous within rules)

**Should have (differentiators):**
- H1B sponsorship intelligence from USCIS + DOL government data
- Auto-apply to company career pages (direct apply only, never platform apply)
- Employer blocklist with encryption (stealth mode)
- LLM cost tracking with per-user budget caps (<$6/user/month)

**Defer to v2+:**
- Gmail/Outlook OAuth email parsing (requires CASA assessment at $5K-$75K/year -- use email forwarding for MVP)
- LinkedIn Network Agent automation (very high legal risk, redesign as "draft suggestions" instead)
- LinkedIn profile import as primary path (use resume upload + LinkedIn data export as fallback)
- Full event sourcing (simple append-only audit log is sufficient)
- pgvector semantic job matching (start with keyword matching)

### Architecture Approach

JobPilot follows a Coordinator-Worker (Supervisor) pattern where a central Orchestrator routes tasks to specialized agents (Job Scout, Resume, Apply, Pipeline, Follow-up). Routing is deterministic code, not LLM-driven -- task type, user tier, and schedule determine which agent runs. LLMs are used only within individual agents for their specialized tasks. The L0-L3 autonomy enforcement is implemented as decorators on agent methods, not as API middleware, because agents run in Celery workers without HTTP context.

**Major components:**
1. **Orchestrator (TaskRouter + StateManager + TierEnforcer)** -- Deterministic task routing, state management, autonomy enforcement. Must NOT become a god object; split into focused sub-components.
2. **Agent Framework (BaseAgent)** -- Common base with brake check, tier enforcement, cost tracking. Each specialized agent extends this.
3. **Approval Queue** -- Bridge between L2 (human-approves) and L3 (autonomous). Pending action table + WebSocket notification. Missing from current schema.
4. **Background Processing (Celery + Redis)** -- Separate queues: `agents` (high priority), `briefings` (time-sensitive), `scraping` (low priority, rate-limited), `default`.
5. **Real-Time Events (WebSocket + Redis Pub/Sub)** -- Per-user channels for agent status updates. Pub/Sub is sufficient (no need for Redis Streams).
6. **Three-Layer Cache** -- Redis (L1: user prefs, brake state) -> Materialized Views (L2: match scores, H1B aggregations) -> TanStack Query (L3: briefings, job lists).

### Critical Pitfalls

1. **Job board data is not freely available.** LinkedIn, Indeed, and Glassdoor have no public APIs and actively block scraping. Use aggregator APIs (JSearch, Adzuna, SerpAPI) exclusively. Do NOT promise LinkedIn job monitoring in MVP. *(Sources: TECHNICAL_STACK, DOMAIN_CONCERNS -- both agree)*

2. **Gmail OAuth triggers $5K-$75K/year CASA compliance.** The Pipeline Agent's email parsing feature requires Google's restricted `gmail.readonly` scope, which mandates an annual third-party security audit. Start with email forwarding (zero compliance cost), pursue CASA only when revenue justifies it. *(Source: DOMAIN_CONCERNS)*

3. **Auto-apply on LinkedIn/Indeed violates ToS and will be detected.** The Apply Agent must ONLY automate Direct Apply (company career pages), never Platform Apply (Easy Apply, Indeed Apply). Build graceful manual fallback for unsupported ATS forms. *(Source: DOMAIN_CONCERNS)*

4. **Dual database abstraction will cause drift.** The codebase has both Supabase SDK and SQLAlchemy accessing the same database with no clear boundaries. Resolve immediately: SQLAlchemy for ALL application data, Supabase SDK for auth/storage/realtime ONLY. Never use both to access the same table. *(Source: ARCHITECTURE_PATTERNS)*

5. **Agent orchestration framework disagreement.** TECHNICAL_STACK recommends LangGraph (production-grade state management, human-in-the-loop, checkpointing). ARCHITECTURE_PATTERNS recommends custom orchestrator (lighter, no framework lock-in, existing LLMClient abstraction is sufficient). This must be resolved via time-boxed prototype. *(See "Key Architectural Decisions" below)*

6. **Resume fabrication is a legal liability.** The Resume Agent must NEVER invent qualifications -- only rephrase and reorganize existing experience. This is both a PRD requirement and a legal necessity. Enforce with DeepEval hallucination testing (threshold 0.9). *(Sources: DOMAIN_CONCERNS, QUALITY_STRATEGY)*

---

## Key Architectural Decisions (ADRs Needed)

These decisions must be made before or during Phase 1. They affect every subsequent phase.

### ADR-1: Agent Orchestration Framework

**Options:**
| Option | Champion | Pros | Cons |
|--------|----------|------|------|
| **LangGraph 1.0** | TECHNICAL_STACK | Human-in-the-loop built-in, durable state, checkpointing, audit via tracing | Adds ~50-100MB deps, learning curve, ecosystem lock-in |
| **Custom orchestrator** | ARCHITECTURE_PATTERNS | Lighter, extends existing LLMClient, no framework lock-in, 40% latency reduction cited | Reinvents HIL, checkpointing, state persistence; more code to maintain |

**Recommendation:** Time-box a 2-day prototype with LangGraph. If the autonomy tier enforcement maps cleanly onto LangGraph's interrupt/checkpoint model, use it. If not, go custom. The risk of going custom is higher (reinventing production patterns) but the risk of LangGraph is framework lock-in with a v1.0 that is still maturing.

### ADR-2: Database Access Pattern

**Decision (consensus):** SQLAlchemy as primary for all application data. Supabase SDK only for auth token validation, file storage, and realtime subscriptions. Wire up SQLAlchemy async engine + Alembic immediately. Use direct connections (port 5432), not PgBouncer, until 5000+ DAU.

### ADR-3: Job Data Acquisition Strategy

**Decision (consensus):** Aggregator APIs only for MVP. JSearch (RapidAPI) as primary, Adzuna as secondary, SerpAPI Google Jobs as tertiary. No scraping. No LinkedIn promises. Budget needed: $50-200/month for API access at scale.

### ADR-4: Email Pipeline Approach

**Decision (consensus):** Email forwarding for MVP (zero compliance cost). Begin CASA assessment process only when revenue exceeds ~$50K ARR. Design the `EmailProvider` abstraction layer now so OAuth can be added later without refactoring.

### ADR-5: LinkedIn Integration Scope

**Decision (consensus):** Resume upload as primary onboarding. LinkedIn data export (GDPR download) as secondary. LinkedIn profile fetch as tertiary fallback with clear failure handling. NO LinkedIn automation (Network Agent redesigned as suggestion-only).

---

## Implications for Roadmap

### Phase 1: Foundation Modernization
**Rationale:** Every researcher identified foundation gaps as the first priority. Nothing else works until deps are upgraded, auth is wired, and the DB layer is resolved.
**Delivers:** Modern, buildable codebase with CI/CD, auth, background jobs, and resolved database architecture.
**Addresses:** Dependency modernization, CRA->Vite, TypeScript adoption, Clerk auth, Celery+Redis setup, SQLAlchemy async engine, Alembic migrations, CI/CD pipeline (GitHub Actions), security scanning (Bandit, gitleaks).
**Avoids:** Dual database abstraction drift, building on deprecated dependencies.
**Duration estimate:** 1-2 weeks.
**Must also start:** Google OAuth app registration (2-6 week verification), LinkedIn Partner API exploration (long lead time).

### Phase 2: Agent Framework Core
**Rationale:** Must validate the agent lifecycle (trigger -> orchestrate -> execute -> store -> notify) before building individual agents. The orchestration approach (ADR-1) must be resolved here.
**Delivers:** BaseAgent class, Orchestrator (task router + tier enforcer), emergency brake, WebSocket event system, approval queue schema, agent contract tests, deterministic LLM mock layer.
**Addresses:** L0-L3 autonomy enforcement, emergency brake state machine, agent output schema with rationale/confidence/alternatives.
**Avoids:** God Orchestrator anti-pattern, shared mutable state between agents, synchronous agent calls.
**Research flag:** NEEDS DEEPER RESEARCH -- LangGraph vs. custom decision, LLM mock strategy for testing.

### Phase 3: Job Scout Agent (First Agent)
**Rationale:** Simplest agent (read-only, no approval queue needed for L0-L1). Proves the end-to-end pipeline: API data fetch -> match -> store -> briefing -> notify. Validates cost tracking, caching, and scheduling.
**Delivers:** Job matching with deal-breaker enforcement, daily briefing generation, job data pipeline from JSearch/Adzuna, three-layer caching, LLM cost tracking.
**Addresses:** Job matching (F4), daily briefings (F3), deal-breaker compliance.
**Avoids:** Single source dependency (multi-API strategy), over-engineering agent memory (start with PostgreSQL JSONB).
**Research flag:** NEEDS DEEPER RESEARCH -- job board API rate limits, deduplication strategy, match scoring algorithm.

### Phase 4: Resume Agent + ATS Optimization
**Rationale:** Resume tailoring is high-value and lower-risk than auto-apply. Builds on agent framework from Phase 2.
**Delivers:** Master resume storage, job-specific resume tailoring, keyword gap analysis, ATS-optimized DOCX output, diff view, never-fabricate enforcement.
**Addresses:** Resume tailoring (F5), ATS compatibility, copy-on-write pattern for master resume protection.
**Avoids:** Resume fabrication (DeepEval hallucination testing, threshold 0.9), ATS format violations (single-column, standard headings, no images).
**Standard patterns:** Well-documented ATS rules, PDF/DOCX generation is straightforward.

### Phase 5: Pipeline Tracking + Email Forwarding
**Rationale:** Pipeline tracking is core UX but does not require OAuth. Email forwarding approach avoids CASA compliance cost entirely.
**Delivers:** Application pipeline board, email forwarding setup flow, email parsing (server-side, no OAuth), pipeline status updates, manual entry.
**Addresses:** Pipeline tracking (F6), email-based status updates.
**Avoids:** CASA assessment costs, Gmail restricted scope compliance, email scope creep.
**Standard patterns:** Email parsing with keyword pre-filter is straightforward.

### Phase 6: H1B Sponsorship Intelligence
**Rationale:** Requires dedicated ETL pipeline from government data. 2-3 weeks for initial build + employer name normalization. Decoupled from other agents.
**Delivers:** H1B sponsor database from USCIS + DOL data, approval rates per employer, wage ranges, employer name resolution, quarterly refresh pipeline, freshness badges.
**Addresses:** H1B features (F11), visa-aware job matching.
**Avoids:** Scraping third-party H1B sites (prohibited by their ToS), presenting stale data as current, conflating initial vs. continuing petitions in approval rates.
**Research flag:** NEEDS DEEPER RESEARCH -- employer name normalization strategy, USCIS/DOL data joining accuracy.

### Phase 7: Apply Agent (Auto-Apply)
**Rationale:** Highest architectural complexity. Requires approval queue (L2), form-filling across diverse ATS platforms, and careful legal/ethical constraints. Must build on proven patterns from all previous phases.
**Delivers:** Direct-apply automation for top 5 ATS platforms (Workday, Greenhouse, Lever, iCIMS, Taleo), quality gate (70% match minimum), volume caps (10/day L3, 5-7/day L2), graceful manual fallback for unsupported forms.
**Addresses:** Auto-apply (F9), approval queue for L2 tier.
**Avoids:** Platform apply (LinkedIn/Indeed -- ToS violation), application spam, CAPTCHA-blocked forms without fallback, fabricated application content.
**Research flag:** NEEDS DEEPER RESEARCH -- ATS form-filling reliability per platform, CAPTCHA handling, EU AI Act compliance for applicant-side tools.

### Phase 8: Advanced Features + Production Hardening
**Rationale:** These features are either high-risk (Network Agent), high-cost (Gmail OAuth), or non-critical for launch.
**Delivers:** Gmail/Outlook OAuth (post-CASA), Network Assistant (suggestion-only, no automation), Playwright E2E suite, OWASP ZAP dynamic testing, Grafana dashboards, LLM cost alerting.
**Addresses:** Email OAuth (F6 upgrade), network features (F14 redesigned), production observability.
**Avoids:** LinkedIn automation (legal risk), premature CASA investment.

### Phase Ordering Rationale

1. **Foundation first** because every researcher identified dependency upgrades and missing infrastructure (CI/CD, auth, background jobs) as blocking all feature work.
2. **Agent framework before agents** because the orchestration pattern, tier enforcement, and emergency brake are cross-cutting concerns that affect every agent.
3. **Job Scout as first agent** because it is read-only (simplest), validates the full lifecycle, and delivers immediate user value (job matching + briefings).
4. **Resume before Apply** because resume tailoring is a dependency for auto-apply (applications need tailored resumes) and is lower-risk.
5. **Pipeline before H1B** because pipeline tracking is core UX for all users, while H1B is a specific tier feature.
6. **Apply Agent late** because it has the highest legal/ethical complexity and depends on all prior patterns being proven.
7. **Advanced features last** because they are either gated by external processes (CASA) or carry legal risk (LinkedIn automation).

### Research Flags Summary

**Needs deeper research during planning:**
- **Phase 2:** Agent orchestration approach (LangGraph vs. custom -- resolve via prototype)
- **Phase 2:** LLM mock strategy for deterministic agent testing
- **Phase 3:** Job board API rate limits, pricing at scale, deduplication
- **Phase 6:** USCIS/DOL data joining, employer name normalization
- **Phase 7:** ATS form-filling reliability, CAPTCHA handling, EU AI Act applicability

**Standard patterns (skip research-phase):**
- **Phase 1:** CRA->Vite migration, Clerk setup, Celery+Redis, GitHub Actions CI/CD
- **Phase 4:** ATS resume formatting rules, DOCX generation
- **Phase 5:** Email forwarding + server-side parsing
- **Phase 8:** Sentry/OTel instrumentation, Playwright E2E

---

## Consolidated Open Questions

From all 4 research files, these questions need answers:

### Must Resolve Before Phase 1
1. **LangGraph vs. custom orchestrator:** Time-box a 2-day prototype to decide. (TECHNICAL_STACK vs. ARCHITECTURE_PATTERNS disagree)
2. **Job board data budget:** Monthly budget for API access determines which aggregators are viable. ($50-200/month estimated)
3. **Supabase local dev strategy:** Local Supabase CLI instance vs. dedicated test project for integration tests? (QUALITY_STRATEGY)

### Must Resolve Before Phase 2
4. **LLM mock fidelity:** How realistic do mocks need to be? Recorded responses (VCR-style) vs. templated vs. actual LLM with low temperature. (QUALITY_STRATEGY)
5. **DeepEval CI cost:** Benchmark actual OpenAI API cost per eval run before committing to per-PR evaluations. (QUALITY_STRATEGY)

### Must Resolve Before Phase 3
6. **Google OAuth verification timing:** Submit for verification in Phase 1 even though email features are Phase 5. 2-6 week lead time. (TECHNICAL_STACK)
7. **Tailwind v3 vs. v4:** Recommend v3 for stability. (TECHNICAL_STACK)
8. **React 18 vs. 19:** Recommend 18.x -- no need for Server Components or Actions. (TECHNICAL_STACK)

### Must Resolve Before Phase 6
9. **H1B data freshness expectations:** PRD says "<24 hours" but government data is quarterly. Reframe as "within 48 hours of government release." (DOMAIN_CONCERNS)

### Must Resolve Before Phase 7
10. **EU AI Act applicability to applicant-side tools:** Unclear whether JobPilot's auto-apply falls under "high-risk AI in employment." Legal review needed. (DOMAIN_CONCERNS)
11. **Auto-apply success rate metric:** PRD target of 95% is only achievable for direct apply (career pages), not platform apply. Reframe metric. (DOMAIN_CONCERNS)

### Longer-Term
12. **Railway scaling limits:** At what user count does Railway's pricing become untenable? Need cost modeling. (QUALITY_STRATEGY)
13. **Email service choice:** Resend (recommended) vs. SendGrid (existing ecosystem). Resend is newer with less track record. (TECHNICAL_STACK)

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack (TECHNICAL_STACK) | HIGH | Versions verified via PyPI/npm; upgrade paths well-documented |
| Features / Domain (DOMAIN_CONCERNS) | HIGH | Government sources, court rulings, platform ToS directly verified |
| Architecture (ARCHITECTURE_PATTERNS) | MEDIUM-HIGH | Patterns are well-established; custom autonomy tier model is novel (untested in production) |
| Quality / Testing (QUALITY_STRATEGY) | MEDIUM-HIGH | Standard CI/CD patterns; DeepEval for LLM testing is emerging but well-documented |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

1. **Agent orchestration framework choice:** Researchers disagree. Resolve with prototype before committing.
2. **LangGraph production maturity:** v1.0 is new (October 2025). Production patterns still emerging. Medium confidence.
3. **Job board API pricing at scale:** 100K jobs/day target from PRD needs cost modeling against JSearch/Adzuna paid tiers.
4. **CASA assessment actual cost:** Range of $500-$75K is too wide. Need vendor quotes before Phase 5.
5. **Supabase + asyncpg DuplicatePreparedStatementError:** Known issue under burst load. Mitigations documented but not yet validated for this project.
6. **DeepEval soft failure thresholds:** Industry emerging practice. Thresholds (0.7 quality, 0.9 fabrication) need tuning per agent through experimentation.
7. **L0-L3 autonomy enforcement pattern:** Custom design, not validated in production elsewhere. Needs careful testing.

---

## Cross-Reference: Where Researchers Agree and Disagree

### Strong Agreement (4/4 researchers)
- Foundation modernization must come before feature work
- Celery + Redis for background processing
- SQLAlchemy as primary DB access (not Supabase SDK for app logic)
- Clerk for authentication
- CI/CD pipeline is a critical missing piece
- Emergency brake is architecturally important and well-designed

### Agreement with Nuance (3/4 or qualified agreement)
- Job data via aggregator APIs, not scraping (STACK + DOMAIN agree; ARCHITECTURE assumes it)
- Resume upload as primary onboarding (DOMAIN strongly recommends; STACK mentions LinkedIn fetch as secondary)
- OpenTelemetry + Sentry for observability (STACK + QUALITY agree; ARCHITECTURE mentions it)

### Disagreement Requiring Resolution
- **Agent framework:** TECHNICAL_STACK recommends LangGraph; ARCHITECTURE_PATTERNS recommends custom + skip langchain-core entirely. ARCHITECTURE explicitly calls LangGraph "overkill."
- **langchain-core usage:** ARCHITECTURE says skip it (existing LLMClient abstraction is sufficient). STACK says use langchain-core model wrappers + LangGraph. Cannot use both approaches.
- **Email service:** STACK recommends Resend (newer, developer-first). Existing architecture doc mentions SendGrid. Low-stakes decision.

---

## Sources

### Primary (HIGH confidence)
- USCIS H-1B Employer Data Hub (government source)
- DOL OFLC Performance Data (government source)
- Google Gmail API Scopes and CASA documentation
- LinkedIn User Agreement and Terms of Service
- hiQ v. LinkedIn court ruling and settlement
- OWASP API Security Top 10
- PyPI and npm package registries (version verification)
- CRA deprecation announcement (React team)
- Sentry official documentation for FastAPI/OTel
- DeepEval official documentation

### Secondary (MEDIUM-HIGH confidence)
- LangGraph 1.0 documentation and blog posts
- Supabase + asyncpg GitHub issues (community-reported)
- ATS compatibility guides (multiple industry sources consistent)
- Celery + FastAPI integration guides
- Railway deployment documentation

### Tertiary (MEDIUM confidence, needs validation)
- LangGraph production performance claims
- Resend vs. SendGrid comparison (landscape changes frequently)
- Job board API pricing (changes frequently)
- DeepEval soft failure threshold recommendations
- EU AI Act applicability to applicant-side tools

---

*Research completed: 2026-01-30*
*Researchers: TECHNICAL_STACK, ARCHITECTURE_PATTERNS, DOMAIN_CONCERNS, QUALITY_STRATEGY*
*Synthesizer confidence: MEDIUM-HIGH*
*Ready for roadmap: YES*
