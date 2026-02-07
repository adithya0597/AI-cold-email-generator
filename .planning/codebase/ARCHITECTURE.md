# Architecture

**Analysis Date:** 2026-01-30

## Pattern Overview

**Overall:** Microservice-style separation between frontend and backend with layered backend architecture.

**Key Characteristics:**
- Frontend-backend API separation with clear REST boundaries
- Service-oriented backend with specialized domain services
- Async-first design using async/await throughout
- Plugin-style LLM provider abstraction for flexible AI model selection
- Session-based state management with localStorage caching in frontend

## Layers

**Presentation (Frontend):**
- Purpose: User-facing React application for email and LinkedIn post generation
- Location: `frontend/src/`
- Contains: React components, form management, API integration
- Depends on: Backend API endpoints, localStorage for session cache
- Used by: End users via browser

**API Layer (Backend):**
- Purpose: FastAPI HTTP endpoints exposing business operations
- Location: `backend/app/main.py`
- Contains: Route definitions, request/response models, error handling
- Depends on: Service layer for business logic
- Used by: Frontend React application, external utilities

**Service Layer (Backend):**
- Purpose: Core business logic for content generation and data processing
- Location: `backend/app/services/`
- Contains: `email_service.py`, `post_service.py`, `author_styles_service.py`, `web_search_service.py`
- Depends on: LLM clients, database models, web scraper, utilities
- Used by: API layer routes

**Core Utilities (Backend):**
- Purpose: Shared infrastructure and integrations
- Location: `backend/app/core/`
- Contains: LLM client abstractions, web scraping, configuration, error handling
- Depends on: External APIs (OpenAI, Anthropic), HTTP libraries
- Used by: Service layer, main application

**Database Layer (Backend):**
- Purpose: Data persistence and schema definition
- Location: `backend/app/db/`
- Contains: SQLAlchemy ORM models, Supabase connection management
- Depends on: Supabase PostgreSQL backend
- Used by: Services for data storage (author styles, email tracking)

**Models/Schemas (Backend):**
- Purpose: Request/response validation and type definitions
- Location: `backend/app/models.py`
- Contains: Pydantic models for all API contracts
- Depends on: Pydantic library
- Used by: API routes, services

## Data Flow

**Cold Email Generation Flow:**

1. Frontend (`ColdEmailGenerator.js`) collects resume, recipient info, company URL
2. User submits form to `POST /api/generate-email`
3. Backend `main.py` receives request, validates via `ColdEmailRequest` model
4. `main.py` spawns parallel scraping tasks:
   - Scrapes company website via `WebScraper.scrape_website()`
   - Optionally scrapes sender's LinkedIn profile
   - Optionally scrapes job posting URL
5. `EmailService.generate_cold_email()` receives scraped content:
   - Analyzes company tone via `_analyze_company_tone()`
   - Synthesizes value propositions via `_synthesize_value_propositions()`
   - Generates subject line via `_generate_subject()`
   - Generates email body via `_generate_email_body()`
6. Adds tracking pixel URL to email body
7. Returns `ColdEmailResponse` with email ID, subject, body, and value propositions
8. Frontend displays email, caches to sessionStorage, enables copy/download

**LinkedIn Post Generation Flow:**

1. Frontend (`LinkedInPostGenerator.js`) collects topic, industry, style, goals
2. User submits form to `POST /api/generate-post`
3. Backend `main.py` receives request, validates via `LinkedInPostRequest` model
4. `LinkedInPostService.generate_post()` processes:
   - Analyzes influencer style (pre-defined or custom author)
   - If custom author: fetches author's posts from database
   - Scrapes reference URLs if provided
   - Generates hook, body, call-to-action using LLM
   - Generates relevant hashtags
   - Optionally generates image via DALL-E
5. Returns `LinkedInPostResponse` with content, hashtags, image, metrics
6. Frontend displays post, caches to sessionStorage

**Resume Parsing Flow:**

1. Frontend user uploads PDF or DOCX file
2. POST to `/api/parse-resume` with FormData
3. `EmailService.parse_resume()` processes:
   - Detects file type (PDF vs DOCX)
   - Extracts text content
   - Identifies skills and experience
4. Returns `ResumeParsingResult` with parsed text and metadata

**State Management:**

**Frontend:**
- React component state (useState) for form data, loading states
- Session cache via `sessionCache.js` using localStorage
- React Router for page navigation
- Form state managed by `react-hook-form`
- Toast notifications via `react-toastify` for user feedback

**Backend:**
- In-memory dictionaries for email storage and tracking (note: not production-ready)
- Supabase PostgreSQL for author styles persistence
- Pydantic model validation at API boundary
- No session-based state; stateless HTTP design

## Key Abstractions

