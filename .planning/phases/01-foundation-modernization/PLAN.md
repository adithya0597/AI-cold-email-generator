---
phase: 01-foundation-modernization
plans: 8
type: phase-plan
---

# Phase 1: Foundation Modernization -- Execution Plan

## Phase Goal

Developers have a modern, buildable codebase with auth, background jobs, CI/CD, and resolved database architecture -- enabling all subsequent feature work.

## Success Criteria (all must be TRUE at phase end)

1. Running `npm run dev` starts a Vite+React+TypeScript frontend that connects to the FastAPI backend
2. A user can sign up and log in via Clerk (LinkedIn OAuth) and see a protected dashboard page
3. A Celery worker can pick up a task from Redis, execute it, and record the result in PostgreSQL via SQLAlchemy
4. Pushing to main triggers a GitHub Actions CI pipeline that runs backend tests, frontend tests, and blocks on failure
5. The OpenTelemetry + Sentry stack captures a traced API request end-to-end and surfaces it in the observability backend

---

## Dependency Graph & Wave Structure

```
Wave 1 (parallel):
  Plan 01: Backend Dependency Modernization
  Plan 02: CRA-to-Vite + TypeScript Migration

Wave 2 (parallel, depends on Wave 1):
  Plan 03: Database Layer Resolution (SQLAlchemy async engine + Alembic)
  Plan 04: API Foundation + Clerk Auth Backend

Wave 3 (parallel, depends on Wave 2):
  Plan 05: Celery + Redis Worker Infrastructure
  Plan 06: Frontend Auth (Clerk React) + Protected Routes

Wave 4 (parallel, depends on Waves 2-3):
  Plan 07: Observability Stack (OpenTelemetry + Sentry + LLM Cost Tracking)
  Plan 08: CI/CD Pipeline + Remaining Stories (WebSocket, Email, Storage, GDPR, Perf)
```

---

## Plan 01: Backend Dependency Modernization

**Wave:** 1 (no dependencies)
**Stories:** Partial 0-1 (schema exists), research-identified work (dep upgrades, langchain removal, SDK upgrades)
**Estimated effort:** 30-45 min Claude execution

### Objective

Upgrade all backend Python dependencies to target versions, remove deprecated packages (langchain, python-jose, passlib, selenium, black, flake8), add new required packages, and ensure the backend starts cleanly with `uvicorn`.

### Tasks

**Task 1: Update requirements.txt and install** [DONE - 1d3ad66]
- Files: `backend/requirements.txt`
- Action:
  - Replace entire `requirements.txt` with modernized versions per research:
    - `fastapi>=0.115.0,<1.0.0`
    - `uvicorn[standard]>=0.34.0`
    - `pydantic>=2.10.0,<3.0.0`
    - `pydantic-settings>=2.7.0` (NEW -- for config management)
    - `openai>=2.16.0,<3.0.0` (v1->v2 upgrade)
    - `anthropic>=0.77.0,<1.0.0` (major upgrade)
    - `sqlalchemy[asyncio]>=2.0.36`
    - `asyncpg>=0.30.0` (NEW -- async PostgreSQL driver)
    - `alembic>=1.14.0`
    - `celery[redis]>=5.4.0,<6.0.0` (NEW)
    - `redis>=5.2.0` (NEW)
    - `fastapi-clerk-auth>=0.0.9` (NEW)
    - `sentry-sdk[fastapi]>=2.0.0` (NEW)
    - `opentelemetry-api>=1.29.0` (NEW)
    - `opentelemetry-sdk>=1.29.0` (NEW)
    - `opentelemetry-instrumentation-fastapi>=0.50b0` (NEW)
    - `opentelemetry-instrumentation-celery>=0.50b0` (NEW)
    - `resend>=2.0.0` (NEW -- email service, ADR-6 resolved: use Resend)
    - `broadcaster[redis]>=1.0.0` (NEW -- WebSocket pub/sub)
    - Keep: `httpx`, `beautifulsoup4`, `pypdf2`, `python-docx`, `python-dotenv`, `email-validator`, `python-multipart>=0.0.18`, `structlog`, `pytest*`, `faker`
    - Remove: `langchain==0.0.340`, `python-jose`, `passlib`, `selenium`, `black`, `flake8`, `prometheus-client`, `aiohttp`, `lxml`, `openpyxl`, `pandas`
    - Add dev tools: `ruff>=0.9.0`, `mypy>=1.7.0`, `pre-commit>=3.5.0`
  - Run `pip install -r backend/requirements.txt` and verify no conflicts
- Verify: `pip install -r backend/requirements.txt` completes without errors; `python -c "import fastapi; import openai; import celery; import redis; import sqlalchemy; print('OK')"` prints OK
- Done: All target packages installed at correct versions, deprecated packages removed

