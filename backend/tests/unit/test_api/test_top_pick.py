"""
Unit tests for the GET /matches/top-pick endpoint.

Tests the top-pick selection logic: highest-scoring new match returned,
204 when none exist, non-new statuses excluded.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Helpers (same pattern as test_matches.py)
# ---------------------------------------------------------------------------


class _FakeMatchStatus:
    """Mimic MatchStatus enum for tests."""

    NEW = "new"
    SAVED = "saved"
    DISMISSED = "dismissed"
    APPLIED = "applied"

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


def _make_job(job_id=None, title="Software Engineer", company="Acme Corp"):
    return SimpleNamespace(
        id=job_id or uuid4(),
        title=title,
        company=company,
        location="San Francisco, CA",
        remote=True,
        salary_min=140000,
        salary_max=180000,
        url="https://example.com/job/123",
        description="Build amazing software.",
        employment_type=None,
        h1b_sponsor_status=None,
        posted_at=None,
        source="indeed",
    )


def _make_match(user_id=None, job=None, match_id=None, status=None, score=85.50):
    if status is None:
        status = _FakeMatchStatus("new")
    return SimpleNamespace(
        id=match_id or uuid4(),
        user_id=user_id or uuid4(),
        job_id=(job or _make_job()).id,
        score=score,
        status=status,
        rationale=json.dumps(
            {
                "summary": "Great match for your skills",
                "top_reasons": ["Strong Python experience", "Remote friendly"],
                "concerns": ["Salary slightly below target"],
                "confidence": "High",
            }
        ),
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
# Tests: GET /matches/top-pick
# ---------------------------------------------------------------------------


class TestGetTopPick:
    def test_top_pick_returns_highest_scoring_new_match(self, test_app):
        app, user, client, _ensure, get_db = test_app

        job_low = _make_job(title="Junior Dev", company="SmallCo")
        job_high = _make_job(title="Senior Engineer", company="BigCorp")
        match_high = _make_match(user_id=user.id, job=job_high, score=95.0)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        # The query returns the highest match (ORDER BY score DESC LIMIT 1)
        mock_result.scalar_one_or_none.return_value = match_high

        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/matches/top-pick")
        assert response.status_code == 200

        data = response.json()
        assert data["score"] == 95
        assert data["job"]["title"] == "Senior Engineer"
        assert data["job"]["company"] == "BigCorp"
        assert data["status"] == "new"
        assert data["rationale"]["summary"] == "Great match for your skills"
        assert len(data["rationale"]["top_reasons"]) == 2

    def test_top_pick_returns_204_when_no_new_matches(self, test_app):
        app, user, client, _ensure, get_db = test_app

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/matches/top-pick")
        assert response.status_code == 204
        assert response.content == b""

    def test_top_pick_excludes_non_new_matches(self, test_app):
        """When all matches are saved/dismissed, the query returns None -> 204."""
        app, user, client, _ensure, get_db = test_app

        mock_db = AsyncMock()
        mock_result = MagicMock()
        # The DB filters status='new', so saved matches are excluded
        mock_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/matches/top-pick")
        assert response.status_code == 204
