# Phase 1: Foundation Modernization - Research

**Researched:** 2026-01-30
**Domain:** Build tooling migration, authentication, background jobs, observability, CI/CD, database architecture resolution
**Confidence:** HIGH (most findings verified via official docs and codebase inspection)

## Summary

Phase 1 transforms a cold-email-generator codebase into a modern, buildable foundation for the JobPilot multi-agent platform. The existing codebase has a FastAPI 0.104.1 backend with raw httpx-based LLM clients (no SDK usage), a CRA-based React frontend (deprecated), SQLAlchemy ORM models with NO engine configured, a Supabase REST client as the only DB connection, and zero auth/background-jobs/observability infrastructure.

The work breaks into six major streams: (1) CRA-to-Vite + TypeScript migration, (2) backend dependency modernization (FastAPI, OpenAI SDK v1->v2, remove langchain), (3) Clerk authentication integration, (4) Celery + Redis task queue, (5) database abstraction resolution (SQLAlchemy as primary, Supabase SDK for auth/storage only), and (6) observability + CI/CD setup. Each stream is well-documented with established migration paths.

**Primary recommendation:** Execute dependency upgrades and CRA-to-Vite migration first (they unblock everything), then layer in auth, task queue, and observability in parallel. The dual-DB resolution is architecturally critical and must happen early -- the current codebase has SQLAlchemy models defined but NO engine/session configuration, meaning SQLAlchemy is completely non-functional today.

---

## Standard Stack

### Core (What to Install/Upgrade)

| Library | Target Version | Purpose | Current State | Why Standard |
|---------|---------------|---------|---------------|--------------|
| `fastapi` | >=0.115.0,<1.0.0 | REST API framework | 0.104.1 installed | Latest stable, Python 3.9+ only |
| `uvicorn[standard]` | >=0.34.0 | ASGI server | 0.24.0 installed | Includes uvloop, httptools |
| `pydantic` | >=2.10.0,<3.0.0 | Data validation | 2.5.0 installed | Compatible minor upgrade |
| `openai` | >=2.16.0,<3.0.0 | OpenAI API client | 1.3.0 installed (**v1**) | **Major version jump required** |
| `anthropic` | >=0.77.0,<1.0.0 | Anthropic API client | 0.7.0 installed | Massive feature gap |
| `sqlalchemy[asyncio]` | >=2.0.36 | ORM + async engine | 2.0.23 (models only, no engine) | Need async session factory |
| `asyncpg` | >=0.30.0 | PostgreSQL async driver | Not installed | Required for SQLAlchemy async |
| `alembic` | >=1.14.0 | Database migrations | 1.12.1 installed | Upgrade for compatibility |
| `celery[redis]` | >=5.4.0,<6.0.0 | Distributed task queue | **Not installed** | Battle-tested, Python task queue standard |
| `redis` | >=5.2.0 | Cache + message broker | **Not installed** | Required for Celery broker + cache |
| `fastapi-clerk-auth` | >=0.0.9 | Clerk JWT validation | **Not installed** | Lightweight Clerk JWKS validation |
| `@clerk/clerk-react` | ^5.0.0 | Frontend auth SDK | **Not installed** | Official Clerk React integration |
| `sentry-sdk[fastapi]` | >=2.0.0 | Error tracking | **Not installed** | Industry standard, FastAPI auto-integration |
| `opentelemetry-api` | >=1.29.0 | Tracing API | **Not installed** | Industry standard distributed tracing |
| `opentelemetry-sdk` | >=1.29.0 | Tracing SDK | **Not installed** | Required implementation |
| `opentelemetry-instrumentation-fastapi` | >=0.50b0 | Auto-instrument FastAPI | **Not installed** | Auto-traces all HTTP requests |
| `opentelemetry-instrumentation-celery` | >=0.50b0 | Auto-instrument Celery | **Not installed** | Auto-traces background tasks |
| `vite` | ^6.0.0 | Frontend build tool | **Not installed** (using CRA) | Replaces deprecated CRA |
| `@vitejs/plugin-react` | ^4.3.0 | React plugin for Vite | **Not installed** | Required for JSX/TSX |
| `typescript` | ^5.7.0 | Type system | **Not installed** | Architecture requires strict TS |
| `vitest` | ^3.0.0 | Test runner | **Not installed** (using Jest via CRA) | Vite-native test runner, Jest-compatible API |

### To Remove

