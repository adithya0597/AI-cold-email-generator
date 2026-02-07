# Testing Patterns

**Analysis Date:** 2026-01-30

## Test Framework

**Runner:**
- pytest 7.4.3
- Config: `/backend/pytest.ini`
- Additional: pytest-asyncio, pytest-cov, pytest-mock, pytest-timeout, pytest-env

**Assertion Library:**
- pytest's built-in assert statements (no separate library)

**Run Commands:**
```bash
pytest                           # Run all tests with coverage
pytest tests/                    # Run all tests in tests directory
pytest -v                        # Verbose output
pytest --cov=app                 # Generate coverage report
pytest --cov-report=html         # HTML coverage report (htmlcov/)
pytest -k "test_generate_email"  # Run specific test by name
pytest --markers unit            # Run tests marked as unit
pytest --maxfail=1               # Stop after first failure
```

**Frontend:**
- React Testing Library (^14.1.2)
- Jest (via react-scripts)
- Run: `npm test` (from frontend/)

## Test File Organization

**Location:**
- Backend: `/backend/tests/` directory matches app structure
- Tests co-located with app code in `tests/` directory, not alongside source files
- Example structure:
  - App code: `backend/app/services/email_service.py`
  - Tests: `backend/tests/test_email_service.py`
  - Schema tests: `backend/tests/unit/test_db/test_schema.py`

**Naming:**
- Test files: `test_*.py`
- Test classes: `Test*` (e.g., `TestCoreTablesExist`)
- Test functions: `test_*` (e.g., `test_generate_cold_email`)

**Structure:**
```
backend/tests/
├── __init__.py
├── conftest.py                 # Shared fixtures and configuration
├── test_email_service.py       # Tests for email service
├── test_post_service.py        # Tests for post service
├── test_services.py            # General service tests
├── test_hashtag_relevance.py   # Feature-specific tests
├── unit/
│   ├── __init__.py
│   └── test_db/
│       ├── __init__.py
│       └── test_schema.py      # Database schema validation tests
```

## Test Structure

**Suite Organization:**
```python
# From test_email_service.py
@pytest.fixture
def email_service():
    """Create email service instance"""
    return EmailService()

@pytest.fixture
def sample_email_request():
    """Create sample email request"""
    return ColdEmailRequest(
        user_resume_text="Software engineer with 5 years experience...",
        recipient_name="John Smith",
        ...
    )

@pytest.mark.asyncio
async def test_generate_cold_email(email_service, sample_email_request):
    """Test cold email generation"""
    company_text = "Example Corp is a leading technology company..."
    result = await email_service.generate_cold_email(sample_email_request, company_text)
    assert result.email_id is not None
    assert result.subject is not None
```

**Patterns:**
- Setup: Fixtures provide test data and service instances
- Execution: Call function/method under test with specific inputs
- Assertion: Use assert statements to validate results
- Async support: `@pytest.mark.asyncio` decorator on async test functions
- Mocking: `@patch.object()` context managers for isolated testing

## Mocking

**Framework:**
- `unittest.mock` (from Python standard library)
- `pytest-mock` plugin for simpler syntax
- `httpx-mock` for HTTP mocking

**Patterns:**
```python
# From test_email_service.py - Context manager pattern
with patch.object(email_service.llm_client, 'generate', new_callable=AsyncMock) as mock_generate:
    with patch.object(email_service.llm_client, 'generate_json', new_callable=AsyncMock) as mock_generate_json:
        mock_generate.side_effect = [
            "Professional tone with focus on innovation",  # First call
            "Innovative Partnership Opportunity",          # Second call
            "Dear John,\n\nI noticed Example Corp's..."    # Third call
        ]
        mock_generate_json.return_value = {
            "propositions": ["Reduce development time by 40%", ...]
        }

        result = await email_service.generate_cold_email(sample_email_request, company_text)
        assert result.email_id is not None
```

**AsyncMock usage:**
- Use `AsyncMock` for async functions: `new_callable=AsyncMock`
- Use `side_effect` for multiple return values in sequence
- Use `return_value` for single return value

**What to Mock:**
- External API calls (LLM clients, web scrapers)
- Database operations (marked as "In production, use a database")
- File I/O operations
- Time-dependent operations

**What NOT to Mock:**
- Core business logic
- Model validation (Pydantic models)
- Internal helper functions
- Error handling decorators

## Fixtures and Factories

**Test Data:**
```python
# From conftest.py - Shared fixtures
@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing"""
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_anthropic_key")
    monkeypatch.setenv("TRACKING_BASE_URL", "http://localhost:8000/api/track")

# From test_email_service.py - Feature-specific fixtures
@pytest.fixture
def sample_email_request():
    """Create sample email request"""
    return ColdEmailRequest(
        user_resume_text="Software engineer with 5 years experience in Python and React",
        recipient_name="John Smith",
        recipient_role="CTO",
        company_website_url="https://example.com",
        company_tone=EmailTone.PROFESSIONAL,
        email_goal="Schedule a meeting",
        pain_point="Scaling engineering team",
        sender_name="Jane Doe",
        sender_email="jane@example.com"
    )
```

**Location:**
- Global fixtures: `backend/tests/conftest.py`
- Feature-specific fixtures: Top of relevant test file (e.g., `backend/tests/test_email_service.py`)
- Fixture scope: `session` for expensive setup, `function` (default) for test isolation

**Faker usage:**
- faker (^20.0.3) available in dependencies for generating realistic test data
- Not heavily used in current tests; consider for larger test suites

## Coverage