**Task 2: Fix OpenAI SDK v2 breaking changes in LLM clients** [DONE - 1e05616]
- Files: `backend/app/core/llm_clients.py`, any file importing `openai` or `anthropic`
- Action:
  - Grep codebase for `import openai`, `from openai`, `import anthropic`, `from anthropic`
  - The existing `OpenAIClient` in `llm_clients.py` uses raw httpx (not the SDK), so it is likely unaffected
  - If any code uses the `openai` package directly, update to v2 API patterns (response format changes, `client.chat.completions.create()` instead of old patterns)
  - If the `anthropic` package is used directly anywhere, update to v0.77 patterns
  - Add a thin wrapper comment in `llm_clients.py` noting it uses raw httpx, not the SDK, and suggesting migration to SDK v2 in a future phase
- Verify: `python -c "from app.core.llm_clients import OpenAIClient, AnthropicClient; print('OK')"` (from backend/) works; no import errors
- Done: Backend can import all LLM client code without errors under new SDK versions

**Task 3: Create pydantic-settings config module** [DONE - 3ca2f7e]
- Files: `backend/app/config.py` (NEW)
- Action:
  - Create a `Settings` class using `pydantic_settings.BaseSettings` with fields for:
    - `DATABASE_URL: str` (postgresql+asyncpg://...)
    - `REDIS_URL: str = "redis://localhost:6379/0"`
    - `CLERK_DOMAIN: str`
    - `SENTRY_DSN: str = ""`
    - `APP_ENV: str = "development"`
    - `RESEND_API_KEY: str = ""`
    - `SUPABASE_URL: str`
    - `SUPABASE_KEY: str`
    - `OPENAI_API_KEY: str = ""`
    - `ANTHROPIC_API_KEY: str = ""`
  - Export a `settings = Settings()` singleton
  - Create `backend/.env.example` with all variables documented
- Verify: `python -c "from app.config import Settings; print(Settings.model_fields.keys())"` lists all fields
- Done: Centralized config module exists; `.env.example` documents all required environment variables

### Acceptance Criteria
- `cd backend && python -c "import app.main; print('OK')"` succeeds (backend importable)
- No deprecated packages remain in requirements.txt
- All new target packages are importable

---

## Plan 02: CRA-to-Vite + TypeScript Migration

**Wave:** 1 (no dependencies, parallel with Plan 01)
**Stories:** Research-identified (CRA->Vite, TypeScript adoption)
**Estimated effort:** 45-60 min Claude execution

### Objective

Migrate the frontend from Create React App to Vite, rename JSX files, convert env vars, add TypeScript support, and install the modern frontend stack (TanStack Query, Zustand, Zod). The frontend must start with `npm run dev` and show the existing UI.

### Tasks

**Task 1: Uninstall CRA, install Vite + TypeScript + modern stack** [DONE]
- Files: `frontend/package.json`, `frontend/vite.config.ts` (NEW), `frontend/tsconfig.json` (NEW), `frontend/tsconfig.node.json` (NEW)
- Action:
  - `cd frontend && npm uninstall react-scripts`
  - `npm install vite @vitejs/plugin-react --save-dev`
  - `npm install typescript @types/react @types/react-dom --save-dev`
  - `npm install vitest @testing-library/react @testing-library/jest-dom jsdom --save-dev`
  - `npm install @clerk/clerk-react @tanstack/react-query zustand zod`
  - Create `vite.config.ts`:
    ```typescript
    import { defineConfig } from 'vite';
    import react from '@vitejs/plugin-react';

    export default defineConfig({
      plugins: [react()],
      server: {
        port: 3000,
        proxy: {
          '/api': 'http://localhost:8000',
          '/health': 'http://localhost:8000',
        },
      },
      test: {
        globals: true,
        environment: 'jsdom',
        setupFiles: './src/test-setup.ts',
      },
    });
    ```
  - Create `tsconfig.json` with strict: false initially (incremental adoption), target: ES2020, jsx: react-jsx, paths alias `@/` -> `src/`
  - Update `package.json` scripts:
    ```json
    "scripts": {
      "dev": "vite",
      "build": "tsc && vite build",
      "preview": "vite preview",
      "test": "vitest",
      "lint": "eslint src/"
    }
    ```
  - Remove from `package.json`: `eslintConfig`, `browserslist`, `proxy` keys
- Verify: `cat frontend/package.json | grep vite` shows vite in devDependencies; `cat frontend/vite.config.ts` exists
- Done: Package.json has Vite scripts, CRA references fully removed

**Task 2: Migrate HTML entry point and rename JSX files** [DONE]
- Files: `frontend/index.html` (NEW, moved from public/), `frontend/src/*.jsx` (renamed from .js), `frontend/src/components/*.jsx` (renamed from .js)
- Action:
  - Move `frontend/public/index.html` to `frontend/index.html`
  - Edit `index.html`: remove all `%PUBLIC_URL%` references; add `<script type="module" src="/src/main.jsx"></script>` before `</body>`
  - Rename files containing JSX from `.js` to `.jsx`:
    - `src/index.js` -> `src/main.jsx` (also rename to match Vite convention)
    - `src/App.js` -> `src/App.jsx`
    - `src/components/AuthorStylesManager.js` -> `.jsx`
    - `src/components/ColdEmailGenerator.js` -> `.jsx`
    - `src/components/Dashboard.js` -> `.jsx`
    - `src/components/LandingPage.js` -> `.jsx`
    - `src/components/LinkedInPostGenerator.js` -> `.jsx`
    - `src/components/Settings.js` -> `.jsx`
  - Files without JSX stay as `.js`: `src/services/api.js`, `src/utils/sessionCache.js` (if they exist)
  - Update all import paths in source files to match renamed files (remove `.js` extensions if used, or update to `.jsx`)
  - Replace `process.env.REACT_APP_*` with `import.meta.env.VITE_*` in ALL source files (grep for `process.env.REACT_APP`)
  - Create `frontend/.env.example` with `VITE_API_URL=http://localhost:8000`
  - Create `frontend/src/test-setup.ts` with `import '@testing-library/jest-dom';`
  - Create `frontend/src/vite-env.d.ts` with `/// <reference types="vite/client" />`
- Verify: `cd frontend && npx vite --version` prints version; `npm run dev` starts without crashing (may show blank page if env vars are missing, but no build errors)
- Done: Vite dev server starts on port 3000; no CRA references remain in codebase; JSX files have correct extensions

### Acceptance Criteria
- `cd frontend && npm run dev` starts the Vite dev server on port 3000
- `cd frontend && npm run build` completes without errors
- No `react-scripts`, `REACT_APP_*`, or `%PUBLIC_URL%` references exist in the codebase
- Existing components render (visually unchanged from CRA version)

---

## Plan 03: Database Layer Resolution

**Wave:** 2 (depends on Plan 01 for asyncpg/sqlalchemy versions)
**Stories:** 0-1 (Database Schema Foundation), 0-2 (Row-Level Security -- partial, document-only), research-identified (dual DB resolution)
**Estimated effort:** 45-60 min Claude execution

### Objective

Wire up the SQLAlchemy async engine + session factory that the existing ORM models need. Configure Alembic for async migrations. Stamp existing schema as the baseline migration. Rename `connection.py` to clarify Supabase SDK is storage-only. This resolves ADR-2 (Database Access Pattern).

### Tasks

**Task 1: Create SQLAlchemy async engine and session factory**
- Files: `backend/app/db/engine.py` (NEW), `backend/app/db/session.py` (NEW), `backend/app/db/connection.py` -> rename to `backend/app/db/supabase_client.py`
- Action:
  - Create `backend/app/db/engine.py` with:
    - `create_async_engine` using `settings.DATABASE_URL`
    - `statement_cache_size=0` in connect_args (prevents Supabase asyncpg conflict)
    - `server_settings={"jit": "off"}`
    - `pool_size=5, max_overflow=10`
    - `AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)`
  - Create `backend/app/db/session.py` with `get_db()` async generator (FastAPI dependency):
    ```python
    async def get_db() -> AsyncGenerator[AsyncSession, None]:
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    ```
  - Rename `backend/app/db/connection.py` to `backend/app/db/supabase_client.py`
  - Add docstring to `supabase_client.py`: "Supabase SDK client. Use ONLY for file storage and auth. ALL application data access must use SQLAlchemy (see engine.py)."
  - Update any imports of `connection.py` (grep for `from app.db.connection` or `from .connection`) to point to `supabase_client`
  - Update `backend/app/db/__init__.py` to export `get_db`, `engine`, `AsyncSessionLocal`
  - Verify ORM models in `backend/app/db/models.py` use `DeclarativeBase` or `declarative_base()` -- ensure they are compatible with the engine
- Verify: `python -c "from app.db.engine import engine, AsyncSessionLocal; from app.db.session import get_db; print('OK')"` works
- Done: SQLAlchemy async engine is configured; session dependency is available for FastAPI; Supabase client is clearly scoped to storage/auth only

**Task 2: Configure Alembic for async migrations**
- Files: `backend/alembic.ini` (modify if exists, create if not), `backend/alembic/env.py` (modify for async), `backend/alembic/versions/` (initial migration)
- Action:
  - If `alembic.ini` exists, update `sqlalchemy.url` to use `DATABASE_URL` env var. If not, run `cd backend && alembic init alembic`
  - Modify `backend/alembic/env.py` to:
    - Import `from app.db.engine import engine` and `from app.db.models import Base`
    - Set `target_metadata = Base.metadata`
    - Implement `run_async_migrations()` pattern:
      ```python
      async def run_async_migrations():
          connectable = engine
          async with connectable.connect() as connection:
              await connection.run_sync(do_run_migrations)
      ```
    - Use `asyncio.run(run_async_migrations())` in `run_migrations_online()`
  - Generate initial migration: `cd backend && alembic revision --autogenerate -m "initial schema"`
  - Since tables already exist in Supabase (from `supabase/migrations/00001_initial_schema.sql`), stamp as applied: `alembic stamp head`
  - Document in a comment: "Tables were created via Supabase migration 00001. This Alembic baseline matches that schema. All future changes go through Alembic."
- Verify: `cd backend && alembic heads` shows the initial migration; `alembic current` shows it as applied (if DB is available) OR the files exist correctly
- Done: Alembic is configured for async; initial migration generated and stamped; future schema changes go through Alembic

**Task 3: Write ADR-2 decision document**
- Files: `backend/docs/adr/002-database-access-pattern.md` (NEW)
- Action:
  - Create ADR documenting:
    - Decision: SQLAlchemy for ALL application data access
    - Supabase SDK only for: auth token forwarding, file storage (Supabase Storage), realtime subscriptions
    - Rationale: Prevents dual-persistence drift, enables Alembic migrations, type-safe queries
    - Anti-pattern to avoid: Never use both Supabase SDK and SQLAlchemy to read/write the same table
    - Connection: Use direct connection (port 5432), not PgBouncer, with `statement_cache_size=0`
- Verify: File exists and is well-formed markdown
- Done: ADR-2 is documented and committed

### Acceptance Criteria
- `from app.db.engine import engine, AsyncSessionLocal` works
- `from app.db.session import get_db` works
- Alembic config exists and can show migration heads
- No code imports from `app.db.connection` (all updated to `app.db.supabase_client`)
- ADR-2 documented

---

## Plan 04: API Foundation + Clerk Auth Backend

**Wave:** 2 (depends on Plan 01 for fastapi-clerk-auth package; parallel with Plan 03)
**Stories:** 0-3 (Clerk Authentication -- backend half), 0-4 (API Foundation with Versioning)
**Estimated effort:** 45-60 min Claude execution

### Objective

Restructure the FastAPI app with versioned API routes (`/api/v1/`), health check endpoint, CORS config, Clerk JWT middleware for protected routes, and rate limiting middleware. This is the backend skeleton that all subsequent features build on.

### Tasks

**Task 1: Restructure FastAPI app with versioned routes and health check**
- Files: `backend/app/main.py` (modify), `backend/app/api/__init__.py` (NEW), `backend/app/api/v1/__init__.py` (NEW), `backend/app/api/v1/router.py` (NEW), `backend/app/api/v1/health.py` (NEW)
- Action:
  - Create `backend/app/api/v1/health.py` with:
    - `GET /health` returning `{"status": "healthy", "version": "1.0.0", "environment": settings.APP_ENV}`
    - Include checks for DB connectivity and Redis connectivity (return degraded if either fails)
  - Create `backend/app/api/v1/router.py` that aggregates all v1 routes using `APIRouter(prefix="/api/v1")`
  - Modify `backend/app/main.py` to:
    - Use app factory pattern: `def create_app() -> FastAPI:`
    - Include the v1 router
    - Configure CORS middleware allowing frontend origins (`http://localhost:3000` for dev, configurable via settings)
    - Add global exception handlers for consistent error responses
    - Keep existing routes working during migration (add them under v1 prefix)
  - Create `__init__.py` files for `api/` and `api/v1/`
- Verify: `cd backend && uvicorn app.main:app --port 8000` starts; `curl http://localhost:8000/api/v1/health` returns JSON with status "healthy"
- Done: API serves at `/api/v1/` prefix with health check; CORS allows frontend origin

**Task 2: Add Clerk JWT authentication middleware**
- Files: `backend/app/auth/__init__.py` (NEW), `backend/app/auth/clerk.py` (NEW), `backend/app/api/v1/users.py` (NEW)
- Action:
  - Create `backend/app/auth/clerk.py` with:
    - `ClerkConfig` using `settings.CLERK_DOMAIN` to derive JWKS URL
    - `clerk_auth = ClerkHTTPBearer(clerk_config=clerk_config)` dependency
    - Helper function `get_current_user_id(auth) -> str` that extracts `auth.decoded["sub"]`
    - If `fastapi-clerk-auth` has issues, implement manual fallback: fetch JWKS from Clerk, decode JWT with PyJWT
  - Create `backend/app/api/v1/users.py` with:
    - `GET /api/v1/users/me` (protected) -- returns current user info from JWT claims
    - This is a minimal endpoint to verify auth works end-to-end
  - Wire users router into v1 router
- Verify: `python -c "from app.auth.clerk import clerk_auth; print('OK')"` works; `curl http://localhost:8000/api/v1/users/me` returns 401 (no token) -- confirming auth is active
- Done: Protected endpoints reject unauthenticated requests with 401; authenticated requests can extract user_id from JWT

**Task 3: Add rate limiting middleware**
- Files: `backend/app/middleware/__init__.py` (NEW), `backend/app/middleware/rate_limit.py` (NEW)
- Action:
  - Create basic rate limiting middleware using Redis (if available) or in-memory fallback:
    - Free tier: 100 requests/hour
    - Pro tier: 1000 requests/hour
    - Rate exceeded: 429 with `Retry-After` header
  - Tier is extracted from JWT claims or defaults to Free for unauthenticated
  - Wire into FastAPI app in `main.py`
  - NOTE: Full tier-based limiting requires user tier in DB, which may not exist yet. Implement with sensible defaults (all users get Pro-tier limits initially) and a TODO for tier lookup once user management is in place.
- Verify: Middleware file exists and imports cleanly
- Done: Rate limiting middleware is in place (may use in-memory for now if Redis is not yet running)

### Acceptance Criteria
- `GET /api/v1/health` returns 200 with status JSON
- `GET /api/v1/users/me` returns 401 without a valid Clerk JWT
- All endpoints are prefixed with `/api/v1/`
- CORS allows `http://localhost:3000`
- Rate limiting middleware exists and is wired in

---

## Plan 05: Celery + Redis Worker Infrastructure

**Wave:** 3 (depends on Plan 01 for celery/redis packages, Plan 03 for SQLAlchemy session)
**Stories:** 0-5 (Redis Cache and Queue Setup), 0-6 (Celery Worker Infrastructure)
**Estimated effort:** 30-45 min Claude execution

### Objective

Configure Celery with Redis as broker/backend, create the worker app with reliability settings (retry, timeout, heartbeat), define queue routing for future agent types, and create an example task that writes to PostgreSQL via SQLAlchemy to prove the full pipeline works.

### Tasks

**Task 1: Create Celery app and Redis configuration**
- Files: `backend/app/worker/__init__.py` (NEW), `backend/app/worker/celery_app.py` (NEW)
- Action:
  - Create `backend/app/worker/celery_app.py` with:
    - Celery app named "jobpilot"
    - Broker and backend from `settings.REDIS_URL`
    - Serialization: JSON only
    - Reliability: `task_acks_late=True`, `worker_prefetch_multiplier=1`, `task_reject_on_worker_lost=True`
    - Timeouts: soft=240s, hard=300s
    - Result expiry: 3600s
    - Heartbeat: `worker_send_task_events=True`, `task_send_sent_event=True`
    - Queue routing:
      ```python
      task_routes = {
          "app.worker.tasks.agent_*": {"queue": "agents"},
          "app.worker.tasks.briefing_*": {"queue": "briefings"},
          "app.worker.tasks.scrape_*": {"queue": "scraping"},
          "app.worker.tasks.*": {"queue": "default"},
      }
      ```
    - Retry defaults: 30s delay, 3 max retries
  - Keep `celery_app.py` minimal -- NO imports from app.db or app.main at module level (prevents event loop errors)
- Verify: `python -c "from app.worker.celery_app import celery_app; print(celery_app.main)"` prints "jobpilot"
- Done: Celery app is configured with Redis broker, reliability settings, and queue routing

**Task 2: Create example task and health integration**
- Files: `backend/app/worker/tasks.py` (NEW), `backend/app/api/v1/health.py` (modify to add Redis check)
- Action:
  - Create `backend/app/worker/tasks.py` with:
    - `example_task(user_id: str, task_data: dict)` -- a proof-of-concept task that:
      1. Lazily imports `AsyncSessionLocal` from `app.db.engine` (NOT at module level)
      2. Uses `asyncio.run()` to execute async DB operations
      3. Creates or updates a simple record in the database
      4. Returns `{"status": "completed", "user_id": user_id}`
    - `health_check_task()` -- returns timestamp, used by health endpoint to verify worker is alive
  - Update health endpoint to include Redis ping check:
    - Try `redis.asyncio.from_url(settings.REDIS_URL).ping()`
    - Report Redis status in health response
  - Add pub/sub channel documentation in a comment for future agent control:
    - `agent:pause:{user_id}`, `agent:resume:{user_id}`, `agent:status:{user_id}`
- Verify:
  - `python -c "from app.worker.tasks import example_task; print('OK')"` works
  - With Redis running: `celery -A app.worker.celery_app worker --loglevel=info` starts without errors
  - Enqueue test: `python -c "from app.worker.tasks import example_task; r = example_task.delay('test-user', {}); print(r.id)"` returns a task ID
- Done: Celery worker starts, picks up tasks from Redis, and can execute async DB operations via SQLAlchemy

### Acceptance Criteria
- Celery worker starts with `celery -A app.worker.celery_app worker --loglevel=info`
- A task enqueued via `.delay()` is picked up and executed
- Health endpoint reports Redis connectivity status
- Worker uses lazy imports (no event loop errors on startup)

---

## Plan 06: Frontend Auth (Clerk React) + Protected Routes

**Wave:** 3 (depends on Plan 02 for Vite frontend, Plan 04 for Clerk backend)
**Stories:** 0-3 (Clerk Authentication -- frontend half)
**Estimated effort:** 30-45 min Claude execution

### Objective

Integrate Clerk React SDK into the Vite frontend. Wrap the app in ClerkProvider, create sign-in/sign-up pages, protect the dashboard route, and update the API service to attach Clerk JWT tokens to all requests.

### Tasks

**Task 1: Set up Clerk provider and auth pages**
- Files: `frontend/src/providers/ClerkProvider.tsx` (NEW), `frontend/src/providers/QueryProvider.tsx` (NEW), `frontend/src/main.jsx` (modify), `frontend/src/App.jsx` -> `frontend/src/App.tsx` (convert)
- Action:
  - Create `frontend/src/providers/ClerkProvider.tsx`:
    ```tsx
    import { ClerkProvider } from '@clerk/clerk-react';
    const CLERK_PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
    export function AuthProvider({ children }: { children: React.ReactNode }) {
      return <ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY}>{children}</ClerkProvider>;
    }
    ```
  - Create `frontend/src/providers/QueryProvider.tsx` wrapping `QueryClientProvider` from TanStack Query
  - Convert `App.jsx` to `App.tsx` with:
    - Routes wrapped in `AuthProvider` and `QueryProvider`
    - Public routes: `/sign-in`, `/sign-up`, `/` (landing)
    - Protected routes: `/dashboard` (requires auth)
    - Use Clerk's `<SignedIn>`, `<SignedOut>`, `<RedirectToSignIn>` components
  - Update `main.jsx` to import from the new App location
  - Create `frontend/src/pages/SignIn.tsx` (NEW) using `<SignIn />` from Clerk
  - Create `frontend/src/pages/SignUp.tsx` (NEW) using `<SignUp />` from Clerk
  - Create `frontend/src/pages/Dashboard.tsx` (NEW) -- minimal protected page showing user info from `useUser()`
  - Update `.env.example` with `VITE_CLERK_PUBLISHABLE_KEY=pk_test_...`
- Verify: `npm run dev` starts; visiting `/sign-in` shows Clerk sign-in UI (if publishable key is set); visiting `/dashboard` without auth redirects to sign-in
- Done: Clerk auth wraps the app; protected routes require authentication; sign-in and dashboard pages exist

**Task 2: Update API service with Clerk token injection**
- Files: `frontend/src/services/api.ts` (convert from .js and update)
- Action:
  - Convert `frontend/src/services/api.js` to `api.ts`
  - Update to use `import.meta.env.VITE_API_URL` instead of `process.env.REACT_APP_API_URL`
  - Create `useApiClient()` hook that:
    - Uses `useAuth()` from Clerk to get `getToken()`
    - Adds Axios request interceptor to attach `Authorization: Bearer <token>` header
    - Returns configured axios instance
  - Export both the raw `api` instance (for non-authed calls) and `useApiClient` hook
- Verify: `api.ts` compiles without TypeScript errors; import paths are correct
- Done: All API calls include Clerk JWT token; API service uses Vite env vars

### Acceptance Criteria
- `npm run dev` starts the app with Clerk integration
- Visiting `/sign-in` shows Clerk sign-in form (with valid publishable key)
- Visiting `/dashboard` without auth redirects to sign-in
- API calls include `Authorization: Bearer <token>` header when user is authenticated
- A user can sign up via Clerk (LinkedIn OAuth configured in Clerk dashboard), log in, and see the protected dashboard page

---

## Plan 07: Observability Stack

**Wave:** 4 (depends on Plan 04 for FastAPI app, Plan 05 for Celery)
**Stories:** 0-7 (OpenTelemetry Tracing), 0-8 (LLM Cost Tracking), 0-9 (Error Tracking / Sentry)
**Estimated effort:** 30-45 min Claude execution

### Objective

Set up OpenTelemetry distributed tracing, Sentry error tracking, and LLM cost tracking middleware. A traced API request should flow from FastAPI through to Celery tasks and be visible in the observability backend.

### Tasks

**Task 1: OpenTelemetry + Sentry initialization**
- Files: `backend/app/observability/__init__.py` (NEW), `backend/app/observability/tracing.py` (NEW), `backend/app/observability/sentry.py` (NEW), `backend/app/main.py` (modify to call setup)
- Action:
  - Create `backend/app/observability/tracing.py` with `setup_observability(app)` function:
    - Initialize Sentry with `sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1, environment=settings.APP_ENV)`
    - Include `StarletteIntegration()` and `FastApiIntegration()`
    - Set up OpenTelemetry `TracerProvider`
    - In development: use `ConsoleSpanExporter` (traces printed to stdout)
    - In production: placeholder for OTLP exporter (Grafana Cloud / Honeycomb)
    - Auto-instrument FastAPI: `FastAPIInstrumentor.instrument_app(app)`
    - Auto-instrument Celery: `CeleryInstrumentor().instrument()`
  - Call `setup_observability(app)` in `create_app()` in main.py
  - Traces should include: user_id (from JWT), request path, status code, duration
- Verify: Start backend, make a request to `/api/v1/health`, see trace span logged to console (development mode)
- Done: Every API request generates a trace span; Celery tasks create child spans; Sentry captures unhandled exceptions

**Task 2: LLM Cost Tracking middleware**
- Files: `backend/app/observability/cost_tracker.py` (NEW)
- Action:
  - Create `track_llm_cost(user_id, model, input_tokens, output_tokens)` async function:
    - Calculate cost based on model pricing table (GPT-4-turbo, GPT-3.5-turbo, Claude 3 Opus, etc.)
    - Store monthly aggregation in Redis key `llm_cost:{user_id}:{YYYY-MM}`
    - Set 35-day TTL on keys
    - Publish alert to `alerts:cost:{user_id}` when user exceeds 80% of $6/month budget
  - Create `GET /api/v1/admin/llm-costs` endpoint returning:
    - Total cost today/month
    - Per-user breakdown (if admin)
    - Projected month-end cost
  - Wire into v1 router
- Verify: `python -c "from app.observability.cost_tracker import track_llm_cost; print('OK')"` works
- Done: LLM cost tracking function exists and is callable; admin endpoint returns cost data from Redis

### Acceptance Criteria
- API requests generate OpenTelemetry trace spans (visible in console output)
- Sentry is initialized (captures errors when DSN is configured)
- LLM cost tracking function can record costs to Redis
- Celery tasks are auto-instrumented with trace spans
- Admin cost endpoint exists at `/api/v1/admin/llm-costs`

---

## Plan 08: CI/CD Pipeline + Remaining Infrastructure Stories

**Wave:** 4 (depends on Plans 01-06 for testable code; parallel with Plan 07)
**Stories:** 0-10 (WebSocket), 0-11 (Email Service), 0-12 (CI/CD), 0-13 (Supabase Storage), 0-14 (Performance Baseline -- partial), 0-15 (GDPR Endpoints)
**Estimated effort:** 45-60 min Claude execution

### Objective

Create the GitHub Actions CI pipeline, WebSocket infrastructure, email service config, Supabase storage setup, GDPR data portability endpoints, and performance baseline documentation. This closes out all remaining Epic 0 stories.

### Tasks

**Task 1: GitHub Actions CI pipeline**
- Files: `.github/workflows/ci.yml` (NEW)
- Action:
  - Create CI workflow triggered on push to main and PRs to main
  - Two jobs (parallel):
    - **backend-test:**
      - Service containers: Redis 7 (port 6379), PostgreSQL 15 (port 5432, db: jobpilot_test)
      - Python 3.11, pip cache
      - `pip install -r backend/requirements.txt`
      - `ruff check backend/` (linting)
      - `cd backend && pytest tests/ -v --cov=app --cov-report=xml` (with env vars for DATABASE_URL and REDIS_URL pointing to service containers)
      - Note: Coverage thresholds start at 0% and increase as tests are added. Do NOT set `--cov-fail-under` yet.
    - **frontend-test:**
      - Node 20, npm cache (cache-dependency-path: frontend/package-lock.json)
      - `cd frontend && npm ci`
      - `cd frontend && npm run lint` (if eslint is configured)
      - `cd frontend && npx vitest --run` (run tests once, not in watch mode)
      - `cd frontend && npm run build` (verify build succeeds)
  - Add initial test files so CI has something to run:
    - `backend/tests/__init__.py`, `backend/tests/conftest.py` (with async fixtures)
    - `backend/tests/unit/__init__.py`
    - `backend/tests/unit/test_health.py` -- test health endpoint returns 200
    - `frontend/src/App.test.tsx` -- basic smoke test that App renders
- Verify: `.github/workflows/ci.yml` exists and is valid YAML; test files exist
- Done: Pushing to main triggers CI; backend linting + tests + frontend build all run; failures block merge

**Task 2: WebSocket infrastructure + Email service + Storage config**
- Files: `backend/app/api/v1/ws.py` (NEW), `backend/app/services/email_service.py` (modify or create), `backend/app/services/storage_service.py` (NEW)
- Action:
  - Create `backend/app/api/v1/ws.py` with WebSocket endpoint:
    - `WS /api/v1/ws/agents/{user_id}` -- accepts connection, subscribes to Redis pub/sub channel `agent:status:{user_id}`
    - Forwards messages from Redis to WebSocket client
    - JWT authentication via query parameter or first message
    - Graceful disconnect handling
    - Add `publish_agent_event(user_id, event)` helper for Celery workers to use
  - Create or update `backend/app/services/email_service.py`:
    - Use Resend SDK (`resend.Emails.send()`)
    - `send_email(to, subject, html_body)` function
    - Template support for briefing emails
    - Configure from `settings.RESEND_API_KEY`
    - ADR-6 resolved: Resend chosen over SendGrid (better DX, free tier sufficient)
  - Create `backend/app/services/storage_service.py`:
    - Use Supabase Storage SDK (from `supabase_client.py`)
    - `upload_file(user_id, file, bucket="resumes")` -- stores file, returns storage path
    - `get_signed_url(path, expires_in=900)` -- 15-minute signed URL
    - File size limit: 10MB
    - Accepted types: PDF, DOCX
  - Wire WebSocket route into v1 router
- Verify: All files import cleanly; WebSocket route is registered
- Done: WebSocket endpoint exists for real-time agent updates; email service is configured with Resend; storage service wraps Supabase Storage

**Task 3: GDPR endpoints + performance baseline docs**
- Files: `backend/app/api/v1/users.py` (modify -- add export/delete), `backend/docs/performance-baseline.md` (NEW)
- Action:
  - Add to `backend/app/api/v1/users.py`:
    - `GET /api/v1/users/me/export` (protected):
      - Queries all user data (profile, applications, documents, agent_actions) via SQLAlchemy
      - Returns JSON export OR enqueues async Celery task for large exports
      - Includes download links for stored documents
    - `DELETE /api/v1/users/me` (protected):
      - Schedules account for deletion (sets `deleted_at` + 30 days)
      - Returns confirmation
      - NOTE: Actual deletion job is a future Celery task; for now just marks the record
  - Create `backend/docs/performance-baseline.md` documenting:
    - Target metrics: page load <2s, API p95 <500ms, agent response <30s
    - Baseline will be established after Phase 1 using k6 (manual, not CI-integrated yet)
    - Regression threshold: >20% degradation fails CI (future -- Phase 9)
    - Placeholder for actual baseline numbers after deployment
- Verify: `curl http://localhost:8000/api/v1/users/me/export` returns 401 (auth required -- confirms endpoint exists)
- Done: GDPR export and deletion endpoints exist; performance baseline targets documented

### Acceptance Criteria
- `.github/workflows/ci.yml` exists with backend-test and frontend-test jobs
- At least one backend test and one frontend test exist and pass
- WebSocket endpoint is registered at `/api/v1/ws/agents/{user_id}`
- Email service wraps Resend SDK
- Storage service wraps Supabase Storage with signed URLs
- GDPR export and delete endpoints exist under `/api/v1/users/me/`
- Performance baseline targets are documented

---

## Execution Summary

| Plan | Wave | Stories Covered | Key Deliverable | Parallel With |
|------|------|-----------------|-----------------|---------------|
| 01 | 1 | Research (deps) | Modern Python deps, config module | Plan 02 |
| 02 | 1 | Research (CRA->Vite) | Vite + TypeScript frontend | Plan 01 |
| 03 | 2 | 0-1, 0-2, Research (dual DB) | SQLAlchemy async engine + Alembic | Plan 04 |
| 04 | 2 | 0-3 (backend), 0-4 | Versioned API + Clerk auth | Plan 03 |
| 05 | 3 | 0-5, 0-6 | Celery + Redis workers | Plan 06 |
| 06 | 3 | 0-3 (frontend) | Clerk React + protected routes | Plan 05 |
| 07 | 4 | 0-7, 0-8, 0-9 | OTel + Sentry + cost tracking | Plan 08 |
| 08 | 4 | 0-10, 0-11, 0-12, 0-13, 0-14, 0-15 | CI/CD + remaining infra | Plan 07 |

**Total: 8 plans across 4 waves. Sequential depth: 4 steps. Max parallelism: 2 plans per wave.**

## User Setup Required (External Services)

These require human action in external dashboards before the code will fully work:

| Service | Action Required | When Needed |
|---------|----------------|-------------|
| **Clerk** | Create Clerk app at clerk.com; enable LinkedIn OAuth provider; copy Publishable Key and set `VITE_CLERK_PUBLISHABLE_KEY` and `CLERK_DOMAIN` env vars | Plan 04 (backend) and Plan 06 (frontend) |
| **Supabase** | Create project (if not done); get direct connection string (port 5432); set `DATABASE_URL=postgresql+asyncpg://...` | Plan 03 |
| **Redis** | Provision Redis instance (Railway, Upstash, or local `docker run redis:7`); set `REDIS_URL` | Plan 05 |
| **Sentry** | Create Sentry project; get DSN; set `SENTRY_DSN` env var | Plan 07 |
| **Resend** | Create Resend account; get API key; set `RESEND_API_KEY`; verify sending domain | Plan 08 |
| **GitHub** | Ensure repo has Actions enabled; add secrets for CI if needed | Plan 08 |

## Post-Phase Verification Checklist

After all 8 plans execute, verify these success criteria:

- [ ] `cd frontend && npm run dev` starts Vite dev server on port 3000
- [ ] `cd backend && uvicorn app.main:app` starts FastAPI on port 8000
- [ ] `curl http://localhost:8000/api/v1/health` returns 200 with healthy status
- [ ] Sign up via Clerk (LinkedIn OAuth) and see protected dashboard page
- [ ] `celery -A app.worker.celery_app worker --loglevel=info` starts worker
- [ ] Enqueue a task and see it complete with DB write
- [ ] API request generates OTel trace span in console output
- [ ] Pushing to main triggers GitHub Actions CI
- [ ] CI runs backend tests + frontend build and blocks on failure