| Library | Version | Why Remove |
|---------|---------|-----------|
| `langchain` | 0.0.340 | Pre-1.0, deprecated, not needed -- agents are Phase 3 |
| `react-scripts` | 5.0.1 | CRA is deprecated, no security patches since Feb 2025 |
| `python-jose` | 3.3.0 | Replaced by Clerk JWT validation |
| `passlib` | 1.7.4 | Replaced by Clerk (no password auth) |
| `selenium` | 4.15.2 | Not needed for Phase 1; heavy dependency |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `resend` | >=2.0.0 | Transactional email | Story 0-11: Email service config |
| `python-multipart` | >=0.0.18 | File upload handling | Already needed, upgrade |
| `ruff` | >=0.9.0 | Linter + formatter | Replaces black + flake8 (one tool) |
| `@tanstack/react-query` | ^5.90.0 | Server state management | Install during frontend migration |
| `zustand` | ^5.0.0 | Client state management | Install during frontend migration |
| `zod` | ^3.24.0 | Runtime validation | Install during frontend migration |
| `broadcaster[redis]` | >=1.0.0 | WebSocket + Redis pub/sub | Story 0-10: WebSocket infrastructure |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Celery + Redis | Dramatiq | Simpler API, but smaller ecosystem; Celery is safer bet for complex agent workflows |
| `fastapi-clerk-auth` | Manual JWT with PyJWT | More control, but unnecessary; Clerk JWKS validation is sufficient |
| Resend | SendGrid | SendGrid is established but more expensive and declining DX; Resend free tier is 3K emails/mo |
| Vite | Turbopack (Next.js) | Would require rewriting to Next.js; Vite keeps React SPA architecture |
| `broadcaster` | `fastapi-websocket-pubsub` | More features but heavier; broadcaster is simpler for status updates |
| Sentry | Self-hosted Grafana | Sentry is zero-config for errors; Grafana requires more setup |

**Installation (backend):**
```bash
pip install "fastapi>=0.115.0" "uvicorn[standard]>=0.34.0" "pydantic>=2.10.0" \
  "openai>=2.16.0" "anthropic>=0.77.0" \
  "sqlalchemy[asyncio]>=2.0.36" "asyncpg>=0.30.0" "alembic>=1.14.0" \
  "celery[redis]>=5.4.0" "redis>=5.2.0" \
  "fastapi-clerk-auth>=0.0.9" \
  "sentry-sdk[fastapi]>=2.0.0" \
  "opentelemetry-api>=1.29.0" "opentelemetry-sdk>=1.29.0" \
  "opentelemetry-instrumentation-fastapi>=0.50b0" \
  "opentelemetry-instrumentation-celery>=0.50b0" \
  "broadcaster[redis]>=1.0.0" \
  "resend>=2.0.0" \
  "ruff>=0.9.0"
```

**Installation (frontend):**
```bash
npm uninstall react-scripts
npm install vite @vitejs/plugin-react --save-dev
npm install typescript @types/react @types/react-dom --save-dev
npm install vitest @testing-library/react @testing-library/jest-dom --save-dev
npm install @clerk/clerk-react @tanstack/react-query zustand zod
```

---

## Architecture Patterns

### Recommended Project Structure (Phase 1 Target)

```
backend/
  app/
    __init__.py
    main.py                    # FastAPI app factory + middleware
    config.py                  # Settings via pydantic-settings (NEW)
    api/
      __init__.py
      v1/
        __init__.py
        router.py              # Aggregate all v1 routes
        health.py              # GET /api/v1/health
        users.py               # User endpoints (GDPR export/delete)
        ws.py                  # WebSocket endpoints
    auth/
      __init__.py
      clerk.py                 # Clerk middleware + dependencies (NEW)
    db/
      __init__.py
      engine.py                # SQLAlchemy async engine + session factory (NEW)
      models.py                # ORM models (EXISTS, needs engine wiring)
      connection.py            # Supabase client (EXISTS, keep for storage only)
    core/
      llm_clients.py           # EXISTS - extend with cost tracking
      llm_config.py            # EXISTS
      web_scraper.py           # EXISTS
      error_handlers.py        # EXISTS
    worker/
      __init__.py
      celery_app.py            # Celery app configuration (NEW)
      tasks.py                 # Task definitions (NEW)
    observability/
      __init__.py
      tracing.py               # OpenTelemetry setup (NEW)
      sentry.py                # Sentry initialization (NEW)
      cost_tracker.py          # LLM cost tracking middleware (NEW)
    services/
      email_service.py         # EXISTS (Phase 1: keep functional)
      ...
  alembic/
    env.py                     # Alembic config (needs async engine wiring)
    versions/
  tests/
    conftest.py
    unit/
    integration/

frontend/
  index.html                   # MOVED from public/ to root
  vite.config.ts               # NEW - replaces CRA webpack config
  tsconfig.json                # NEW - TypeScript config
  src/
    main.tsx                   # NEW entry point (was index.js)
    App.tsx                    # Converted from .js
    providers/
      ClerkProvider.tsx        # NEW - Clerk auth wrapper
      QueryProvider.tsx        # NEW - TanStack Query provider
    services/
      api.ts                   # Converted from .js, add Clerk token
    components/
      ...                      # Incrementally convert .js -> .tsx
```