**LLMClient (Provider Abstraction):**
- Purpose: Abstract multiple LLM providers (OpenAI, Anthropic, Google, local)
- Examples: `backend/app/core/llm_clients.py` (OpenAIClient, AnthropicClient)
- Pattern: Abstract base class with concrete implementations; factory pattern for provider selection
- Usage: Services obtain appropriate client via `LLMClient()` which auto-selects based on environment

**WebScraper:**
- Purpose: Unified web content extraction with retry logic and error handling
- Examples: `backend/app/core/web_scraper.py`
- Pattern: Single class handling HTTP, HTML parsing, content extraction
- Usage: Scrapes company websites, LinkedIn profiles, job postings in parallel

**EmailService:**
- Purpose: Centralize all email generation and tracking logic
- Examples: `backend/app/services/email_service.py`
- Pattern: Service class with public async methods; private helpers for subtasks
- Usage: Called by API route; handles generation, tracking, stats

**LinkedInPostService:**
- Purpose: LinkedIn post generation with style emulation
- Examples: `backend/app/services/post_service.py`
- Pattern: Pre-defined influencer styles + custom author style support
- Usage: Called by API route; manages hashtag generation, image generation

**AuthorStylesService:**
- Purpose: Manage custom author writing styles via Excel upload
- Examples: `backend/app/services/author_styles_service.py`
- Pattern: Service class with database persistence via Supabase
- Usage: Upload, search, export author styles for custom post generation

## Entry Points

**Frontend Entry:**
- Location: `frontend/src/index.js`
- Triggers: Browser load; renders React app to DOM
- Responsibilities: Bootstrap React, mount App component, setup global styles

**Frontend Application:**
- Location: `frontend/src/App.js`
- Triggers: Page load
- Responsibilities: Setup routing, health check, navigation UI, render page components

**Backend Entry:**
- Location: `backend/app/main.py`
- Triggers: `uvicorn app.main:app --reload --port 8000`
- Responsibilities: Initialize FastAPI app, configure CORS, setup routes, initialize services

**API Health Check:**
- Endpoint: `GET /health`
- Triggers: Frontend on App mount, can be called manually
- Responsibilities: Check LLM client health, report service status

## Error Handling

**Strategy:** Layered error handling with graceful degradation.

**Patterns:**

- **API Layer:** FastAPI exception handlers catch HTTPException and generic exceptions; return JSON ErrorResponse
  - File: `backend/app/main.py` lines 366-382
  - Returns: JSON with error type, message, details, timestamp

- **Service Layer:** Try-catch blocks return result objects (success flag + error message)
  - Example: `EmailService.parse_resume()` returns `ResumeParsingResult` with error_message field
  - Allows downstream handling of failures without exceptions

- **Web Scraper:** Validation errors and fetch failures return WebScrapingResult with success=False
  - Retries failed requests up to `max_retries` times
  - Returns descriptive error messages for client handling

- **LLM Clients:** Fallback responses when API fails or keys missing
  - Example: OpenAI client returns `_fallback_response()` on API error
  - Prevents complete failure; allows degraded functionality

- **Frontend:** Toast notifications (react-toastify) for user feedback
  - Success toasts for generation completion
  - Error toasts with error messages
  - Warning toasts for degraded service status

## Cross-Cutting Concerns

**Logging:**
- Backend: Python `logging` module configured at app startup
  - File: `backend/app/main.py` line 28
  - Log level: INFO
  - Used in main.py routes and service classes for tracking operations

**Validation:**
- Backend: Pydantic models at API boundary
  - File: `backend/app/models.py`
  - All request/response models inherit from BaseModel
  - Automatic validation and schema generation via FastAPI
- Frontend: react-hook-form for form validation
  - File: `frontend/src/components/*.js`
  - Error state rendering via form errors object

**Authentication:**
- Current: None; comment in code suggests token-based auth planned (localStorage.authToken)
- Frontend API interceptor ready for Bearer token injection (file: `frontend/src/services/api.js` lines 15-27)
- Backend has no auth routes or middleware implemented yet

**Rate Limiting/Timeouts:**
- Frontend: 60 second HTTP timeout in axios config (file: `frontend/src/services/api.js` line 8)
- Backend: 10 second timeout for web scraper (file: `backend/app/core/web_scraper.py` line 22)
- Backend: 30 second API timeout for LLM calls (file: `backend/app/core/llm_config.py` line 27)

**Email Tracking:**
- Mechanism: Invisible 1x1 GIF pixel returned from tracking endpoint
- File: `backend/app/main.py` lines 197-218
- Stores tracking events in-memory (not production-ready)
- Tracks open events via unique email ID and pixel URL

---

*Architecture analysis: 2026-01-30*
