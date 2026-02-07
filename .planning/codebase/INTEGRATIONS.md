# External Integrations

**Analysis Date:** 2026-01-30

## APIs & External Services

**LLM Providers:**
- OpenAI (GPT-4, GPT-3.5, DALL-E)
  - SDK/Client: `openai` 1.6.1 (Python)
  - Auth: `OPENAI_API_KEY` environment variable
  - Uses: `backend/app/core/llm_clients.py` (OpenAIClient class)
  - Endpoints: https://api.openai.com/v1/chat/completions, https://api.openai.com/v1/images/generations
  - Timeout: 60 seconds

- Anthropic Claude
  - SDK/Client: `anthropic` 0.8.1 (Python)
  - Auth: `ANTHROPIC_API_KEY` environment variable
  - Uses: `backend/app/core/llm_clients.py` (AnthropicClient class)
  - Endpoint: https://api.anthropic.com/v1/messages
  - API Version: 2023-06-01
  - Timeout: 60 seconds

**LLM Abstraction:**
- Primary abstraction: `backend/app/core/llm_clients.py` LLMClient class
- Supports fallback to local mock client when no API keys configured
- Provider selection logic: Checks OPENAI_API_KEY first, then ANTHROPIC_API_KEY, falls back to LocalLLMClient
- Used by: EmailService, LinkedInPostService, AuthorStylesService

**Web Services & Utilities:**
- Web Scraping (no external API, local implementation)
  - Client: httpx AsyncClient + BeautifulSoup4
  - Target: Generic websites for company research
  - Timeout: 10 seconds per request, max 2 retries
  - Used by: `backend/app/core/web_scraper.py` (WebScraper class)
  - Methods: Single page scrape via `scrape_website()`, multi-page via `scrape_multiple_pages()`

- Web Search Service (placeholder for external integration)
  - Implementation: `backend/app/services/web_search_service.py`
  - Methods available for: trending hashtags, company insights, industry trends, competitor analysis
  - Infrastructure ready for SerpAPI or Google Search integration (not currently configured)

## Data Storage

**Databases:**
- Supabase (PostgreSQL)
  - Connection: Environment variables `SUPABASE_URL` and `SUPABASE_KEY`
  - Client: `supabase` 2.3.0 Python SDK
  - Implementation: `backend/app/db/connection.py`
  - Functions: `get_supabase_client()` creates client, `get_client()` singleton pattern
  - ORM: SQLAlchemy 2.0.23 configured (for future use)
  - Migrations: Alembic 1.13.0 configured for schema management

**In-Memory Storage (Development):**
- Email storage: Dict in `EmailService.__init__()` - `self.email_storage = {}`
- Tracking events: List in `EmailService.__init__()` - `self.tracking_events = []`
- Note: Marked for database migration in production

**File Storage:**
- Local filesystem only (in-memory for testing)
- Document upload handling: `backend/app/services/author_styles_service.py` processes Excel files
- Resume parsing: PDF via PyPDF2, DOCX via python-docx

**Caching:**
- Not actively configured
- Redis commented out in requirements (`# redis==5.0.1`)
- Session cache available: `frontend/src/utils/sessionCache.js`

## Authentication & Identity

**Auth Provider:**
- Custom JWT-based implementation
- Implementation: `backend/app/core/llm_clients.py` and `frontend/src/services/api.js`
- Token storage: localStorage (frontend)
- Bearer token format: `Authorization: Bearer {token}`

**Frontend Auth Flow:**
- Token stored in localStorage via key: `authToken`
- Request interceptor: Attaches token to all API requests
- Response interceptor: Handles 401 errors by clearing token and redirecting to `/login`

**Backend Auth:**
- JWT handling via `python-jose` 3.3.0
- Password hashing via `passlib[bcrypt]` 1.7.4
- Email validation via `email-validator` 2.1.0

## Monitoring & Observability

**Error Tracking:**
- Not configured to external service
- Local logging via Python logging module
- Error handlers in `backend/app/core/error_handlers.py`