### Pattern 1: SQLAlchemy Async Engine Setup

**What:** Create the async engine and session factory that the existing ORM models need.
**When to use:** Every database operation in the application.
**Why critical:** The codebase has ORM models defined (`backend/app/db/models.py`) but NO engine. The only DB connection is the Supabase REST client (`backend/app/db/connection.py`). All application data access must go through SQLAlchemy.

```python
# backend/app/db/engine.py (NEW FILE)
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
import os

DATABASE_URL = os.getenv("DATABASE_URL")  # postgresql+asyncpg://...

# Use Supabase direct connection (port 5432), NOT pooler
# Add statement_cache_size=0 to prevent DuplicatePreparedStatementError
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    connect_args={
        "server_settings": {"jit": "off"},
        "statement_cache_size": 0,  # Prevents asyncpg + Supabase conflict
    },
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncSession:
    """FastAPI dependency for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Confidence:** HIGH -- standard SQLAlchemy async pattern; Supabase `statement_cache_size=0` fix is well-documented.

### Pattern 2: Clerk Auth Middleware for FastAPI

**What:** Protect FastAPI routes using Clerk JWT validation.
**When to use:** All authenticated endpoints.

```python
# backend/app/auth/clerk.py (NEW FILE)
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer
from fastapi import Depends
import os

clerk_config = ClerkConfig(
    jwks_url=f"https://{os.getenv('CLERK_DOMAIN')}/.well-known/jwks.json"
)

clerk_auth = ClerkHTTPBearer(clerk_config=clerk_config)

# Use as FastAPI dependency:
# @router.get("/api/v1/users/me")
# async def get_me(auth: HTTPAuthorizationCredentials = Depends(clerk_auth)):
#     user_id = auth.decoded["sub"]  # Clerk user ID
#     ...
```

**Confidence:** MEDIUM-HIGH -- `fastapi-clerk-auth` v0.0.9 is lightweight (1 contributor, 30 stars), but it only does JWT/JWKS validation which is straightforward. Fallback: manual JWT decode with PyJWT if the library has issues.

### Pattern 3: Celery App Configuration

**What:** Configure Celery with Redis broker, task queues, and reliability settings.
**When to use:** All background task processing.

```python
# backend/app/worker/celery_app.py (NEW FILE)
from celery import Celery
import os

celery_app = Celery(
    "jobpilot",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Reliability
    task_acks_late=True,              # Ack after completion, not receipt
    worker_prefetch_multiplier=1,      # One task at a time per worker
    task_reject_on_worker_lost=True,   # Requeue if worker dies

    # Timeouts
    task_soft_time_limit=240,          # 4 min soft limit (raises SoftTimeLimitExceeded)
    task_time_limit=300,               # 5 min hard kill

    # Result expiry
    result_expires=3600,               # 1 hour

    # Heartbeat for zombie detection
    worker_send_task_events=True,
    task_send_sent_event=True,

    # Queue routing
    task_routes={
        "app.worker.tasks.agent_*": {"queue": "agents"},
        "app.worker.tasks.briefing_*": {"queue": "briefings"},
        "app.worker.tasks.scrape_*": {"queue": "scraping"},
        "app.worker.tasks.*": {"queue": "default"},
    },

    # Retry
    task_default_retry_delay=30,
    task_max_retries=3,
)
```

**Confidence:** HIGH -- standard Celery configuration pattern for FastAPI.

### Pattern 4: OpenTelemetry + Sentry Combined Setup

**What:** Distributed tracing via OpenTelemetry with Sentry as error tracker.
**When to use:** Application initialization.

```python
# backend/app/observability/tracing.py (NEW FILE)
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
import os

def setup_observability(app):
    """Initialize OpenTelemetry tracing and Sentry error tracking."""

    # Sentry -- auto-detects FastAPI
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        traces_sample_rate=0.1,  # 10% of requests traced in production
        profiles_sample_rate=0.1,
        environment=os.getenv("APP_ENV", "development"),
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
        ],
    )

    # OpenTelemetry
    provider = TracerProvider()

    if os.getenv("APP_ENV") == "development":
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    else:
        # In production: add OTLP exporter to Grafana Cloud / Honeycomb
        # from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        # provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        pass

    trace.set_tracer_provider(provider)

    # Auto-instrument
    FastAPIInstrumentor.instrument_app(app)
    CeleryInstrumentor().instrument()
