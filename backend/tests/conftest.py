"""
Pytest configuration and shared fixtures for the JobPilot test suite.

Provides:
- Async event loop (session-scoped) for async tests
- HTTPX AsyncClient wired to the FastAPI app for integration tests
- Environment variable mocking helpers
- Mock user fixtures for each autonomy tier (L0-L3)
- Mock Redis fixtures for brake state testing
- VCR.py cassette configuration for deterministic LLM tests
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure backend package is importable when running from repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create a single event loop for the entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client bound to the FastAPI application.

    Uses ``httpx.AsyncClient`` with ``ASGITransport`` so requests never
    hit the network -- they are dispatched directly to the ASGI app.
    """
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables commonly needed by tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_anthropic_key")
    monkeypatch.setenv("TRACKING_BASE_URL", "http://localhost:8000/api/track")
    monkeypatch.setenv("APP_ENV", "test")


# ---------------------------------------------------------------------------
# User tier fixtures -- mock _get_user_tier to return each autonomy level
# ---------------------------------------------------------------------------

_TEST_USER_ID = "test-user-00000000-0000-0000-0000-000000000001"


@pytest.fixture
def test_user_id() -> str:
    """Standard test user ID used across agent tests."""
    return _TEST_USER_ID


@pytest.fixture
def mock_user_l0():
    """Patch _get_user_tier to return 'l0' (suggestions only)."""
    with patch(
        "app.agents.tier_enforcer._get_user_tier",
        new_callable=AsyncMock,
        return_value="l0",
    ) as m:
        yield m


@pytest.fixture
def mock_user_l1():
    """Patch _get_user_tier to return 'l1' (read-only / drafts)."""
    with patch(
        "app.agents.tier_enforcer._get_user_tier",
        new_callable=AsyncMock,
        return_value="l1",
    ) as m:
        yield m


@pytest.fixture
def mock_user_l2():
    """Patch _get_user_tier to return 'l2' (supervised -- writes queue for approval)."""
    with patch(
        "app.agents.tier_enforcer._get_user_tier",
        new_callable=AsyncMock,
        return_value="l2",
    ) as m:
        yield m


@pytest.fixture
def mock_user_l3():
    """Patch _get_user_tier to return 'l3' (autonomous)."""
    with patch(
        "app.agents.tier_enforcer._get_user_tier",
        new_callable=AsyncMock,
        return_value="l3",
    ) as m:
        yield m


# ---------------------------------------------------------------------------
# Redis brake fixtures -- mock check_brake / check_brake_or_raise
# ---------------------------------------------------------------------------


@pytest.fixture
def redis_brake_active():
    """Patch check_brake to return True (brake is ON)."""
    with patch(
        "app.agents.brake.check_brake",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_check:
        with patch(
            "app.agents.brake.check_brake_or_raise",
            new_callable=AsyncMock,
            side_effect=_raise_brake_active,
        ) as mock_raise:
            yield {"check_brake": mock_check, "check_brake_or_raise": mock_raise}


async def _raise_brake_active(user_id: str):
    from app.agents.base import BrakeActive

    raise BrakeActive(f"Emergency brake active for {user_id}")


@pytest.fixture
def redis_brake_inactive():
    """Patch check_brake to return False (brake is OFF)."""
    with patch(
        "app.agents.brake.check_brake",
        new_callable=AsyncMock,
        return_value=False,
    ) as mock_check:
        with patch(
            "app.agents.brake.check_brake_or_raise",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_raise:
            yield {"check_brake": mock_check, "check_brake_or_raise": mock_raise}


# ---------------------------------------------------------------------------
# Mock Redis client for brake module internal tests
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_redis():
    """Provide a mock async Redis client for brake / briefing tests.

    The mock supports common Redis operations:
    set, get, exists, delete, hset, hgetall, publish, aclose.
    """
    redis_mock = AsyncMock()
    redis_mock.exists = AsyncMock(return_value=0)
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.hset = AsyncMock(return_value=1)
    redis_mock.hgetall = AsyncMock(return_value={})
    redis_mock.publish = AsyncMock(return_value=1)
    redis_mock.aclose = AsyncMock()
    return redis_mock


# ---------------------------------------------------------------------------
# VCR.py cassette configuration for deterministic LLM testing
# ---------------------------------------------------------------------------


@pytest.fixture
def vcr_config():
    """VCR.py configuration for recording/replaying HTTP interactions.

    Cassettes are stored in ``backend/tests/cassettes/``.
    Sensitive headers (Authorization, API keys) are filtered out.
    Default mode is ``none`` -- cassettes must exist.  Switch to
    ``record_mode="once"`` when recording new cassettes against a real API.
    """
    return {
        "filter_headers": ["authorization", "x-api-key", "api-key"],
        "record_mode": "none",
        "cassette_library_dir": os.path.join(
            os.path.dirname(__file__), "cassettes"
        ),
        "decode_compressed_response": True,
    }