**Logs:**
- Backend: Python logging to console/stdout
- Format options: JSON (via `structlog` 23.2.0) or standard format
- Controlled by: `LOG_FORMAT` environment variable (json/standard)
- Log level: `LOG_LEVEL` environment variable (default: INFO)
- JSON logging: `python-json-logger` 2.0.7 for structured logs

**Metrics:**
- Prometheus client available: `prometheus-client` 0.19.0
- Implementation: `backend/app/monitoring/alerts.py` tracks API calls by provider and web search requests
- Metrics tracked: Total email generations, total post generations, openai calls, anthropic calls, web_search calls

**Health Check Endpoint:**
- GET `/health` - Returns service health status
- Frontend calls: `utilityService.checkHealth()` in `frontend/src/App.js`

## CI/CD & Deployment

**Hosting:**
- Not configured (self-hosted option)
- Deployment-ready: ASGI application via Uvicorn
- Environment: `API_ENV` environment variable (development/production)
- Allowed origins: Configured via `ALLOWED_ORIGINS` (comma-separated list)
- Defaults: http://localhost:3000, http://localhost:3001

**CI Pipeline:**
- Not detected
- Pre-commit hooks available: `pre-commit` 3.5.0 configured

## Environment Configuration

**Required env vars (Backend):**
- `OPENAI_API_KEY` - OpenAI API key (if using OpenAI)
- `ANTHROPIC_API_KEY` - Anthropic API key (if using Anthropic)
- `SUPABASE_URL` - Database connection URL
- `SUPABASE_KEY` - Database API key
- `TRACKING_BASE_URL` - Email tracking pixel base URL (default: http://localhost:8000/api/track)
- `API_HOST` - Server host (default: 0.0.0.0)
- `API_PORT` - Server port (default: 8000)
- `API_ENV` - Environment type (development/production)
- `SECRET_KEY` - Session/token signing key
- `ALLOWED_ORIGINS` - CORS-allowed origins (comma-separated)

**Required env vars (Frontend):**
- `REACT_APP_API_URL` - Backend API base URL (default: http://localhost:8000)

**Optional env vars:**
- `LLM_PROVIDER` - Force specific LLM provider (openai/anthropic/local)
- `OPENAI_MODEL` - OpenAI model name (default: gpt-4-turbo-preview)
- `ANTHROPIC_MODEL` - Anthropic model name (default: claude-3-opus-20240229)
- `LOG_LEVEL` - Logging level (default: INFO)
- `LOG_FORMAT` - Logging format (json/standard, default: standard)
- `SCRAPER_TIMEOUT` - Web scraper timeout in seconds (default: 30)
- `SCRAPER_MAX_RETRIES` - Web scraper retry attempts (default: 3)
- `SCRAPER_USER_AGENT` - Custom User-Agent for scraping
- `EMAIL_TRACKING_ENABLED` - Enable email tracking (default: true)
- `RATE_LIMIT_ENABLED` - Enable rate limiting (default: true)
- `RATE_LIMIT_REQUESTS` - Rate limit request count (default: 100)
- `RATE_LIMIT_PERIOD` - Rate limit period in seconds (default: 3600)

**Secrets location:**
- Development: `.env` file (gitignored)
- Production: Environment variables, no file storage
- Template: `.env.example` provides configuration reference

## Webhooks & Callbacks

**Incoming:**
- No incoming webhooks configured

**Outgoing:**
- Email tracking: Generates tracking pixel URLs at `{TRACKING_BASE_URL}/email/{email_id}/pixel.gif`
- Implementation: `backend/app/services/email_service.py` - `_add_tracking_pixel()` method
- Endpoint: Tracking pixel served by `/api/track/email/{email_id}/pixel.gif` (FastAPI route)

## API Documentation

**OpenAPI/Swagger:**
- Auto-generated: FastAPI Swagger UI at `/docs`
- ReDoc documentation at `/redoc`
- API Title: "AI Content Generation Suite"
- API Version: 1.0.0

**CORS Configuration:**
- File: `backend/app/main.py`
- Allowed origins: localhost:3000, localhost:3001
- Allowed methods: All (*)
- Allowed headers: All (*)
- Allow credentials: True

---

*Integration audit: 2026-01-30*
