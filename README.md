# JobPilot

An AI-powered multi-agent career platform that automates job discovery, resume tailoring, application tracking, and outreach generation.

## Features

- **Multi-Agent System** with tiered autonomy (L0-L3): suggestions-only to fully autonomous
- **Daily Briefings** with personalized job matches and agent activity summaries
- **Resume Parsing & Tailoring** per job posting
- **Cold Email & LinkedIn Post Generation** with author style analysis
- **H1B Sponsorship Research** and employer scoring
- **Application Pipeline** management with follow-up automation
- **Enterprise Administration** with org-level controls

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | FastAPI, SQLAlchemy async (asyncpg), Celery + Redis, Clerk auth, Pydantic 2 |
| **Frontend** | React 18, TypeScript, Vite 6, Tailwind CSS, Zustand, TanStack Query, Clerk |
| **Database** | Supabase PostgreSQL, Alembic migrations, Row-Level Security |
| **Testing** | pytest + pytest-asyncio (backend), Vitest + testing-library (frontend) |
| **Observability** | Sentry, Langfuse (LLM tracing), PostHog analytics, OpenTelemetry |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (via Supabase or local)
- Redis (for Celery workers)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install

# Configure environment
cp .env.example .env
# Edit .env with your Clerk and API keys

# Start dev server
npm run dev
```

### Database

```bash
# Apply migrations to Supabase
supabase db push

# Or run locally
python backend/scripts/run_migrations.py
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Project Structure

```
.
├── backend/             # FastAPI backend (app factory pattern)
│   ├── app/
│   │   ├── agents/      # Multi-agent framework (orchestrator, brake, tiers)
│   │   ├── api/v1/      # Versioned API routes
│   │   ├── auth/        # Clerk JWT authentication
│   │   ├── core/        # LLM clients, web scraper, error handling
│   │   ├── db/          # SQLAlchemy engine, Supabase client
│   │   ├── middleware/   # Rate limiting
│   │   ├── observability/ # Sentry, Langfuse, OpenTelemetry
│   │   ├── services/    # Business logic (email, posts, job sources)
│   │   └── worker/      # Celery background tasks
│   └── tests/
├── frontend/            # React SPA
│   └── src/
│       ├── components/  # UI components by domain
│       ├── pages/       # Route-level components
│       ├── services/    # API clients
│       ├── providers/   # React context providers
│       └── hooks/       # Custom hooks
├── supabase/            # Database migrations
└── docs/                # Architecture documentation
```

## API Endpoints

### v1 API (`/api/v1/`)
- `GET /api/v1/health` - Health check
- `POST /api/v1/onboarding/*` - User onboarding flow
- `GET /api/v1/briefings` - Daily briefings
- `GET /api/v1/matches` - Job matches
- `POST /api/v1/applications` - Application tracking
- `GET /api/v1/agents/status` - Agent status and control

### Legacy (`/api/`)
- `POST /api/generate-email` - Cold email generation
- `POST /api/generate-post` - LinkedIn post generation
- `POST /api/parse-resume` - Resume parsing

## Testing

```bash
# Backend
cd backend
pytest                    # All tests
pytest -x                 # Stop on first failure
pytest --cov=app          # With coverage

# Frontend
cd frontend
npm test                  # Vitest
npm run lint              # ESLint
```

## License

MIT
