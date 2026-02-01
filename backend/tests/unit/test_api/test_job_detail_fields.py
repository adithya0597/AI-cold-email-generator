"""
Unit tests for extended job detail fields in match responses.

Verifies that employment_type, h1b_sponsor_status, posted_at, and source
are correctly serialized in the match API responses.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Helpers (same pattern as test_matches.py / test_top_pick.py)
# ---------------------------------------------------------------------------


class _FakeMatchStatus:
    NEW = "new"

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


class _FakeH1BStatus:
    def __init__(self, value: str):
        self._value = value

    @property
    def value(self):
        return self._value


def _make_user(user_id=None):
    return SimpleNamespace(
        id=user_id or uuid4(),
        clerk_id="clerk_test_123",
        email="test@example.com",
    )


def _make_job(
    job_id=None,
    title="Software Engineer",
    company="Acme Corp",
    employment_type=None,
    h1b_sponsor_status=None,
    posted_at=None,
    source="indeed",
):
    return SimpleNamespace(
        id=job_id or uuid4(),
        title=title,
        company=company,
        location="San Francisco, CA",
        remote=True,
        salary_min=140000,
        salary_max=180000,
        url="https://example.com/job/123",
        description="Build amazing software. " * 50,
        employment_type=employment_type,
        h1b_sponsor_status=h1b_sponsor_status,
        posted_at=posted_at,
        source=source,
    )


def _make_match(user_id=None, job=None, match_id=None, score=85.50):
    return SimpleNamespace(
        id=match_id or uuid4(),
        user_id=user_id or uuid4(),
        job_id=(job or _make_job()).id,
        score=score,
        status=_FakeMatchStatus("new"),
        rationale=json.dumps({
            "summary": "Great match",
            "top_reasons": ["Strong skills"],
            "concerns": [],
            "confidence": "High",
        }),
        job=job or _make_job(),
        created_at=datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_app():
    from app.api.v1.matches import ensure_user_exists, router
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
# Tests: Extended job detail fields
# ---------------------------------------------------------------------------


class TestExtendedJobFields:
    def test_match_response_includes_employment_type(self, test_app):
        app, user, client, _ensure, get_db = test_app

        job = _make_job(employment_type="Full-time")
        match = _make_match(user_id=user.id, job=job)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = match
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/matches/top-pick")
        assert response.status_code == 200
        data = response.json()
        assert data["job"]["employment_type"] == "Full-time"

    def test_match_response_includes_h1b_verified(self, test_app):
        app, user, client, _ensure, get_db = test_app

        job = _make_job(h1b_sponsor_status=_FakeH1BStatus("verified"))
        match = _make_match(user_id=user.id, job=job)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = match
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/matches/top-pick")
        assert response.status_code == 200
        data = response.json()
        assert data["job"]["h1b_sponsor_status"] == "verified"

    def test_match_response_includes_posted_at(self, test_app):
        app, user, client, _ensure, get_db = test_app

        posted = datetime(2025, 6, 10, 8, 0, 0, tzinfo=timezone.utc)
        job = _make_job(posted_at=posted)
        match = _make_match(user_id=user.id, job=job)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = match
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/matches/top-pick")
        assert response.status_code == 200
        data = response.json()
        assert data["job"]["posted_at"] == "2025-06-10T08:00:00+00:00"

    def test_match_response_includes_source(self, test_app):
        app, user, client, _ensure, get_db = test_app

        job = _make_job(source="linkedin")
        match = _make_match(user_id=user.id, job=job)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = match
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/matches/top-pick")
        assert response.status_code == 200
        data = response.json()
        assert data["job"]["source"] == "linkedin"

    def test_match_response_null_optional_fields(self, test_app):
        app, user, client, _ensure, get_db = test_app

        job = _make_job(
            employment_type=None,
            h1b_sponsor_status=None,
            posted_at=None,
            source=None,
        )
        match = _make_match(user_id=user.id, job=job)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = match
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/matches/top-pick")
        assert response.status_code == 200
        data = response.json()
        assert data["job"]["employment_type"] is None
        assert data["job"]["h1b_sponsor_status"] is None
        assert data["job"]["posted_at"] is None
        assert data["job"]["source"] is None
