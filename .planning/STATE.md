# Project State

## Project Reference

**Core value:** "Your AI Career Agent that works 24/7" -- multi-agent platform that automates job search, resume tailoring, application submission, and pipeline tracking with tiered autonomy (L0-L3).
**Current focus:** Phase 2 - Onboarding + Preferences (In Progress)

## Current Position

Phase: 2 of 9 (Onboarding + Preferences)
Plan: 1 of 6 in current phase
Status: In progress
Last activity: 2026-01-31 -- Completed 02-01-PLAN (Database Schema + Backend Models)

Progress: [█████████░] ~12%

## Performance Metrics

**Velocity:**
- Total plans completed: 9
- Average duration: ~7 min
- Total execution time: ~68 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 8/8 | ~63 min | ~8 min |
| 2 | 1/6 | ~5 min | ~5 min |

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

### Pending Todos

- Start Google OAuth app registration (2-6 week lead time, needed Phase 6+)
- ~~Resolve email service choice: Resend vs SendGrid (Phase 1, low stakes)~~ RESOLVED in 01-01
- Budget for job board aggregator APIs: $50-200/month (needed Phase 4)

### Blockers/Concerns

- ADR-1 (LangGraph vs Custom orchestrator) MUST be resolved at start of Phase 3 via 2-day prototype
- ~~Dual database abstraction (Supabase SDK vs SQLAlchemy) must be resolved in Phase 1 -- blocks all data work~~ RESOLVED in 01-03 (ADR-2)
- ~~CRA is deprecated with no security patches -- migration to Vite is blocking for frontend work~~ RESOLVED in 01-02

## Session Continuity

Last session: 2026-01-31
Stopped at: Completed 02-01-PLAN (Database Schema + Backend Models). Ready for 02-02 (Analytics) or 02-03/02-04 (Wave 2).
Resume file: None
