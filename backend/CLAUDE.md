# CLAUDE.md - Backend Reference

> For project overview and tech stack, see root `/CLAUDE.md`

## Overview

FastAPI application using an app-factory pattern. Entry point: `uvicorn app.main:app --reload --port 8000`. API docs at `/docs` (Swagger) and `/redoc`.

## Directory Structure

```
backend/
├── app/
│   ├── main.py              # App factory, legacy routes
│   ├── config.py            # pydantic-settings config (import settings)
│   ├── models.py            # Pydantic request/response schemas
│   │
│   ├── api/v1/              # Versioned API routes
│   │   ├── router.py        # Mounts all v1 routers
│   │   ├── health.py        # Health check endpoint
│   │   ├── auth.py          # Clerk auth endpoints
│   │   ├── onboarding.py    # User onboarding flow
│   │   ├── preferences.py   # User job preferences
│   │   ├── briefings.py     # Daily briefing endpoints
│   │   ├── matches.py       # Job match endpoints
│   │   ├── applications.py  # Application tracking
│   │   ├── documents.py     # Resume/cover letter storage
│   │   ├── agents.py        # Agent status and control
│   │   ├── privacy.py       # Blocklist and passive mode
│   │   ├── h1b.py           # H1B sponsor research
│   │   └── ...
│   │
│   ├── services/            # Business logic layer
│   │   ├── email_service.py
│   │   ├── post_service.py
│   │   ├── job_scoring.py
│   │   ├── preference_learning.py
│   │   ├── job_sources/     # Job board integrations
│   │   │   ├── base.py      # Abstract JobSource
│   │   │   ├── aggregator.py
│   │   │   ├── jsearch.py
│   │   │   ├── adzuna.py
│   │   │   └── ...
│   │   └── research/        # Company research services
│   │
│   ├── agents/              # Multi-agent framework
│   │   ├── base.py          # BaseAgent, BrakeActive exception
│   │   ├── tier_enforcer.py # Autonomy tier (L0-L3) enforcement
│   │   ├── brake.py         # Emergency brake (Redis-backed)
│   │   ├── orchestrator.py  # Agent coordination
│   │   ├── core/            # Core agents (job_scout, pipeline, followup)
│   │   ├── pro/             # Pro-tier agents (resume, cover_letter, apply)
│   │   └── briefing/        # Briefing generation agents
│   │
│   ├── core/                # Shared utilities
│   │   ├── llm_clients.py   # OpenAI/Anthropic abstraction
│   │   ├── llm_config.py    # Model selection and token limits
│   │   ├── web_scraper.py   # HTTP + HTML extraction
│   │   ├── error_handlers.py # ServiceError hierarchy
│   │   └── constants.py
│   │
│   ├── db/                  # Database layer
│   │   ├── engine.py        # SQLAlchemy async engine
│   │   ├── session.py       # Session factory + get_db dependency
│   │   └── supabase_client.py # Supabase storage client
│   │
│   ├── auth/                # Authentication
│   │   ├── clerk.py         # ClerkAuth dependency
│   │   └── ws_auth.py       # WebSocket auth
│   │
│   ├── middleware/          # HTTP middleware
│   │   └── rate_limit.py    # Tier-based rate limiting
│   │
│   ├── cache/               # Redis cache
│   │   ├── redis_client.py
│   │   └── pubsub.py        # Real-time updates
│   │
│   ├── worker/              # Celery background tasks
│   │   ├── celery_app.py    # Celery configuration
│   │   ├── dlq.py           # Dead letter queue
│   │   └── retry.py         # Retry policies
│   │
│   └── observability/       # Monitoring
│       ├── tracing.py       # OpenTelemetry setup
│       ├── error_tracking.py # Sentry integration
│       ├── cost_tracker.py  # LLM cost tracking
│       └── langfuse_client.py
│
├── tests/
│   ├── conftest.py          # Fixtures: client, mock_env_vars, mock_user_l0-l3, mock_redis
│   ├── cassettes/           # VCR.py cassettes for LLM tests
│   └── unit/
│       └── test_db/
│
├── scripts/
│   └── run_migrations.py
│
└── requirements.txt
```

## Adding a New Endpoint

