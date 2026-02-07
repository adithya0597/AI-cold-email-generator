# Codebase Structure

**Analysis Date:** 2026-01-30

## Directory Layout

```
AI-cold-email-generator/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI application entry point
│   │   ├── models.py          # Pydantic request/response models
│   │   ├── core/              # Shared utilities and integrations
│   │   │   ├── llm_clients.py # LLM provider abstractions (OpenAI, Anthropic, etc.)
│   │   │   ├── llm_config.py  # Model and token configuration
│   │   │   ├── constants.py   # Global constants
│   │   │   ├── error_handlers.py # Error handling utilities
│   │   │   └── web_scraper.py # Web scraping service
│   │   ├── services/          # Business logic services
│   │   │   ├── email_service.py # Cold email generation and tracking
│   │   │   ├── post_service.py  # LinkedIn post generation
│   │   │   ├── author_styles_service.py # Author style management
│   │   │   └── web_search_service.py # Web search integration
│   │   ├── db/                # Database layer
│   │   │   ├── models.py      # SQLAlchemy ORM models
│   │   │   └── connection.py  # Supabase client initialization
│   │   └── monitoring/        # Observability
│   │       └── alerts.py      # Alert management (unused)
│   ├── tests/                 # Test suite
│   │   ├── conftest.py        # Pytest configuration and fixtures
│   │   ├── test_email_service.py
│   │   ├── test_post_service.py
│   │   ├── test_services.py
│   │   ├── test_hashtag_relevance.py
│   │   └── unit/
│   │       └── test_db/
│   │           └── test_schema.py
│   ├── scripts/               # Helper scripts
│   │   └── run_migrations.py # Database migration runner
│   └── requirements.txt       # Python dependencies
│
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── App.js             # Root component with routing
│   │   ├── index.js           # React entry point
│   │   ├── components/        # React components
│   │   │   ├── LandingPage.js
│   │   │   ├── ColdEmailGenerator.js # Email generation UI
│   │   │   ├── LinkedInPostGenerator.js # LinkedIn post UI
│   │   │   ├── AuthorStylesManager.js # Author style upload/management
│   │   │   ├── Dashboard.js   # Analytics dashboard
│   │   │   └── Settings.js    # User settings
│   │   ├── services/          # API client services
│   │   │   └── api.js         # Axios instance and API methods
│   │   └── utils/             # Utility functions
│   │       └── sessionCache.js # localStorage wrapper for caching
│   ├── public/                # Static assets
│   └── package.json           # Node.js dependencies
│
├── supabase/                  # Database schema and migrations
│   └── migrations/            # SQL migration files
│
├── .planning/                 # GSD planning documents
│   └── codebase/             # This directory; architecture analysis
│
└── README.md                  # Project documentation
```

## Directory Purposes

**backend/app/:**
- Purpose: Main Python application code
- Contains: FastAPI app, models, services, database code
- Key files: `main.py` (FastAPI entry), `models.py` (Pydantic schemas)

**backend/app/core/:**
- Purpose: Reusable infrastructure and integrations
- Contains: LLM client abstractions, web scraping, configuration
- Key files: `llm_clients.py` (provider abstraction), `web_scraper.py` (HTTP + HTML parsing)

**backend/app/services/:**
- Purpose: Domain-specific business logic
- Contains: Email generation, LinkedIn post generation, author styles
- Key files: `email_service.py` (22KB), `post_service.py` (40KB)

**backend/app/db/:**
- Purpose: Data persistence layer
- Contains: SQLAlchemy ORM definitions, Supabase client
- Key files: `models.py` (ORM models), `connection.py` (client factory)

**backend/tests/:**
- Purpose: Unit and integration tests
- Contains: Test fixtures, service tests, database schema tests
- Key files: `conftest.py` (pytest configuration), test_*.py (test modules)

**frontend/src/:**
- Purpose: React application code
- Contains: Components, services, utilities
- Key files: `App.js` (routing), `index.js` (render target)

**frontend/src/components/:**
- Purpose: React UI components
- Contains: Page components and feature components
- Key files: `ColdEmailGenerator.js` (24KB), `LinkedInPostGenerator.js` (31KB)

**frontend/src/services/:**
- Purpose: API integration layer
- Contains: Axios configuration, API method wrappers
- Key files: `api.js` (single file; centralizes all API calls)

**supabase/:**
- Purpose: Database infrastructure
- Contains: SQL migrations for PostgreSQL schema
- Key files: `migrations/` directory with numbered SQL files

## Key File Locations

**Entry Points:**
- `backend/app/main.py`: Backend FastAPI application
- `frontend/src/index.js`: Frontend React entry point
- `frontend/src/App.js`: Frontend routing and layout

**Configuration:**
- `backend/app/core/llm_config.py`: Model selection and token limits
- `backend/app/core/constants.py`: Global constants (email length, hashtag limits)
- `.env.example`: Environment variables template

