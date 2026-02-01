"""
Unit tests for the auth sync endpoint POST /api/v1/auth/sync.

Tests user creation (new) and lookup (returning) with mocked
database session and auth dependencies.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(clerk_id="clerk_test_123", user_id=None, email="test@example.com", tier="free"):
    return SimpleNamespace(
        id=user_id or uuid4(),
        clerk_id=clerk_id,
        email=email,
        tier=SimpleNamespace(value=tier),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_app():
    """Create a test FastAPI app with the auth router and overridable deps."""
    from app.api.v1.auth import router
    from app.auth.clerk import get_current_user_id
    from app.db.session import get_db

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    return app, TestClient(app), get_current_user_id, get_db


# ---------------------------------------------------------------------------
# Tests: POST /api/v1/auth/sync
# ---------------------------------------------------------------------------

class TestSyncNewUser:
    """When clerk_id is not found in the database, a new user is created."""

    def test_creates_new_user_returns_is_new_true(self, test_app):
        app, client, get_current_user_id_dep, get_db_dep = test_app

        clerk_id = "clerk_new_user_001"
        new_user = _make_user(clerk_id=clerk_id)

        # Override auth dependency
        async def override_auth():
            return clerk_id

        app.dependency_overrides[get_current_user_id_dep] = override_auth

        # Mock DB: scalar_one_or_none returns None (user not found),
        # then flush + refresh populate the new user object
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        async def mock_refresh(obj):
            # Simulate DB populating the user after flush
            obj.id = new_user.id
            obj.tier = new_user.tier

        mock_db.refresh = mock_refresh

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db_dep] = override_db

        response = client.post("/api/v1/auth/sync")
        assert response.status_code == 200

        data = response.json()
        assert data["is_new"] is True
        assert data["user"]["clerk_id"] == clerk_id
        assert "id" in data["user"]
        assert "tier" in data["user"]

        # Verify DB add was called
        mock_db.add.assert_called_once()


class TestSyncReturningUser:
    """When clerk_id is found, the existing user is returned."""

    def test_returns_existing_user_is_new_false(self, test_app):
        app, client, get_current_user_id_dep, get_db_dep = test_app

        clerk_id = "clerk_existing_user_001"
        existing_user = _make_user(clerk_id=clerk_id, email="existing@example.com")

        async def override_auth():
            return clerk_id

        app.dependency_overrides[get_current_user_id_dep] = override_auth

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user

        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db_dep] = override_db

        response = client.post("/api/v1/auth/sync")
        assert response.status_code == 200

        data = response.json()
        assert data["is_new"] is False
        assert data["user"]["clerk_id"] == clerk_id
        assert data["user"]["email"] == "existing@example.com"
        assert data["user"]["id"] == str(existing_user.id)


class TestSyncUnauthorized:
    """When no auth token is provided, 401 is returned."""

    def test_returns_401_without_auth(self, test_app):
        app, client, get_current_user_id_dep, get_db_dep = test_app

        # Do NOT override auth -- let the real dependency reject the request.
        # With fastapi-clerk-auth installed, this returns 401.
        # Without it (test env), the fallback _reject_all may produce 401 or 422
        # depending on how FastAPI resolves the dependency chain.
        app.dependency_overrides.clear()

        response = client.post("/api/v1/auth/sync")
        assert response.status_code in (401, 422), (
            f"Expected 401 or 422 for unauthenticated request, got {response.status_code}"
        )


class TestSyncResponseSchema:
    """Verify the response schema includes all required fields."""

    def test_response_has_user_and_is_new(self, test_app):
        app, client, get_current_user_id_dep, get_db_dep = test_app

        clerk_id = "clerk_schema_test"
        user = _make_user(clerk_id=clerk_id, tier="pro")

        async def override_auth():
            return clerk_id

        app.dependency_overrides[get_current_user_id_dep] = override_auth

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user

        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db_dep] = override_db

        response = client.post("/api/v1/auth/sync")
        data = response.json()

        # Schema validation
        assert "user" in data
        assert "is_new" in data
        assert isinstance(data["is_new"], bool)

        user_data = data["user"]
        assert "id" in user_data
        assert "clerk_id" in user_data
        assert "email" in user_data
        assert "tier" in user_data
        assert user_data["tier"] == "pro"
