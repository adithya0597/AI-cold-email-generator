# CLAUDE.md - JobPilot Project Reference

## Project Overview

**JobPilot** is an AI-powered multi-agent career platform that helps job seekers with automated job discovery, resume tailoring, application tracking, and email generation.

**Core Capabilities:**
- Multi-agent system with tiered autonomy (L0-L3): suggestions-only → autonomous
- Daily briefings with personalized job matches
- Resume parsing and tailoring per job
- Cold email and LinkedIn post generation
- H1B sponsorship research and scoring
- Application pipeline management with follow-up automation

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | FastAPI, SQLAlchemy async (asyncpg), Celery + Redis, Clerk auth, Pydantic 2, OpenAI/Anthropic clients |
| **Frontend** | React 18, TypeScript, Vite 6, Tailwind CSS, Zustand, TanStack Query, Clerk, react-hook-form + Zod |
| **Database** | Supabase PostgreSQL, asyncpg driver, Alembic migrations |
| **Testing** | pytest + pytest-asyncio (backend), Vitest + testing-library (frontend) |
| **Observability** | Sentry, Langfuse (LLM tracing), PostHog analytics |

## Repository Layout

| Directory | Purpose | Details |
|-----------|---------|---------|
| `backend/` | FastAPI backend | See `backend/CLAUDE.md` |
| `frontend/` | React SPA | See `frontend/CLAUDE.md` |
| `supabase/` | Database migrations | See `supabase/CLAUDE.md` |
| `docs/` | Project documentation | Architecture and analysis docs |

## Common Commands

### Backend
```bash
# Run dev server
uvicorn app.main:app --reload --port 8000

# Run tests (from backend/)
pytest                           # all tests
pytest -x                        # stop on first failure
pytest -k "test_job_scout"       # filter by name
pytest --cov=app                 # with coverage

# Linting and types
ruff check app/
mypy app/
```

### Frontend
```bash
npm run dev          # Vite dev server (port 3000)
npm test             # Vitest tests
npm run build        # Production build
npm run lint         # ESLint
```

### Database
```bash
supabase db push     # Apply migrations to Supabase
python backend/scripts/run_migrations.py  # Local migration runner
```

## Architecture Rules

### Critical Constraints

1. **No Network I/O in DB Transactions** — Never call external APIs (LLM, web scrape) while holding a database transaction. Fetch data first, then commit.

2. **Type Hints Required** — All backend functions must have type hints. Use `mypy` to verify.

3. **Lazy Imports in Celery Tasks** — Import heavy modules inside task functions to avoid worker startup overhead.

4. **Privacy Invariant** — Enterprise admin queries return aggregate-only data. Never expose individual user data cross-tenant.

5. **RLS Defense-in-Depth** — Row-Level Security is enabled on all user-scoped tables. Backend sets `SET LOCAL app.current_user_id = '<uuid>'` per transaction.

6. **Clerk Auth Flow** — All authenticated endpoints use Clerk JWT. Frontend includes token via `useApiClient` hook; backend validates via `ClerkAuth` dependency.

7. **API Versioning** — All new endpoints go under `/api/v1/`. Legacy routes remain at root for backward compatibility.

## Naming Conventions

| Context | Convention | Example |
|---------|------------|---------|
| Python files | snake_case | `job_scout.py`, `email_service.py` |
| Python functions | snake_case | `generate_cold_email()`, `_analyze_tone()` |
| Python classes | PascalCase | `JobScoutAgent`, `EmailService` |
| TypeScript components | PascalCase | `SwipeCard.tsx`, `BriefingDetail.tsx` |
| TypeScript services | camelCase files, named exports | `matches.ts`, `export const matchesApi` |
| SQL tables/columns | snake_case | `user_id`, `created_at` |
| SQL indexes | idx_ prefix | `idx_applications_user_id` |

## Configuration

- **Backend:** `pydantic-settings` via `app/config.py`. Access as `from app.config import settings`.
- **Frontend:** Environment variables with `VITE_` prefix in `.env`.
- **Never commit** `.env` files. Use `.env.example` as template.

## Error Handling

### Backend
- Custom `ServiceError` hierarchy in `app/core/error_handlers.py`
- Subclasses: `ValidationError`, `LLMGenerationError`, `WebScrapingError`, `RateLimitError`
- Use `@async_error_handler(fallback_value=None)` decorator for graceful degradation

### Frontend
- Sentry `ErrorBoundary` wraps the app
- `react-toastify` for user-facing errors: `toast.error('Failed to load matches')`
- API errors caught in services and re-thrown with context

## Git Workflow

1. Branch from `main` for features: `feature/job-scout-filters`
2. Use `bd` (beads) for issue tracking — not markdown files
3. PR-based merges with review required
4. **Session close protocol:** Always `git status`, `bd sync`, commit, push before ending

## Reference Docs

Detailed architecture analysis in `.planning/codebase/`:
- `ARCHITECTURE.md` — Layer definitions and data flow
- `CONVENTIONS.md` — Code style and patterns
- `STACK.md` — Full dependency list
- `STRUCTURE.md` — Directory purposes and file locations