**Core Logic:**
- `backend/app/services/email_service.py`: Cold email generation (22.5KB)
- `backend/app/services/post_service.py`: LinkedIn post generation (40.7KB)
- `backend/app/services/author_styles_service.py`: Custom author management (13.7KB)
- `backend/app/core/web_scraper.py`: Website content extraction (11.4KB)

**Data Models:**
- `backend/app/models.py`: Pydantic API schemas
- `backend/app/db/models.py`: SQLAlchemy ORM models

**Testing:**
- `backend/tests/conftest.py`: Pytest fixtures and configuration
- `backend/tests/test_email_service.py`: Email service tests
- `backend/tests/test_post_service.py`: LinkedIn post service tests

**Frontend Components:**
- `frontend/src/components/ColdEmailGenerator.js`: Email generation form and results
- `frontend/src/components/LinkedInPostGenerator.js`: LinkedIn post form and results
- `frontend/src/components/AuthorStylesManager.js`: Custom author upload interface

## Naming Conventions

**Files:**
- Snake_case for Python files: `llm_clients.py`, `email_service.py`, `web_scraper.py`
- camelCase for React files: `ColdEmailGenerator.js`, `LinkedInPostGenerator.js`
- All uppercase for constants: `constants.py`, `.env`

**Directories:**
- Lowercase for Python: `app`, `services`, `core`, `tests`
- Lowercase for React: `src`, `components`, `services`, `utils`
- Subdirectories mirror functional domains: `services/`, `db/`, `core/`

**Classes:**
- PascalCase: `ColdEmailGenerator`, `EmailService`, `LinkedInPostService`, `WebScraper`

**Functions/Methods:**
- snake_case in Python: `generate_cold_email()`, `parse_resume()`, `scrape_website()`
- camelCase in React: `handleSubmit()`, `onDrop()`, `checkApiHealth()`

**Constants:**
- SCREAMING_SNAKE_CASE: `MAX_EMAIL_LENGTH`, `DEFAULT_TRACKING_BASE_URL`, `MAX_HASHTAGS`

## Where to Add New Code

**New Backend Service Feature:**
1. Add Pydantic request/response models to `backend/app/models.py`
2. Create service class in `backend/app/services/` (e.g., `new_feature_service.py`)
3. Add route(s) to `backend/app/main.py`
4. Create tests in `backend/tests/test_new_feature.py`

**New Frontend Component:**
1. Create component file in `frontend/src/components/FeatureName.js`
2. Use form management via `react-hook-form` (see `ColdEmailGenerator.js` pattern)
3. Add API calls via exported functions in `frontend/src/services/api.js`
4. Add navigation link in `frontend/src/App.js` Routes
5. Import and use toast notifications from `react-toastify`

**New Shared Utility:**
- Python: Place in `backend/app/core/` with descriptive name
- JavaScript: Place in `frontend/src/utils/` with descriptive name

**New Database Table:**
1. Create SQLAlchemy model in `backend/app/db/models.py`
2. Create SQL migration file in `supabase/migrations/` with format: `XXXXX_description.sql`
3. Run migration via `backend/scripts/run_migrations.py`

**New Environment Variable:**
1. Add to `.env.example` with descriptive comment
2. Access in Python via `os.getenv("VAR_NAME", default_value)`
3. Document usage in comments near access point

## Special Directories

**backend/app/__pycache__/:**
- Purpose: Python bytecode cache
- Generated: Yes (automatic)
- Committed: No (in .gitignore)

**frontend/node_modules/:**
- Purpose: Node.js dependencies
- Generated: Yes (via npm install)
- Committed: No (in .gitignore)

**supabase/migrations/:**
- Purpose: Database schema evolution
- Generated: No (manually created)
- Committed: Yes (version control for schema)

**backend/tests/unit/test_db/:**
- Purpose: Database-specific tests
- Generated: No (manually created)
- Committed: Yes

**htmlcov/:**
- Purpose: Code coverage reports (pytest --cov)
- Generated: Yes
- Committed: No (in .gitignore)

**docs/:**
- Purpose: Project documentation
- Generated: No (manually maintained)
- Committed: Yes

## Module Organization

**Backend Module Imports Pattern:**
```python
# External imports first
from fastapi import FastAPI
from pydantic import BaseModel

# Local imports by layer
from ..models import ColdEmailRequest
from ..services.email_service import EmailService
from ..core.llm_clients import LLMClient
from ..core.constants import MAX_EMAIL_LENGTH
```

**Frontend Module Imports Pattern:**
```javascript
// React and third-party first
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';

// Icons and UI libraries
import { FiMail, FiSend } from 'react-icons/fi';

// Local services
import { emailService } from '../services/api';

// Local utilities
import sessionCache from '../utils/sessionCache';
```

## Build and Dev Output

**Backend Output:**
- Logs: Console output from `uvicorn` server
- Generated: `__pycache__/` directories (bytecode)
- Migrations: Applied to Supabase database

**Frontend Output:**
- Build: `frontend/build/` directory (created by `npm run build`)
- Dev: Hot reload via `react-scripts` development server
- Cache: localStorage entries with key prefix matching component names

---

*Structure analysis: 2026-01-30*
