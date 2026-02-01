"""
Unit tests for the learned preferences API endpoints.

Tests GET /preferences/learned and PATCH /preferences/learned/{id}
with mocked database session and dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeLearnedPrefStatus:
    """Mimic LearnedPreferenceStatus enum for tests."""
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"

    def __init__(self, value: str):
        self._value = value

    @property
    def value(self):
        return self._value

    def __eq__(self, other):
        if isinstance(other, _FakeLearnedPrefStatus):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return NotImplemented

    def __hash__(self):
        return hash(self._value)


def _make_user(user_id=None):
    return SimpleNamespace(
        id=user_id or uuid4(),
        clerk_id="clerk_test_123",
        email="test@example.com",
    )


def _make_learned_pref(user_id=None, pref_id=None, pattern_type="company",
                       pattern_value="Acme Corp", confidence=0.80,
                       occurrences=5, status=None):
    if status is None:
        status = _FakeLearnedPrefStatus("pending")
    return SimpleNamespace(
        id=pref_id or uuid4(),
        user_id=user_id or uuid4(),
        pattern_type=pattern_type,
        pattern_value=pattern_value,
        confidence=Decimal(str(confidence)),
        occurrences=occurrences,
        status=status,
        created_at=datetime(2025, 7, 1, 10, 0, 0, tzinfo=timezone.utc),
        deleted_at=None,
        deleted_by=None,
        deletion_reason=None,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_app():
    from app.api.v1.learned_preferences import router, ensure_user_exists
    from app.db.session import get_db
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    user = _make_user()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def override_user():
        return user

    app.dependency_overrides[ensure_user_exists] = override_user
    return app, user, TestClient(app), ensure_user_exists, get_db


# ---------------------------------------------------------------------------
# Tests: GET /preferences/learned
# ---------------------------------------------------------------------------

class TestGetLearnedPreferences:
    def test_returns_learned_preferences(self, test_app):
        app, user, client, ensure_user_exists_dep, get_db = test_app

        pref1 = _make_learned_pref(user_id=user.id, pattern_type="company",
                                   pattern_value="BadCo", confidence=0.75)
        pref2 = _make_learned_pref(user_id=user.id, pattern_type="location",
                                   pattern_value="NYC", confidence=0.85)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [pref1, pref2]
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db
        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/preferences/learned")
        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 2
        assert data["data"][0]["pattern_type"] == "company"
        assert data["data"][0]["pattern_value"] == "BadCo"
        assert data["data"][0]["confidence"] == 0.75
        assert data["data"][0]["status"] == "pending"
        assert data["data"][1]["pattern_type"] == "location"

    def test_returns_empty_list_when_no_prefs(self, test_app):
        app, user, client, ensure_user_exists_dep, get_db = test_app

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db
        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/preferences/learned")
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []


# ---------------------------------------------------------------------------
# Tests: PATCH /preferences/learned/{id}
# ---------------------------------------------------------------------------

class TestUpdateLearnedPreferenceStatus:
    def test_acknowledge_preference(self, test_app):
        app, user, client, ensure_user_exists_dep, get_db = test_app

        pref = _make_learned_pref(user_id=user.id)
        pref_id = str(pref.id)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = pref
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        async def mock_refresh(obj):
            obj.status = _FakeLearnedPrefStatus("acknowledged")
        mock_db.refresh = mock_refresh

        async def override_db():
            yield mock_db
        app.dependency_overrides[get_db] = override_db

        response = client.patch(
            f"/api/v1/preferences/learned/{pref_id}",
            json={"status": "acknowledged"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "acknowledged"

    def test_reject_preference(self, test_app):
        app, user, client, ensure_user_exists_dep, get_db = test_app

        pref = _make_learned_pref(user_id=user.id)
        pref_id = str(pref.id)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = pref
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        async def mock_refresh(obj):
            obj.status = _FakeLearnedPrefStatus("rejected")
        mock_db.refresh = mock_refresh

        async def override_db():
            yield mock_db
        app.dependency_overrides[get_db] = override_db

        response = client.patch(
            f"/api/v1/preferences/learned/{pref_id}",
            json={"status": "rejected"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        # Verify soft-delete fields were set
        assert pref.deleted_at is not None
        assert pref.deleted_by == user.id
        assert pref.deletion_reason == "User rejected learned preference"

    def test_nonexistent_preference_returns_404(self, test_app):
        app, user, client, ensure_user_exists_dep, get_db = test_app

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db
        app.dependency_overrides[get_db] = override_db

        pref_id = str(uuid4())
        response = client.patch(
            f"/api/v1/preferences/learned/{pref_id}",
            json={"status": "acknowledged"},
        )
        assert response.status_code == 404

    def test_invalid_status_returns_422(self, test_app):
        app, user, client, ensure_user_exists_dep, get_db = test_app

        mock_db = AsyncMock()
        async def override_db():
            yield mock_db
        app.dependency_overrides[get_db] = override_db

        pref_id = str(uuid4())
        response = client.patch(
            f"/api/v1/preferences/learned/{pref_id}",
            json={"status": "invalid"},
        )
        assert response.status_code == 422
