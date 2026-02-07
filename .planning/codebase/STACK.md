# Technology Stack

**Analysis Date:** 2026-01-30

## Languages

**Primary:**
- Python 3 - Backend API, LLM interactions, web scraping, document processing
- JavaScript/JSX (React) - Frontend UI and client-side logic

**Secondary:**
- CSS (Tailwind CSS) - Styling and responsive design

## Runtime

**Environment:**
- Python 3.x (backend)
- Node.js/npm (frontend)

**Package Manager:**
- pip (Python) - Lockfile: present (`requirements.txt`)
- npm (JavaScript) - Lockfile: present (`package.json`)

## Frameworks

**Core:**
- FastAPI 0.104.1 - REST API framework with async support
- React 18.2.0 - Frontend UI component framework
- React Router DOM 6.20.0 - Client-side routing

**Testing:**
- pytest 7.4.3 - Python unit and integration testing framework
- pytest-asyncio 0.21.1 - Async test support
- pytest-cov 4.1.0 - Code coverage reporting
- pytest-mock 3.12.0 - Mocking utilities
- react-scripts 5.0.1 - React testing utilities via Create React App

**Build/Dev:**
- Uvicorn 0.24.0 - ASGI server for FastAPI
- Tailwind CSS 3.3.6 - Utility-first CSS framework
- PostCSS 8.4.32 - CSS transformation
- Autoprefixer 10.4.16 - Vendor prefix generation
- ESLint 8.55.0 - JavaScript linting
- Prettier 3.1.1 - Code formatting

**Code Quality:**
- black 23.12.0 - Python code formatter
- flake8 6.1.0 - Python linter
- mypy 1.7.1 - Python static type checker
- pre-commit 3.5.0 - Git pre-commit hooks

## Key Dependencies

**AI/LLM Clients:**
- openai 1.3.0-1.6.1 - OpenAI API client for GPT models and DALL-E
- anthropic 0.7.0-0.8.1 - Anthropic Claude API client
- langchain 0.0.340 - LLM orchestration framework (backend only)

**Web Scraping & HTTP:**
- httpx 0.25.1-0.25.2 - Async HTTP client for API calls and web requests
- beautifulsoup4 4.12.2 - HTML parsing and web scraping
- selenium 4.15.2 - Browser automation (backend only)
- lxml 4.9.3 - XML/HTML processing

**Database & ORM:**
- supabase 2.3.0 - PostgreSQL-based database client
- sqlalchemy 2.0.23 - SQL toolkit and ORM
- alembic 1.12.1-1.13.0 - Database migration tool
- asyncpg - PostgeSQL async driver (commented out, for production)

**Document Processing:**
- PyPDF2 3.0.1 - PDF parsing and manipulation
- python-docx 1.1.0 - Word document handling
- openpyxl 3.1.2 - Excel workbook operations
- xlsxwriter 3.1.9 - Excel file creation
- pandas 2.1.3-2.1.4 - Data analysis and manipulation

**Frontend HTTP Client:**
- axios 1.6.2 - Promise-based HTTP client for browser requests

**Frontend UI Components:**
- react-hook-form 7.48.2 - Form state management
- react-toastify 9.1.3 - Toast notifications
- react-dropzone 14.2.3 - Drag-and-drop file uploads
- react-markdown 9.0.1 - Markdown rendering
- react-syntax-highlighter 15.5.0 - Code block syntax highlighting
- react-loader-spinner 5.4.5 - Loading animations
- react-icons 4.12.0 - Icon library (Heroicons, Feather)
- recharts 2.10.3 - Chart and graph visualization
- @headlessui/react 1.7.17 - Unstyled accessible UI components
- @heroicons/react 2.0.18 - Hero Icons SVG collection

**Authentication & Security:**
- python-jose 3.3.0 - JWT token handling
- passlib 1.7.4 - Password hashing and verification
- email-validator 2.1.0 - Email validation

**Utilities:**
- pydantic 2.5.0 - Data validation using Python type hints
- python-multipart 0.0.6 - Multipart form parsing
- python-dotenv 1.0.0 - Environment variable loading
- aiohttp 3.9.1 - Async HTTP client (backend)

**Monitoring & Logging:**
- prometheus-client 0.19.0 - Prometheus metrics collection
- structlog 23.2.0 - Structured JSON logging
- python-json-logger 2.0.7 - JSON formatter for logging

**Testing Utilities:**
- httpx-mock 0.3.1 - HTTP mocking for httpx
- faker 20.0.3 - Fake data generation for tests
- @testing-library/react 14.1.2 - React component testing utilities
- @testing-library/jest-dom 6.1.5 - DOM matchers for Jest
- @testing-library/user-event 14.5.1 - User interaction simulation

## Configuration

**Environment:**
- Configured via `.env.example` template
- Environment variables loaded with python-dotenv and process.env
- Key variables: OPENAI_API_KEY, ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_KEY, TRACKING_BASE_URL, ALLOWED_ORIGINS, LLM_PROVIDER, API_HOST, API_PORT, API_ENV

**Build:**
- Backend: FastAPI app in `backend/app/main.py`, runs via `uvicorn backend.app.main:app`
- Frontend: Create React App configuration in `frontend/package.json`
- Tailwind config: `frontend/tailwind.config.js` with custom color schemes and animations

**API Documentation:**
- FastAPI auto-generated Swagger UI at `/docs`
- ReDoc at `/redoc`

## Platform Requirements

**Development:**
- Python 3.8+ (backend)
- Node.js 14+ with npm (frontend)
- Environment variables from `.env.example`

**Production:**
- PostgreSQL 13+ (via Supabase)
- Python 3.8+ runtime
- Node.js for frontend builds or static hosting (Next.js could replace React)
- Uvicorn or ASGI-compatible server for FastAPI

**Deployment Target:**
- Backend: Any ASGI-compatible server (Heroku, AWS Lambda with adapter, Railway, Fly.io)
- Frontend: Static hosting (Vercel, Netlify, AWS S3 + CloudFront, GitHub Pages)
- Database: Supabase (PostgreSQL managed service)

---

*Stack analysis: 2026-01-30*