1. **Define Pydantic models** in `app/models.py` (or a new file under `app/api/v1/`)
2. **Create service** in `app/services/` with async methods
3. **Create router** in `app/api/v1/` (e.g., `app/api/v1/new_feature.py`)
4. **Register router** in `app/api/v1/router.py`:
   ```python
   from app.api.v1.new_feature import router as new_feature_router
   api_router.include_router(new_feature_router, prefix="/new-feature", tags=["New Feature"])
   ```
5. **Write tests** in `tests/test_new_feature.py`

## Agent Framework

### Base Class
All agents inherit from `BaseAgent` in `app/agents/base.py`:
```python
class JobScoutAgent(BaseAgent):
    async def run(self, user_id: str, params: dict) -> AgentResult:
        # Check brake first
        await check_brake_or_raise(user_id)
        # Execute agent logic
        ...
```

### Tier Enforcer
`tier_enforcer.py` gates actions based on user autonomy level:
- **L0:** Suggestions only — no writes
- **L1:** Drafts — creates pending items for review
- **L2:** Supervised — queues for approval
- **L3:** Autonomous — executes immediately

### Emergency Brake
Redis-backed kill switch in `brake.py`. Check with:
```python
from app.agents.brake import check_brake_or_raise
await check_brake_or_raise(user_id)  # Raises BrakeActive if brake is on
```

### Celery Execution
Agents run as Celery tasks. **Use lazy imports** to avoid loading heavy deps at worker startup:
```python
@celery_app.task
def run_job_scout(user_id: str):
    from app.agents.core.job_scout import JobScoutAgent  # Lazy import
    agent = JobScoutAgent()
    asyncio.run(agent.run(user_id, {}))
```

## Testing

### Commands
```bash
pytest                              # All tests
pytest tests/test_job_scout.py     # Single file
pytest -k "test_scoring"            # Filter by name
pytest -m "not slow"                # Skip slow tests
pytest --cov=app --cov-report=html  # Coverage report in htmlcov/
```

### Configuration
- `asyncio_mode = auto` in pytest config — no need for `@pytest.mark.asyncio`
- Coverage threshold: 80%

### Key Fixtures (from `conftest.py`)
| Fixture | Purpose |
|---------|---------|
| `client` | `AsyncClient` bound to FastAPI app |
| `mock_env_vars` | Sets test API keys and env |
| `test_user_id` | Standard UUID for tests |
| `mock_user_l0` ... `mock_user_l3` | Patch `_get_user_tier` to return specific level |
| `mock_redis` | Mock Redis client for brake/cache tests |
| `redis_brake_active` / `redis_brake_inactive` | Simulate brake state |
| `vcr_config` | VCR.py settings for LLM cassette recording |

### VCR Cassettes
LLM tests use VCR.py to record/replay HTTP interactions:
```python
@pytest.mark.vcr()
async def test_llm_generation(client):
    # Cassette stored in tests/cassettes/test_llm_generation.yaml
    ...
```

## Key Patterns

### Service Layer
- Async methods with type hints
- Private helpers prefixed with `_` (e.g., `_calculate_score()`)
- Return Pydantic models or typed dicts

### Configuration
```python
from app.config import settings
# Access: settings.OPENAI_API_KEY, settings.DATABASE_URL, etc.
```

### Import Order
1. Standard library (`import os`, `from typing import ...`)
2. Third-party (`from fastapi import ...`, `from pydantic import ...`)
3. Local (`from app.services import ...`, `from ..models import ...`)

### Async Concurrency
Use `asyncio.gather` for parallel operations:
```python
results = await asyncio.gather(
    fetch_jobs_from_source_a(query),
    fetch_jobs_from_source_b(query),
    return_exceptions=True  # Don't fail if one source errors
)
```

### Logging Convention
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Processing job matches for user %s", user_id)
logger.error("Failed to fetch jobs: %s", error, exc_info=True)
```

### Rate Limiting Tiers
Defined in `app/middleware/rate_limit.py`:
- Free tier: 100 requests/minute
- Pro tier: 1000 requests/minute
- Enterprise: 10000 requests/minute

## Dependencies

Managed via `requirements.txt`. Key pins:
- `fastapi>=0.104.0`
- `pydantic>=2.5.0`
- `sqlalchemy>=2.0.0`
- `celery>=5.3.0`

Linting: `ruff check app/`
Types: `mypy app/`
