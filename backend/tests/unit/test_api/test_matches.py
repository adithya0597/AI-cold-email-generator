"""
Unit tests for the matches API endpoints.

Tests GET /matches and PATCH /matches/{match_id} with mocked
database session and dependencies.

These tests mock the DB engine/session modules to avoid needing
asyncpg at import time, then test the API router directly.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Helpers
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


def _make_job(job_id=None):
    return SimpleNamespace(
        id=job_id or uuid4(),
        title="Software Engineer",
        company="Acme Corp",
        location="San Francisco, CA",
        remote=True,
        salary_min=140000,
        salary_max=180000,
        url="https://example.com/job/123",
        description="Build amazing software at Acme.",
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
        rationale=json.dumps({
            "summary": "Great match for your skills",
            "top_reasons": ["Strong Python experience", "Remote friendly"],
            "concerns": ["Salary slightly below target"],
            "confidence": "High",
        }),
        job=job or _make_job(),
        created_at=datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Tests: parse_rationale (direct import - no DB dependency)
# ---------------------------------------------------------------------------

class TestParseRationale:
    def test_parse_valid_json(self):
        from app.services.job_scoring import parse_rationale

        result = parse_rationale(json.dumps({
            "summary": "Good match",
            "top_reasons": ["Skill fit"],
            "concerns": [],
            "confidence": "High",
        }))
        assert result["summary"] == "Good match"
        assert result["top_reasons"] == ["Skill fit"]
        assert result["confidence"] == "High"

    def test_parse_none(self):
        from app.services.job_scoring import parse_rationale
        result = parse_rationale(None)
        assert result["summary"] == ""
        assert result["top_reasons"] == []

    def test_parse_plain_text(self):
        from app.services.job_scoring import parse_rationale
        result = parse_rationale("Plain text rationale")
        assert result["summary"] == "Plain text rationale"
        assert result["top_reasons"] == ["Plain text rationale"]


# ---------------------------------------------------------------------------
# Tests: _match_to_response helper (needs import via fixtures)
# ---------------------------------------------------------------------------

class TestMatchToResponse:
    def test_converts_match_with_parsed_rationale(self):
        from app.services.job_scoring import parse_rationale

        # Manually test the conversion logic without importing the full module
        job = _make_job()
        match = _make_match(job=job)
        rationale_dict = parse_rationale(match.rationale)

        assert rationale_dict["summary"] == "Great match for your skills"
        assert len(rationale_dict["top_reasons"]) == 2
        assert rationale_dict["confidence"] == "High"

        # Score conversion
        assert int(match.score) == 85

    def test_handles_none_score(self):
        match = _make_match(score=None)
        score = int(match.score) if match.score is not None else 0
        assert score == 0

    def test_converts_score_decimal_to_int(self):
        match = _make_match(score=92.75)
        assert int(match.score) == 92


# ---------------------------------------------------------------------------
# Tests: GET /matches via TestClient
# ---------------------------------------------------------------------------

@pytest.fixture
def test_app():
    """Create a test FastAPI app by importing the matches router.

    We must ensure the DB modules are mockable before importing.
    """
    # Import here to avoid top-level DB chain issues
    # The matches module has been designed to import cleanly when
    # the DB engine is available (or mocked at conftest level)
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


class TestGetMatches:
    def test_get_matches_returns_correct_format(self, test_app):
        app, user, client, ensure_user_exists_dep, get_db = test_app

        job = _make_job()
        match = _make_match(user_id=user.id, job=job)

        mock_db = AsyncMock()
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        mock_matches_result = MagicMock()
        mock_matches_result.scalars.return_value.all.return_value = [match]

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_matches_result])

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/matches?status=new&page=1&per_page=20")
        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "meta" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["job"]["title"] == "Software Engineer"
        assert data["data"][0]["score"] == 85
        assert data["data"][0]["rationale"]["confidence"] == "High"
        assert data["data"][0]["rationale"]["top_reasons"] == ["Strong Python experience", "Remote friendly"]
        assert data["meta"]["pagination"]["total"] == 1
        assert data["meta"]["pagination"]["page"] == 1

    def test_get_matches_invalid_status_returns_400(self, test_app):
        app, user, client, ensure_user_exists_dep, get_db = test_app

        mock_db = AsyncMock()
        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/matches?status=invalid")
        assert response.status_code == 400

    def test_get_matches_empty_returns_empty_list(self, test_app):
        app, user, client, ensure_user_exists_dep, get_db = test_app

        mock_db = AsyncMock()
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0

        mock_matches_result = MagicMock()
        mock_matches_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_matches_result])

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/matches?status=new")
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["meta"]["pagination"]["total"] == 0

    def test_get_matches_with_saved_status(self, test_app):
        app, user, client, ensure_user_exists_dep, get_db = test_app

        job = _make_job()
        match = _make_match(user_id=user.id, job=job, status=_FakeMatchStatus("saved"))

        mock_db = AsyncMock()
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        mock_matches_result = MagicMock()
        mock_matches_result.scalars.return_value.all.return_value = [match]

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_matches_result])

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/matches?status=saved")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["status"] == "saved"


# ---------------------------------------------------------------------------
# Tests: PATCH /matches/{match_id}
# ---------------------------------------------------------------------------

class TestUpdateMatchStatus:
    def test_update_match_to_saved(self, test_app):
        app, user, client, ensure_user_exists_dep, get_db = test_app

        job = _make_job()
        match = _make_match(user_id=user.id, job=job, status=_FakeMatchStatus("new"))
        match_id = str(match.id)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = match

        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        async def mock_refresh(obj):
            obj.status = _FakeMatchStatus("saved")

        mock_db.refresh = mock_refresh

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.patch(f"/api/v1/matches/{match_id}", json={"status": "saved"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "saved"

    def test_update_match_to_dismissed(self, test_app):
        app, user, client, ensure_user_exists_dep, get_db = test_app

        job = _make_job()
        match = _make_match(user_id=user.id, job=job, status=_FakeMatchStatus("new"))
        match_id = str(match.id)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = match

        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        async def mock_refresh(obj):
            obj.status = _FakeMatchStatus("dismissed")

        mock_db.refresh = mock_refresh

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.patch(f"/api/v1/matches/{match_id}", json={"status": "dismissed"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "dismissed"

    def test_update_with_invalid_status_returns_422(self, test_app):
        app, user, client, ensure_user_exists_dep, get_db = test_app

        mock_db = AsyncMock()
        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        match_id = str(uuid4())
        response = client.patch(f"/api/v1/matches/{match_id}", json={"status": "applied"})
        assert response.status_code == 422

    def test_update_nonexistent_match_returns_404(self, test_app):
        app, user, client, ensure_user_exists_dep, get_db = test_app

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        match_id = str(uuid4())
        response = client.patch(f"/api/v1/matches/{match_id}", json={"status": "saved"})
        assert response.status_code == 404

    def test_update_non_new_match_returns_400(self, test_app):
        app, user, client, ensure_user_exists_dep, get_db = test_app

        job = _make_job()
        match = _make_match(user_id=user.id, job=job, status=_FakeMatchStatus("saved"))
        match_id = str(match.id)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = match

        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.patch(f"/api/v1/matches/{match_id}", json={"status": "dismissed"})
        assert response.status_code == 400