**Requirements:**
- Minimum 70% coverage enforced via `--cov-fail-under=70` in pytest.ini
- Coverage report formats:
  - HTML: `htmlcov/` directory (generated by `--cov-report=html`)
  - Terminal: `--cov-report=term-missing` shows missing lines

**View Coverage:**
```bash
pytest --cov=app --cov-report=html     # Generate HTML report
pytest --cov=app --cov-report=term     # Show in terminal
open htmlcov/index.html                 # View HTML report (macOS)
```

## Test Types

**Unit Tests:**
- Scope: Individual functions, methods, or classes
- Approach: Isolated from external dependencies (mocked)
- Example: `test_generate_cold_email()` tests email generation with mocked LLM
- Location: `backend/tests/test_*.py` and `backend/tests/unit/test_db/test_schema.py`
- Marked with `@pytest.mark.unit` for filtering

**Integration Tests:**
- Scope: Multiple components working together
- Approach: May use real database (SQLite in memory) or mock some layers
- Example: `backend/tests/unit/test_db/test_schema.py` tests SQLAlchemy models with in-memory SQLite
- Marked with `@pytest.mark.integration` for filtering
- Currently limited; focused on database schema validation

**E2E Tests:**
- Framework: Not used
- Approach: Would test full request/response flow
- Status: No E2E tests currently implemented; could use pytest with test client

## Common Patterns

**Async Testing:**
```python
# Pattern: Mark test with @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_generate_cold_email(email_service, sample_email_request):
    """Test cold email generation"""
    company_text = "Example Corp..."
    result = await email_service.generate_cold_email(sample_email_request, company_text)
    assert result.email_id is not None

# Pattern: Using asyncio.gather in tests
@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test parallel task execution"""
    task1 = email_service._analyze_company_tone(text, tone)
    task2 = email_service._synthesize_value_props(resume, company)
    result1, result2 = await asyncio.gather(task1, task2)
    assert result1 is not None
    assert result2 is not None
```

**Error Testing:**
```python
# Pattern: Expecting specific exceptions
def test_missing_api_key(monkeypatch):
    """Test that missing API key raises error"""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    from backend.app.db.connection import get_supabase_client
    with pytest.raises(ValueError, match="SUPABASE_URL and SUPABASE_KEY"):
        get_supabase_client()

# Pattern: Catching ServiceError subclasses
@pytest.mark.asyncio
async def test_rate_limit_error(email_service):
    """Test rate limit error handling"""
    with patch.object(email_service.llm_client, 'generate', new_callable=AsyncMock) as mock:
        mock.side_effect = RateLimitError("Rate limited", "RATE_LIMIT", {})
        with pytest.raises(RateLimitError):
            await email_service.generate_cold_email(request, text)
```

**Parametrized Tests:**
```python
# Pattern: Test multiple cases with @pytest.mark.parametrize
@pytest.mark.parametrize(
    "model",
    [User, Profile, Job, Application, Match, Document, AgentAction, AgentOutput],
    ids=lambda m: m.__tablename__,
)
def test_id_column_is_uuid(self, model):
    """Each model's id column uses UUID type."""
    id_col = model.__table__.columns["id"]
    assert id_col.primary_key
    col_type_name = type(id_col.type).__name__
    assert col_type_name in ("UUID", "Uuid")
```

## Pytest Configuration

**File:** `backend/pytest.ini`

**Key Settings:**
- Test discovery: `python_files = test_*.py`, `python_classes = Test*`, `python_functions = test_*`
- Test paths: `testpaths = tests`
- Async mode: `asyncio_mode = auto` (async tests auto-detected)
- Coverage: `--cov=app --cov-report=html --cov-report=term-missing --cov-fail-under=70`
- Markers: `unit`, `integration`, `performance`, `slow`, `requires_api`
- Logging: `log_cli = true`, `log_cli_level = INFO`
- Timeout: `timeout = 30` seconds per test
- Environment: `TESTING=true`, `OPENAI_API_KEY=test_key`, `DATABASE_URL=sqlite:///test.db`

## Database Schema Testing

**Approach:**
- Tests validate SQLAlchemy ORM models mirror Supabase schema
- Uses in-memory SQLite for model structure validation (not table creation)
- Tests check:
  - All tables present in metadata
  - All columns and types correct
  - Foreign key relationships established
  - UUID primary keys with defaults
  - Timestamp columns with proper defaults
  - Soft delete columns on user-facing tables
  - Enum values match specification

**Example test class:**
```python
class TestCoreTablesExist:
    """AC1: All foundational tables exist with proper relationships."""

    EXPECTED_TABLES = ["users", "profiles", "jobs", "applications", ...]

    def test_all_tables_registered_in_metadata(self):
        """All 8 core tables are registered in SQLAlchemy metadata."""
        table_names = list(Base.metadata.tables.keys())
        for expected in self.EXPECTED_TABLES:
            assert expected in table_names
```

## Frontend Testing

**Framework:**
- React Testing Library (^14.1.2)
- Jest (via react-scripts 5.0.1)
- @testing-library/user-event (^14.5.1)

**Run Commands:**
```bash
npm test              # Run tests in watch mode
npm test -- --coverage  # Run with coverage
```

**Patterns:**
- Test user interactions, not implementation details
- Use `screen.getByRole()`, `screen.getByText()` for queries
- Simulate user events with `userEvent.type()`, `userEvent.click()`
- Mock API calls with `fetch` or axios interceptors

**Note:** Current tests focus on backend; frontend testing patterns not heavily established.

---

*Testing analysis: 2026-01-30*
