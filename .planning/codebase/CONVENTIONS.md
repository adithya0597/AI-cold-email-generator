# Coding Conventions

**Analysis Date:** 2026-01-30

## Naming Patterns

**Files:**
- Backend: `snake_case` for all `.py` files (e.g., `llm_clients.py`, `email_service.py`, `error_handlers.py`)
- Frontend: `PascalCase` for React components (e.g., `ColdEmailGenerator.js`, `LinkedInPostGenerator.js`)
- Frontend: `camelCase` for utilities and services (e.g., `sessionCache.js`, `api.js`)

**Functions:**
- Backend: `snake_case` for all functions (e.g., `async def generate_cold_email()`, `def _analyze_company_tone()`)
- Frontend: `camelCase` for functions, `PascalCase` for React components
- Private functions prefixed with `_` (e.g., `_analyze_company_tone()`, `_synthesize_value_propositions()`)

**Variables:**
- Backend: `snake_case` (e.g., `company_text`, `email_id`, `max_tokens`)
- Frontend: `camelCase` (e.g., `generatedEmail`, `uploadedFile`, `valuePropositions`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_EMAIL_LENGTH`, `DEFAULT_TRACKING_BASE_URL`, `CACHE_KEY`)

**Types & Classes:**
- Python: `PascalCase` for classes (e.g., `ColdEmailRequest`, `EmailService`, `LLMClient`, `ServiceError`)
- Python: `PascalCase` for Enums (e.g., `EmailTone`, `PostGoal`, `UserTier`)
- React: `PascalCase` for component files and classes

## Code Style

**Formatting:**
- Frontend uses ESLint with React app configuration (`react-app`, `react-app/jest`)
- Frontend uses Prettier for code formatting (^3.1.1)
- Backend uses Black (^23.11.0) for code formatting
- Backend uses flake8 (^6.1.0) for linting

**Linting:**
- Frontend: ESLint configured in package.json (extends react-app)
- Backend: flake8 for code quality
- Backend: mypy (^1.7.0) for type checking

**Frontend code style:**
- JSX components use functional components with hooks
- Use destructuring in imports: `import { useState, useEffect } from 'react'`
- Props are destructured in component parameters
- Event handlers use arrow functions: `const handleSubmit = async () => {}`

**Backend code style:**
- Type hints on all function signatures: `async def generate(self, prompt: str, **kwargs) -> str:`
- Docstrings on all classes and public methods (triple-quoted format)
- Use async/await for all I/O operations
- Pydantic models for all request/response validation

## Import Organization

**Order:**
1. Standard library imports (e.g., `import logging`, `from typing import Optional`)
2. Third-party imports (e.g., `import axios`, `from fastapi import FastAPI`)
3. Local/relative imports (e.g., `from ..models import ColdEmailRequest`, `from '../services/api'`)
4. Type imports at top level with full paths

**Backend examples:**
- `from typing import List, Dict, Any, Optional`
- `from pydantic import BaseModel, Field, HttpUrl, EmailStr`
- `from ..models import ColdEmailRequest, ColdEmailResponse`
- `from ..core.error_handlers import ServiceError, async_error_handler`

**Frontend examples:**
- `import React, { useState, useEffect } from 'react'`
- `import { useForm } from 'react-hook-form'`
- `import { emailService } from '../services/api'`
- `import sessionCache from '../utils/sessionCache'`

**Path Aliases:**
- None currently configured in frontend (uses relative paths)
- Backend: No path aliases; uses relative imports with `..` notation

## Error Handling

**Backend patterns:**
- Custom exception hierarchy: `ServiceError` (base) with subclasses like `WebScrapingError`, `LLMGenerationError`, `ValidationError`, `RateLimitError`
- All exceptions include `message`, optional `error_code`, and optional `details` dict
- Example: `raise ValidationError(error_msg, "CLIENT_ERROR", error_details)`
- Decorators for error handling: `@async_error_handler(fallback_value=None, log_errors=True)`
- Retry decorator with exponential backoff: `@retry_async(max_attempts=3, delay=1.0, backoff=2.0)`

**Frontend patterns:**
- Use `react-toastify` for user-facing error messages
- Errors logged to toast: `toast.error('Unable to connect to backend API')`
- Try/catch blocks in async operations
- Warnings for degraded services: `toast.warning('Some services may be degraded')`
- Success messages: `toast.success('Resume parsed successfully!')`

**Example backend error handling:**
```python
try:
    return await func(*args, **kwargs)
except Exception as e:
    if isinstance(e, ServiceError):
        raise
    logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
    return fallback_value
```

**Example frontend error handling:**
```javascript
try {
    const result = await emailService.parseResume(file);
    if (result.success) {
        toast.success('Resume parsed successfully!');
    } else {
        toast.error(result.error_message || 'Failed to parse resume');
    }
} catch (error) {
    toast.error('Error parsing resume: ' + error.message);
}
```

## Logging

**Framework:**
- Backend: Python's built-in `logging` module with `structlog` (^23.2.0)
- Frontend: Console logs (no structured logging framework)

**Patterns:**
- Backend logger initialization: `logger = logging.getLogger(__name__)`
- Log at appropriate levels: INFO for general flow, WARNING for retries, ERROR for failures
- Include function names and context: `logger.info(f"Generating cold email for {request.recipient_name}")`
- Log exceptions with context: `logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)`
- Frontend console logs sparingly for debugging only

## Comments

**When to Comment:**
- Complex algorithms or non-obvious business logic
- Workarounds or temporary solutions (mark with reasoning)
- External API integration details
- Avoid over-commenting obvious code

**JSDoc/TSDoc:**
- Backend: Use docstrings for all public functions and classes
- Format: Triple-quoted strings with Args, Returns, Raises sections
- Example:
  ```python
  async def generate_cold_email(
      self,
      request: ColdEmailRequest,
      company_text: str
  ) -> ColdEmailResponse:
      """
      Generate a personalized cold email

      Args:
          request: Email generation request
          company_text: Scraped company website text

      Returns:
          ColdEmailResponse with generated email
      """
  ```

- Frontend: JSDoc for complex functions (rarely used)
- Inline comments for Tailwind class logic or complex conditional rendering

## Function Design

**Size:**
- Backend: Functions typically 20-50 lines; longer functions broken into smaller helpers
- Frontend: React components 50-200 lines; complex logic extracted to custom hooks or utils
- Use helper methods for complex operations (e.g., `_analyze_company_tone()`, `_synthesize_value_propositions()`)

**Parameters:**
- Backend: Use Pydantic models for complex inputs (e.g., `request: ColdEmailRequest`)
- Backend: Use type hints on all parameters
- Frontend: Props passed directly to components; use destructuring
- Avoid more than 3 positional parameters; use kwargs or request objects instead

**Return Values:**
- Backend: Async functions return typed objects (e.g., `-> ColdEmailResponse`)
- Backend: Use tuples for multiple returns or wrap in Pydantic models
- Frontend: Event handlers typically return void
- Always document return types in backend code

## Module Design

**Exports:**
- Backend: Classes and functions explicitly defined at module level
- Frontend: Default export for components, named exports for utilities
- Example backend: `class EmailService: ...` (imported as `from .email_service import EmailService`)
- Example frontend: `export const emailService = { ... }` (imported as `import { emailService } from '../services/api'`)

**Barrel Files:**
- Backend uses `__init__.py` for package initialization but avoids re-exporting
- Frontend `services/api.js` aggregates all API service definitions
- Frontend components imported individually (no barrel file pattern used)

## Async/Await Patterns

**Async functions:**
- All I/O operations use `async def` with `await`
- Concurrent operations use `asyncio.gather()` for parallel execution
- Example: `tone_analysis, value_props = await asyncio.gather(tone_task, value_task)`

**Frontend:**
- Async event handlers: `const onSubmit = async (data) => { ... }`
- Await API calls: `const result = await emailService.generateEmail(data)`
- Never mix promises and async/await in same function

## State Management

**Frontend:**
- React hooks (`useState`, `useEffect`) for component state
- Custom hook pattern for reusable logic
- Session caching via `sessionCache` utility for form state persistence
- Example: `const [loading, setLoading] = useState(false)`
- Example: `const { register, watch, handleSubmit } = useForm()` (react-hook-form)

**Backend:**
- Services initialized at module level: `email_service = EmailService()`
- In-memory storage marked as temporary: `self.email_storage = {}  # In production, use a database`
- Stateless request handlers preferred; state moved to database or cache

## Validation

**Backend:**
- Pydantic models for request validation (auto-executed by FastAPI)
- Field validation via `Field()` constraints: `Field(..., description="...")`
- Custom validators in service methods: decorated with `@validate_input`
- Example: `recipient_name: str = Field(..., description="Name of the email recipient")`

**Frontend:**
- React Hook Form for form validation: `const { register, formState: { errors } } = useForm()`
- Field-level validation with error messages
- File validation in dropzone: `accept: { ... }`

---

*Convention analysis: 2026-01-30*
