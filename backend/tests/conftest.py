"""
Pytest configuration and shared fixtures for the JobPilot test suite.

Provides:
- Async event loop (session-scoped) for async tests
- HTTPX AsyncClient wired to the FastAPI app for integration tests
- Environment variable mocking helpers
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure backend package is importable when running from repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


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