```

**Confidence:** HIGH -- Sentry auto-detects FastAPI (no manual integration needed beyond `sentry_sdk.init`). OpenTelemetry FastAPI instrumentation is stable.

### Pattern 5: WebSocket with Redis Pub/Sub

**What:** Minimal WebSocket endpoint for real-time agent status updates.
**When to use:** Story 0-10 (WebSocket Infrastructure).

```python
# backend/app/api/v1/ws.py (NEW FILE)
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi_clerk_auth import ClerkHTTPBearer
import redis.asyncio as aioredis
import json, os

router = APIRouter()

@router.websocket("/api/v1/ws/agents/{user_id}")
async def agent_websocket(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time agent activity updates."""
    # TODO: Validate JWT from query param or first message
    await websocket.accept()

    redis_client = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"agent:status:{user_id}")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await websocket.send_json(data)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(f"agent:status:{user_id}")
        await redis_client.close()


# Publishing side (called from Celery workers):
async def publish_agent_event(user_id: str, event: dict):
    """Publish agent event to user's WebSocket channel."""
    redis_client = aioredis.from_url(os.getenv("REDIS_URL"))
    await redis_client.publish(f"agent:status:{user_id}", json.dumps(event))
    await redis_client.close()
```

**Confidence:** MEDIUM-HIGH -- standard `redis.asyncio` pub/sub pattern. For production scaling across multiple Uvicorn workers, consider upgrading to the `broadcaster[redis]` library which handles cross-instance fan-out automatically.

### Anti-Patterns to Avoid

- **Dual DB access for same data:** NEVER use both Supabase SDK and SQLAlchemy to read/write the same table. SQLAlchemy for ALL app data; Supabase SDK for auth/storage/realtime ONLY.
- **Synchronous Celery tasks calling async code:** Celery tasks are sync by default. Use `asyncio.run()` inside tasks or use `celery-pool-asyncio` for async task support.
- **Hardcoding Clerk JWKS URL:** Always derive from `CLERK_DOMAIN` environment variable, not hardcoded URL.
- **Using Supabase pooler (port 6543) with asyncpg:** Use direct connection (port 5432) to avoid `DuplicatePreparedStatementError`. Add `statement_cache_size=0` as safety net.
- **Mixing CRA and Vite config:** Remove ALL CRA artifacts (react-scripts, CRA-specific env vars, public/index.html) before running Vite.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT validation | Manual decode + JWKS fetch | `fastapi-clerk-auth` | JWKS key rotation, caching, clock drift handling |
| WebSocket pub/sub fan-out | Custom connection registry | `broadcaster[redis]` or `redis.asyncio` pubsub | Cross-instance message delivery across Uvicorn workers |
| Distributed tracing | Custom logging middleware | OpenTelemetry auto-instrumentation | Automatic span creation for FastAPI, Celery, httpx, SQLAlchemy |
| Error tracking | Custom exception handlers | Sentry SDK (auto-detects FastAPI) | Stack traces, grouping, alerts, source maps |
| Task queue | `asyncio.create_task()` or `BackgroundTasks` | Celery + Redis | Persistence, retry, monitoring, multi-worker scaling |
| Database migrations | Raw SQL scripts | Alembic + SQLAlchemy | Versioned, reversible, auto-generated from ORM changes |
| Frontend build | Webpack config from scratch | Vite + `@vitejs/plugin-react` | Near-instant HMR, optimized builds, zero-config for React |
| Form state | Manual React useState | `react-hook-form` (already installed) | Validation, performance, uncontrolled components |

**Key insight:** Phase 1 is infrastructure -- every component has a well-maintained library. Hand-rolling any of these would waste days on solved problems and produce worse results.

---

## Common Pitfalls

### Pitfall 1: OpenAI SDK v1 -> v2 Migration Breaks LLM Client

**What goes wrong:** The existing `llm_clients.py` uses raw httpx to call OpenAI API (not the SDK). However, the `openai==1.3.0` package is installed. If code elsewhere uses the `openai` package directly, upgrading to v2.x changes the response format -- `output` fields can now be multi-modal (string | array) instead of string-only.
**Why it happens:** The codebase's `OpenAIClient` class in `llm_clients.py` does NOT use the `openai` package at all -- it makes raw HTTP calls via httpx. This is actually safe for the v2 upgrade, but any other code that imports `openai` directly will break.
**How to avoid:** Grep the entire codebase for `import openai` or `from openai` before upgrading. The existing raw httpx approach in `llm_clients.py` is unaffected by SDK version changes.
**Warning signs:** `AttributeError` on response objects, `output` field type errors.

### Pitfall 2: SQLAlchemy Async Engine Misconfiguration with Supabase

**What goes wrong:** `DuplicatePreparedStatementError` under concurrent requests when using asyncpg with Supabase's PgBouncer.
**Why it happens:** Supabase routes connections through PgBouncer in transaction mode, which does not support PostgreSQL prepared statements. asyncpg uses prepared statements by default.
**How to avoid:** Use direct connection (port 5432), set `statement_cache_size=0` in `connect_args`, and set `server_settings={"jit": "off"}`.
**Warning signs:** Intermittent `asyncpg.exceptions.DuplicatePreparedStatementError` under load.

### Pitfall 3: CRA Environment Variables Don't Work in Vite

**What goes wrong:** All `REACT_APP_*` environment variables stop working after Vite migration.
**Why it happens:** CRA uses `process.env.REACT_APP_*`; Vite uses `import.meta.env.VITE_*`. Different prefix, different access pattern.
**How to avoid:** (1) Rename all env vars from `REACT_APP_*` to `VITE_*`. (2) Replace all `process.env.REACT_APP_*` references with `import.meta.env.VITE_*` in source code. (3) Update `.env.example`.
**Warning signs:** `undefined` values for environment variables in the frontend.

### Pitfall 4: Vite Requires Explicit .jsx Extensions

**What goes wrong:** Build fails with JSX parsing errors after migrating from CRA.
**Why it happens:** CRA's webpack config treats all .js files as potentially containing JSX. Vite is strict -- JSX syntax requires .jsx or .tsx extensions.
**How to avoid:** Rename all files containing JSX from `.js` to `.jsx` (or `.tsx` if adding TypeScript). The existing frontend has 10 files to rename: `App.js`, `index.js`, all 7 component files, `api.js`, `sessionCache.js`.
**Warning signs:** `SyntaxError: Unexpected token '<'` during Vite dev server startup.

### Pitfall 5: Celery Worker Cannot Import FastAPI App Dependencies

**What goes wrong:** Celery worker process fails to start because it imports FastAPI dependencies that require an event loop.
**Why it happens:** Celery workers run in separate processes. If `celery_app.py` imports from modules that trigger async initialization (e.g., creating async engine at import time), it will fail.
**How to avoid:** Keep `celery_app.py` minimal -- only Celery configuration. Use lazy imports for database/service dependencies inside task functions, not at module level.
**Warning signs:** `RuntimeError: no running event loop` when starting Celery worker.

### Pitfall 6: Alembic Not Wired to Async Engine

**What goes wrong:** Alembic generates migrations but cannot apply them because it's not configured for async.
**Why it happens:** Default Alembic `env.py` uses synchronous SQLAlchemy. The codebase uses asyncpg which requires async engine.
**How to avoid:** Configure Alembic's `env.py` with `run_async` pattern:
```python
# alembic/env.py
from app.db.engine import engine
from app.db.models import Base

async def run_async_migrations():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```
**Warning signs:** `sqlalchemy.exc.MissingGreenlet` error when running `alembic upgrade head`.

---

## Dual Database Resolution Strategy

### Current State (CRITICAL TO UNDERSTAND)

The codebase has TWO database layers that are NOT connected:

1. **`backend/app/db/connection.py`** -- Supabase REST client via `supabase.create_client()`. This is the ONLY working database connection. Used by `author_styles_service.py`.

2. **`backend/app/db/models.py`** -- Full SQLAlchemy ORM models (User, Profile, Job, Application, Match, Document, AgentAction, AgentOutput). These models exist but have NO engine, NO session factory, and are NEVER used by any service.

3. **`supabase/migrations/00001_initial_schema.sql`** -- SQL migration creating the actual Postgres tables. This was applied directly to Supabase, bypassing Alembic entirely.

### Resolution Plan

**Objective:** SQLAlchemy is the ONLY application data access layer. Supabase SDK used ONLY for: auth token forwarding, file storage (resumes), and realtime subscriptions.

**Files to Create:**
- `backend/app/db/engine.py` -- Async engine + session factory (see Pattern 1 above)
- `backend/app/db/session.py` -- FastAPI dependency for injecting DB sessions

**Files to Modify:**
- `backend/app/db/connection.py` -- Keep but rename to `supabase_client.py`; add docstring clarifying it is ONLY for storage/auth, not data
- `backend/app/services/author_styles_service.py` -- Refactor to use SQLAlchemy session instead of Supabase client (this is the only service using the DB today)

**Files to Create for Alembic:**
- `backend/alembic.ini` -- Alembic configuration
- `backend/alembic/env.py` -- Async migration runner pointing to SQLAlchemy engine
- `backend/alembic/versions/` -- Migration files (initial migration should match existing schema)

**Migration Strategy:**
1. Create SQLAlchemy async engine configuration
2. Generate initial Alembic migration FROM the existing ORM models
3. Since the tables already exist in Supabase (from 00001_initial_schema.sql), stamp the migration as "applied": `alembic stamp head`
4. All future schema changes go through Alembic, not raw SQL

**Confidence:** HIGH -- the ORM models already match the SQL schema. This is a wiring exercise, not a rewrite.

---

## CRA-to-Vite Migration Path (This Specific Frontend)

### Current Frontend State

- 10 JavaScript files (no TypeScript)
- Uses `react-scripts` 5.0.1 (CRA)
- `public/index.html` as entry point
- `REACT_APP_API_URL` environment variable in `api.js`
- Proxy configured to `http://localhost:8000` in `package.json`
- ESLint configured via CRA presets in `package.json`
- No path aliases, no CSS modules, standard Tailwind setup

### Step-by-Step Migration

1. **Uninstall CRA:** `npm uninstall react-scripts`
2. **Install Vite:** `npm install vite @vitejs/plugin-react --save-dev`
3. **Create `vite.config.ts`:**
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
   });
   ```
4. **Move `public/index.html` to `frontend/index.html`** (project root for frontend)
5. **Edit `index.html`:**
   - Remove `%PUBLIC_URL%` references
   - Add `<script type="module" src="/src/index.jsx"></script>` before `</body>`
6. **Rename `.js` files containing JSX to `.jsx`:**
   - `src/index.js` -> `src/index.jsx`
   - `src/App.js` -> `src/App.jsx`
   - All component files -> `.jsx`
   - `src/services/api.js` stays `.js` (no JSX)
   - `src/utils/sessionCache.js` stays `.js` (no JSX)
7. **Update environment variables:**
   - `REACT_APP_API_URL` -> `VITE_API_URL`
   - `process.env.REACT_APP_API_URL` -> `import.meta.env.VITE_API_URL`
8. **Update `package.json` scripts:**
   ```json
   "scripts": {
     "dev": "vite",
     "build": "vite build",
     "preview": "vite preview",
     "test": "vitest",
     "lint": "eslint src/"
   }
   ```
9. **Remove CRA-specific config from `package.json`:** Remove `eslintConfig`, `browserslist`, `proxy` keys
10. **Install TypeScript (incremental):**
    ```bash
    npm install typescript @types/react @types/react-dom --save-dev
    ```
    Create `tsconfig.json` -- new files in `.tsx`, convert existing `.jsx` files incrementally.

### Proxy Configuration

CRA used `"proxy": "http://localhost:8000"` in `package.json`. Vite uses `server.proxy` in `vite.config.ts`. The proxy config above handles the `/api` prefix.

**Confidence:** HIGH -- well-documented migration path, this is a small frontend (10 files).

---

## GitHub Actions CI/CD Pipeline

### Workflow Structure

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7
        ports: [6379:6379]
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: jobpilot_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports: [5432:5432]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: pip

      - name: Install dependencies
        run: pip install -r backend/requirements.txt

      - name: Run linting
        run: ruff check backend/

      - name: Run type checking
        run: mypy backend/app/ --ignore-missing-imports

      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/jobpilot_test
          REDIS_URL: redis://localhost:6379/0
        run: |
          cd backend
          pytest tests/ -v --cov=app --cov-report=xml \
            --cov-fail-under=80

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: backend/coverage.xml

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: npm
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: cd frontend && npm ci

      - name: Run linting
        run: cd frontend && npm run lint

      - name: Run tests
        run: cd frontend && npm run test -- --run

      - name: Build
        run: cd frontend && npm run build
```

