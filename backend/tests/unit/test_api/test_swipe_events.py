"""
Unit tests for swipe event recording on match status update.

Verifies that saving/dismissing a match creates a SwipeEvent with
correctly denormalized job attributes.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Helpers (reused from test_matches.py patterns)
# ---------------------------------------------------------------------------

class _FakeMatchStatus:
    """Mimic MatchStatus enum for tests."""
    NEW = "new"
    SAVED = "saved"
    DISMISSED = "dismissed"

    def __init__(self, value: str):
        self._value = value

    @property
    def value(self):
        return self._value

    def __eq__(self, other):
        if isinstance(other, _FakeMatchStatus):
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


def _make_job(job_id=None, **overrides):
    defaults = dict(
        id=job_id or uuid4(),
        title="Software Engineer",
        company="Acme Corp",
        location="San Francisco, CA",
        remote=True,
        salary_min=140000,
        salary_max=180000,
        url="https://example.com/job/123",
        description="Build amazing software at Acme.",
        employment_type="Full-time",
        h1b_sponsor_status=None,
        posted_at=None,
        source="indeed",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_match(user_id=None, job=None, match_id=None, status=None, score=85.50):
    if status is None:
        status = _FakeMatchStatus("new")
    j = job or _make_job()
    return SimpleNamespace(
        id=match_id or uuid4(),
        user_id=user_id or uuid4(),
        job_id=j.id,
        score=score,
        status=status,
        rationale=json.dumps({
            "summary": "Great match",
            "top_reasons": ["Good fit"],
            "concerns": [],
            "confidence": "High",
        }),
        job=j,
        created_at=datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_app():
    from app.api.v1.matches import router, ensure_user_exists
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
# Tests: SwipeEvent recording
# ---------------------------------------------------------------------------

class TestSwipeEventRecording:
    def test_save_creates_swipe_event_with_job_attrs(self, test_app):
        app, user, client, ensure_user_exists_dep, get_db = test_app

        job = _make_job(company="BigTech Inc", location="NYC", remote=False,
                        salary_min=100000, salary_max=150000,
                        employment_type="Contract")
        match = _make_match(user_id=user.id, job=job, status=_FakeMatchStatus("new"))
        match_id = str(match.id)

        added_objects = []

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = match
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        original_add = mock_db.add
        def capture_add(obj):
            added_objects.append(obj)
            return original_add(obj)
        mock_db.add = capture_add

        async def mock_refresh(obj):
            obj.status = _FakeMatchStatus("saved")
        mock_db.refresh = mock_refresh

        async def override_db():
            yield mock_db
        app.dependency_overrides[get_db] = override_db

        response = client.patch(f"/api/v1/matches/{match_id}", json={"status": "saved"})
        assert response.status_code == 200

        # Verify SwipeEvent was added
        assert len(added_objects) == 1
        swipe = added_objects[0]
        assert swipe.user_id == user.id
        assert swipe.match_id == match.id
        assert swipe.action == "saved"
        assert swipe.job_company == "BigTech Inc"
        assert swipe.job_location == "NYC"
        assert swipe.job_remote is False
        assert swipe.job_salary_min == 100000
        assert swipe.job_salary_max == 150000
        assert swipe.job_employment_type == "Contract"

    def test_dismiss_creates_swipe_event(self, test_app):
        app, user, client, ensure_user_exists_dep, get_db = test_app

        job = _make_job(company="SmallCo")
        match = _make_match(user_id=user.id, job=job, status=_FakeMatchStatus("new"))
        match_id = str(match.id)

        added_objects = []

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = match
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        original_add = mock_db.add
        def capture_add(obj):
            added_objects.append(obj)
            return original_add(obj)
        mock_db.add = capture_add

        async def mock_refresh(obj):
            obj.status = _FakeMatchStatus("dismissed")
        mock_db.refresh = mock_refresh

        async def override_db():
            yield mock_db
        app.dependency_overrides[get_db] = override_db

        response = client.patch(f"/api/v1/matches/{match_id}", json={"status": "dismissed"})
        assert response.status_code == 200

        assert len(added_objects) == 1
        swipe = added_objects[0]
        assert swipe.action == "dismissed"
        assert swipe.job_company == "SmallCo"

    def test_swipe_event_captures_null_job_fields(self, test_app):
        app, user, client, ensure_user_exists_dep, get_db = test_app

        job = _make_job(location=None, salary_min=None, salary_max=None,
                        remote=None, employment_type=None)
        match = _make_match(user_id=user.id, job=job, status=_FakeMatchStatus("new"))
        match_id = str(match.id)

        added_objects = []

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = match
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        original_add = mock_db.add
        def capture_add(obj):
            added_objects.append(obj)
            return original_add(obj)
        mock_db.add = capture_add

        async def mock_refresh(obj):
            obj.status = _FakeMatchStatus("saved")
        mock_db.refresh = mock_refresh

        async def override_db():
            yield mock_db
        app.dependency_overrides[get_db] = override_db

        response = client.patch(f"/api/v1/matches/{match_id}", json={"status": "saved"})
        assert response.status_code == 200

        swipe = added_objects[0]
        assert swipe.job_location is None
        assert swipe.job_salary_min is None
        assert swipe.job_salary_max is None
        assert swipe.job_remote is None
        assert swipe.job_employment_type is None
