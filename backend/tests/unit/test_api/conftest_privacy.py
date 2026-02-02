"""Shared test fixtures for privacy endpoint tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.privacy import router
from app.auth.clerk import get_current_user_id

# Shared app instance with dependency overrides
privacy_app = FastAPI()
privacy_app.include_router(router, prefix="/api/v1")
privacy_app.dependency_overrides[get_current_user_id] = lambda: "test-user-123"


def mock_session_cm():
    """Create a mock async session context manager."""
    mock_sess = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_sess)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm, mock_sess
