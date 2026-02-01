# Project State

## Project Reference

**Core value:** "Your AI Career Agent that works 24/7" -- multi-agent platform that automates job search, resume tailoring, application submission, and pipeline tracking with tiered autonomy (L0-L3).
**Current focus:** Phase 4 - Job Discovery (In Progress)

## Current Position

Phase: 4 of 9 (Job Discovery)
Plan: 9 of ? in current phase
Status: In progress
Last activity: 2026-02-01 -- Completed 0-2 (Row-Level Security Policies)

Progress: [██████████████████████████████░] ~50%

## Performance Metrics

**Velocity:**
- Total plans completed: 28
- Average duration: ~6 min
- Total execution time: ~171 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 8/8 | ~63 min | ~8 min |
| 2 | 6/6 | ~32 min | ~5 min |
| 3 | 8/8 | ~40 min | ~5 min |
| 4 | 5/? | ~32 min | ~6 min |

## Accumulated Context

### Decisions

- [Roadmap]: 9 phases derived from 11 BMAD Epics (114 stories). MVP boundary at Phase 6.
- [Roadmap]: Stories 4-2, 4-3 redesigned -- aggregator APIs (JSearch, Adzuna) replace LinkedIn/Indeed scraping (ADR-3)
- [Roadmap]: Stories 6-2, 6-3 deferred -- email forwarding replaces Gmail/Outlook OAuth for MVP (ADR-4)
- [Roadmap]: Resume upload is primary onboarding, not LinkedIn URL extraction (ADR-5)
- [Roadmap]: Story 0-1 (Database Schema) already in review from prior BMAD sprint
- [01-01]: ADR-6 resolved -- Resend chosen over SendGrid for transactional email
- [01-01]: Ruff replaces black + flake8 as single linter/formatter
- [01-01]: LLM clients use raw httpx (not SDK) -- safe from openai v2 breaking changes; SDK migration deferred to Phase 3
- [01-02]: `allowJs: true` in tsconfig.json for incremental JS-to-TS migration
- [01-02]: `strict: false` initially -- tighten as files convert to TypeScript
- [01-02]: `"build": "vite build"` not `"tsc && vite build"` -- tsc would fail on unconverted files
- [01-02]: ESM format for all config files (package.json has `"type": "module"`)
- [01-03]: ADR-2 resolved -- SQLAlchemy is the ONLY app data access layer; Supabase SDK restricted to storage/auth/realtime
- [01-03]: Direct connection (port 5432) with statement_cache_size=0 and jit=off for Supabase compatibility
- [01-03]: Alembic baseline migration stamped (not executed) -- tables already exist from Supabase migration 00001
- [01-04]: App factory pattern (create_app) for composable middleware and testability
- [01-04]: Legacy routes preserved alongside new /api/v1/ routes for backward compatibility
- [01-04]: Rate limiter defaults all users to Pro tier (1000 req/hr) until user tier DB lookup is implemented
- [01-04]: In-memory rate limit fallback when Redis unavailable (per-process, dev-only)
- [01-05]: Celery tasks use lazy imports + asyncio.run() to bridge sync workers with async SQLAlchemy
- [01-05]: Queue routing by naming convention: agent_* -> agents, briefing_* -> briefings, scrape_* -> scraping
- [01-05]: Reliability settings: acks_late, prefetch=1, reject_on_worker_lost, soft_timeout=240s, hard_timeout=300s
- [01-06]: AuthProvider gracefully degrades when VITE_CLERK_PUBLISHABLE_KEY is missing (renders children without auth wrapper)
- [01-06]: Legacy routes (email, linkedin, author-styles, settings) remain public; only /dashboard is protected
- [01-06]: Public api instance preserved for unauthenticated calls; useApiClient hook for authenticated calls
- [01-07]: ConsoleSpanExporter for dev, OTLP placeholder for production -- swap when collector provisioned
- [01-07]: Cost tracking is fire-and-forget (never breaks hot path) -- exceptions logged but swallowed
- [01-07]: Budget alert at 80% of $6/month via Redis pub/sub channel alerts:cost:{user_id}
- [01-07]: Admin endpoints under /api/v1/admin/ prefix
- [01-08]: Transactional email (transactional_email.py) separate from legacy cold-email generation (email_service.py)
- [01-08]: WebSocket auth uses query parameter token; full JWT validation is TODO
- [01-08]: GDPR endpoints use raw SQL text() for resilience when tables do not yet exist
- [01-08]: Storage service returns placeholders when Supabase is not configured
- [02-01]: Text columns (not PG Enum) for onboarding_status, work_arrangement, autonomy_level -- avoids ALTER TYPE migrations
- [02-01]: Hybrid relational + JSONB schema for user_preferences -- deal-breakers get dedicated indexed columns, evolving prefs go in JSONB
- [02-01]: Migration 0002 written manually (no DB connection) -- review when first applied
- [02-02]: AnalyticsProvider decoupled from Clerk useUser -- standalone identifyUser() export avoids crash when Clerk key missing
- [02-03]: Resume parser uses OpenAI SDK v2 structured outputs (AsyncOpenAI.beta.chat.completions.parse) -- separate from legacy httpx client
- [02-03]: ensure_user_exists shared between onboarding and preferences modules (defined in preferences.py, imported by onboarding.py)
- [02-03]: LinkedIn extraction designed for graceful failure -- returns None on any error, never raises
- [02-04]: ensure_user_exists also defined in preferences.py (parallel with Plan 03); extract to shared module when consolidating
- [02-04]: Zustand stores use arrays (not Sets) for completedSteps -- Sets don't serialize to JSON
- [02-04]: Autonomy level l0 treated as "not configured" in missing_sections to encourage active user choice
- [02-05]: Each onboarding step manages its own navigation buttons; WizardShell used for step indicator only
- [02-05]: SkillTagInput is a local component in ProfileReview (not extracted to shared/) -- specific to onboarding
- [02-06]: Each preference step manages its own nav buttons (consistent with onboarding pattern)
- [02-06]: TagInput and ChipPicker extracted as shared components in preferences/ directory
- [02-06]: OnboardingGuard allows through on API failure -- graceful degradation over blocking
- [02-06]: Preferences store reset on final submit to prevent stale state on revisit
- [03-01]: ADR-1 resolved -- Custom orchestrator over LangGraph. No dual PG driver, Celery handles crash recovery, ~30 LOC delta for approval queue
- [03-01]: LangGraph deps removed from requirements.txt; shared deps kept (langfuse, celery-redbeat, vcrpy, pytest-recording)
- [03-01]: Prototype files kept as reference (_prototype_langgraph.py, _prototype_custom.py) but not imported by production code
- [03-02]: Text constant classes (not PG Enum) for ApprovalStatus, BrakeState, ActivitySeverity, BriefingType -- avoids ALTER TYPE migrations
- [03-02]: No langgraph_thread_id columns in approval_queue -- ADR-1 custom orchestrator decision
- [03-02]: Migration 0003 written manually (no DB connection) -- review when first applied
- [03-03]: BaseAgent.run() raises BrakeActive exception rather than returning blocked output -- callers must handle
- [03-03]: Brake state uses dual Redis structures: simple flag (paused:{user_id}) for O(1) checks + hash (brake_state:{user_id}) for full state machine
- [03-03]: verify_brake_completion uses Celery inspect API best-effort -- assumes stopped if broker unreachable
- [03-03]: AutonomyGate returns plain string literals not enums for simpler caller pattern matching
- [03-04]: Orchestrator is module-level singleton with TaskRouter class + dispatch_task/get_user_context functions
- [03-04]: Langfuse client uses lazy init with NoOp fallback when SDK unavailable or keys missing
- [03-04]: cost_tracker.py kept as fallback for 1 sprint -- Langfuse is primary observability layer
- [03-04]: Each Celery agent task creates explicit Langfuse trace (contextvars don't propagate across processes)
- [03-04]: agent_apply limited to 1 retry (non-idempotent); other agent tasks get 2 retries
- [03-04]: cleanup_expired_approvals runs every 6 hours via Celery beat_schedule
- [03-05]: Static API routes (/latest, /settings) registered before dynamic /{briefing_id} to prevent FastAPI matching conflicts
- [03-05]: No-LLM fallback: briefing built from raw data when OPENAI_API_KEY not configured
- [03-05]: RedBeat lock disabled (redbeat_lock_key=None) for single-beat deployments
- [03-05]: Timezone conversion at schedule creation time; DST correction via weekly cleanup task
- [03-06]: No confirmation dialog on brake activation -- speed critical per Story 3-6 AC
- [03-06]: EmergencyBrake renders only for signed-in users; public pages unaffected
- [03-06]: WebSocket auto-reconnect with 3-second delay; polling only during transitional states (5s interval)
- [03-07]: BriefingCard is dashboard hero -- prominently displayed at top, above stats cards
- [03-07]: 12-hour AM/PM picker on frontend, converted to 24h for API -- user-friendly display
- [03-07]: Browser timezone auto-detected via Intl.DateTimeFormat, editable from curated list
- [03-07]: Lite briefing rendered with amber styling and cached-data messaging
- [03-08]: VCR cassette infra with record_mode=none; switch to once when recording against live API
- [03-08]: Integration tests marked @pytest.mark.integration with manual verification docs
- [03-08]: All agent tests use mocked Redis/DB; no real connections needed
- [04-01]: SHA-256 dedup keys (URL or title+company+location hash) for job deduplication
- [04-01]: 5-category scoring (title 25, location 20, salary 20, skills 20, seniority 15) -- total 0-100
- [04-01]: Deal-breakers skip job entirely (no Match record created); unknown salary is NOT a deal-breaker
- [04-01]: Neutral mid-range scores when preferences are empty (not zeros)
- [04-04]: Two-stage scoring: heuristic pre-filter (>= threshold*0.5) then GPT-3.5-turbo LLM refinement
- [04-04]: Company size scoring (0-10 pts) added to heuristic; total normalized from 110 to 0-100 via int(raw/1.1)
- [04-04]: MATCH_SCORE_THRESHOLD=40 replaces score>0 filter; LLM_SCORING_ENABLED feature flag
- [04-04]: Cost tracking with token estimation (len//4); lazy imports for OpenAIClient and cost_tracker
- [04-09]: SwipeEvent is append-only (TimestampMixin only); LearnedPreference uses SoftDeleteMixin for rejected patterns
- [04-09]: Pattern detection thresholds: min 3 occurrences, 60%+ dismiss rate, confidence capped at 0.95
- [04-09]: apply_learned_preferences implemented but NOT wired into live scoring pipeline (future integration)
- [04-09]: Score adjustments: -15 * confidence for dismissed patterns, +10 * (1-confidence) for saved patterns
- [0-2]: UUID validation over bind params for SET LOCAL -- async PG drivers don't reliably support bind params with SET
- [0-2]: No WITH CHECK clause in RLS policies -- USING alone covers both read and write for FOR ALL
- [0-2]: users and jobs tables excluded from RLS (not user-scoped)

### Pending Todos

- Start Google OAuth app registration (2-6 week lead time, needed Phase 6+)
- ~~Resolve email service choice: Resend vs SendGrid (Phase 1, low stakes)~~ RESOLVED in 01-01
- Budget for job board aggregator APIs: $50-200/month (needed Phase 4)

### Blockers/Concerns

- ~~ADR-1 (LangGraph vs Custom orchestrator) MUST be resolved at start of Phase 3 via 2-day prototype~~ RESOLVED in 03-01 (Custom wins)
- ~~Dual database abstraction (Supabase SDK vs SQLAlchemy) must be resolved in Phase 1 -- blocks all data work~~ RESOLVED in 01-03 (ADR-2)
- ~~CRA is deprecated with no security patches -- migration to Vite is blocking for frontend work~~ RESOLVED in 01-02

## Session Continuity

Last session: 2026-02-01
Stopped at: Completed 0-2 (Row-Level Security Policies). RLS on 8 user-scoped tables with user isolation + dev bypass policies, transaction-scoped context helper, 85 tests.
Resume file: None