**Confidence:** HIGH -- standard GitHub Actions patterns for FastAPI + React. PostgreSQL and Redis service containers are well-supported.

---

## Code Examples

### Clerk Frontend Integration

```tsx
// frontend/src/providers/ClerkProvider.tsx
import { ClerkProvider } from '@clerk/clerk-react';

const CLERK_PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

export function AuthProvider({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY}>
      {children}
    </ClerkProvider>
  );
}
```

```tsx
// frontend/src/services/api.ts - Updated with Clerk token
import { useAuth } from '@clerk/clerk-react';
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 60000,
});

// Hook to create authenticated API client
export function useApiClient() {
  const { getToken } = useAuth();

  api.interceptors.request.use(async (config) => {
    const token = await getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  return api;
}
```

### Celery Task Example (Agent-Ready)

```python
# backend/app/worker/tasks.py
from .celery_app import celery_app
import asyncio

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=240,
    time_limit=300,
)
def example_agent_task(self, user_id: str, task_data: dict):
    """Example background task that will be extended for agents in Phase 3."""
    try:
        # Run async code inside sync Celery task
        result = asyncio.run(_execute_task(user_id, task_data))
        return result
    except Exception as exc:
        self.retry(exc=exc)

async def _execute_task(user_id: str, task_data: dict):
    """Async task execution."""
    # This will be replaced with agent logic in Phase 3
    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        # Do work with database
        pass

    return {"status": "completed", "user_id": user_id}
```

### LLM Cost Tracking Middleware

```python
# backend/app/observability/cost_tracker.py
import redis.asyncio as aioredis
from datetime import datetime
import os

# Token-to-cost rates (approximate, update periodically)
MODEL_COSTS = {
    "gpt-4-turbo-preview": {"input": 10.0 / 1_000_000, "output": 30.0 / 1_000_000},
    "gpt-3.5-turbo": {"input": 0.5 / 1_000_000, "output": 1.5 / 1_000_000},
    "claude-3-opus-20240229": {"input": 15.0 / 1_000_000, "output": 75.0 / 1_000_000},
}

MONTHLY_BUDGET = 6.00  # $6/user/month

async def track_llm_cost(
    user_id: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
):
    """Record LLM usage cost to Redis aggregation."""
    rates = MODEL_COSTS.get(model, {"input": 10.0 / 1_000_000, "output": 30.0 / 1_000_000})
    cost = (input_tokens * rates["input"]) + (output_tokens * rates["output"])

    redis_client = aioredis.from_url(os.getenv("REDIS_URL"))
    month_key = datetime.utcnow().strftime("%Y-%m")

    # Increment monthly cost counter
    key = f"llm_cost:{user_id}:{month_key}"
    current = await redis_client.incrbyfloat(key, cost)
    await redis_client.expire(key, 60 * 60 * 24 * 35)  # 35 day TTL

    # Alert at 80% budget
    if current > MONTHLY_BUDGET * 0.8:
        await redis_client.publish(
            f"alerts:cost:{user_id}",
            f"User {user_id} at {current/MONTHLY_BUDGET*100:.0f}% of monthly LLM budget"
        )

    await redis_client.close()
    return cost
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CRA (react-scripts) | Vite | CRA deprecated Feb 2025 | Must migrate; no security patches |
| OpenAI SDK v1 (`openai==1.x`) | OpenAI SDK v2 (`openai>=2.0`) | v2.0.0 released late 2025 | Response format changes; Assistants API deprecated |
| `langchain` 0.0.x | `langchain-core` 1.0 or skip entirely | LangGraph 1.0 Oct 2025 | Old langchain is dead; can use raw SDKs for Phase 1 |
| Black + flake8 | Ruff | Ruff 1.0 stable 2025 | One tool replaces both, 10-100x faster |
| Jest (via CRA) | Vitest | Vite ecosystem standard | Jest-compatible API, native Vite integration |
| Manual JWT auth | Clerk | N/A (greenfield) | Handles OAuth, session management, user management |
| Synchronous SQLAlchemy | Async SQLAlchemy + asyncpg | SQLAlchemy 2.0 (2023) | Required for async FastAPI; `statement_cache_size=0` for Supabase |

**Deprecated/outdated in this codebase:**
- `langchain==0.0.340`: Remove entirely. Not needed until Phase 3, and even then LangGraph or raw SDKs are preferred.
- `python-jose==3.3.0` + `passlib==1.7.4`: Remove. Clerk replaces custom auth.
- `react-scripts==5.0.1`: Remove. Dead project, security risk.

---

## Open Questions

1. **Clerk pricing at scale:**
   - What we know: Clerk has a free tier and per-MAU pricing. `fastapi-clerk-auth` is a community package (not official Clerk).
   - What is unclear: Exact cost at 1K-10K MAU, and whether the AuthProvider abstraction should be built in Phase 1 or deferred.
   - Recommendation: Build the AuthProvider interface in Phase 1 as a thin wrapper. It is low effort and enables future migration.

2. **Email service choice (ADR-6):**
   - What we know: Resend is developer-first with free tier (3K emails/mo). SendGrid is established but pricier.
   - What is unclear: The roadmap says "resolve ADR-6" in Phase 1. The BMAD stories reference "SendGrid" but the TECHNICAL_STACK.md recommends Resend.
   - Recommendation: Use Resend. Free tier is sufficient for development and beta. Clean Python SDK.

3. **Supabase Storage for file uploads (Story 0-13):**
   - What we know: Supabase Storage SDK handles file upload, signed URLs, and access policies.
   - What is unclear: Whether virus scanning is available on Supabase free tier (Story 0-13 acceptance criteria require it).
   - Recommendation: Implement upload without virus scanning initially; add ClamAV scanning as a Celery task if Supabase doesn't provide it natively.

4. **Performance baseline tooling (Story 0-14):**
   - What we know: Story requires k6 or similar load testing. This is a "nice to have" for Phase 1.
   - What is unclear: Whether to integrate k6 into CI or run manually.
   - Recommendation: Run k6 manually to establish baselines. CI integration is Phase 9 hardening.

5. **OpenAI SDK v2 impact on existing LLM client:**
   - What we know: The existing `OpenAIClient` in `llm_clients.py` uses raw httpx, NOT the `openai` package. So the v2 upgrade may have zero impact on working code.
   - What is unclear: Whether any other file imports the `openai` package directly.
   - Recommendation: Grep for `import openai` / `from openai`. If only `requirements.txt` references it, upgrading is safe. Consider rewriting `OpenAIClient` to use the official SDK v2 for better features (structured output, streaming).

---

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `backend/app/db/models.py`, `backend/app/db/connection.py`, `backend/app/core/llm_clients.py`, `backend/app/main.py`, `frontend/package.json`, `backend/requirements.txt`
- Supabase migration: `supabase/migrations/00001_initial_schema.sql`
- [OpenTelemetry FastAPI Instrumentation Docs](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html)
- [Sentry FastAPI Integration](https://docs.sentry.io/platforms/python/integrations/fastapi/)
- [fastapi-clerk-auth on PyPI](https://pypi.org/project/fastapi-clerk-auth/) -- v0.0.9, MIT license
- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)

### Secondary (MEDIUM confidence)
- [CRA to Vite Migration Guide (DEV Community)](https://dev.to/solitrix02/goodbye-cra-hello-vite-a-developers-2026-survival-guide-for-migration-2a9f)
- [Celery + FastAPI Production Guide (TestDriven.io)](https://testdriven.io/blog/fastapi-and-celery/)
- [OpenAI Python SDK Releases](https://github.com/openai/openai-python/releases) -- v2.16.0 latest
- [Scalable WebSocket with FastAPI and Broadcaster](https://www.fastapitutorial.com/blog/scalable-fastapi-redis-websocket/)
- [GitHub Actions CI for FastAPI (PyImageSearch)](https://pyimagesearch.com/2024/11/04/enhancing-github-actions-ci-for-fastapi-build-test-and-publish/)
- [Sentry + OpenTelemetry Setups for Python (Medium)](https://medium.com/@Modexa/10-sentry-opentelemetry-setups-for-python-youll-reuse-forever-a3244f810c10)

### Tertiary (LOW confidence -- validate before using)
- [fastapi-websocket-pubsub on PyPI](https://pypi.org/project/fastapi-websocket-pubsub/) -- v1.0.1, less mainstream
- [Celery + Redis Ultimate 2025 Production Guide (Medium)](https://medium.com/@dewasheesh.rana/celery-redis-fastapi-the-ultimate-2025-production-guide-broker-vs-backend-explained-5b84ef508fa7)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all versions verified via PyPI/npm, codebase inspected directly
- Architecture patterns: HIGH -- patterns are well-established (SQLAlchemy async, Celery, Clerk)
- CRA-to-Vite migration: HIGH -- well-documented, small frontend (10 files)
- Dual DB resolution: HIGH -- codebase directly inspected, issue is clear (no engine configured)
- Celery + Redis: HIGH -- battle-tested stack, standard configuration
- Clerk + FastAPI: MEDIUM-HIGH -- community package (v0.0.9, 1 contributor), but the JWT/JWKS validation is simple and fallback exists
- OpenTelemetry + Sentry: HIGH -- both are industry standard with official FastAPI support
- WebSocket: MEDIUM-HIGH -- standard pattern, but broadcaster library choice needs validation
- CI/CD: HIGH -- standard GitHub Actions patterns
- Pitfalls: HIGH -- all sourced from official issue trackers and documentation

**Research date:** 2026-01-30
**Valid until:** 2026-03-01 (stable infrastructure, 30-day window)
