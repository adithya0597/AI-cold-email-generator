"""
Tests for LLM job scoring service.

Mocks OpenAIClient and cost_tracker to avoid real API calls.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.job_scoring import ScoringResult, score_job_with_llm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_job(**kwargs) -> SimpleNamespace:
    """Create a mock Job object with default values."""
    defaults = {
        "id": "job-id-1",
        "title": "Software Engineer",
        "company": "Acme Corp",
        "description": "Python, React, PostgreSQL experience needed. Senior role.",
        "location": "San Francisco, CA",
        "salary_min": 140000,
        "salary_max": 180000,
        "employment_type": "FULLTIME",
        "remote": True,
        "source": "jsearch",
        "source_id": "j1",
        "url": "https://acme.com/apply/1",
        "raw_data": {},
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


TEST_PREFERENCES = {
    "target_titles": ["Software Engineer", "Backend Engineer"],
    "target_locations": ["San Francisco", "New York"],
    "salary_minimum": 120000,
    "salary_target": 180000,
    "seniority_levels": ["senior"],
    "min_company_size": 50,
}

TEST_PROFILE = {
    "skills": ["Python", "React", "PostgreSQL", "FastAPI"],
}

VALID_LLM_RESPONSE = {
    "score": 85,
    "rationale": "Great match for skills and location",
    "breakdown": {
        "title_match": 90,
        "skills_overlap": 80,
        "location_match": 95,
        "salary_match": 85,
        "company_size": 70,
        "seniority_match": 80,
    },
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestScoreJobWithLLM:
    """Tests for score_job_with_llm function."""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        """LLM returns valid score JSON, parsed to ScoringResult."""
        mock_client_instance = AsyncMock()
        mock_client_instance.generate_json = AsyncMock(return_value=VALID_LLM_RESPONSE)

        mock_client_cls = MagicMock(return_value=mock_client_instance)

        with patch("app.core.llm_clients.OpenAIClient", mock_client_cls):
            result = await score_job_with_llm(
                _make_job(), TEST_PREFERENCES, TEST_PROFILE, user_id=None
            )

        assert isinstance(result, ScoringResult)
        assert result.score == 85
        assert result.rationale == "Great match for skills and location"
        assert result.used_llm is True
        assert result.model_used == "gpt-3.5-turbo"
        assert result.breakdown["title_match"] == 90
        assert result.breakdown["skills_overlap"] == 80

    @pytest.mark.asyncio
    async def test_llm_failure_fallback(self):
        """LLM raises exception, falls back to heuristic score."""
        mock_client_instance = AsyncMock()
        mock_client_instance.generate_json = AsyncMock(
            side_effect=Exception("API timeout")
        )
        mock_client_cls = MagicMock(return_value=mock_client_instance)

        with patch("app.core.llm_clients.OpenAIClient", mock_client_cls):
            result = await score_job_with_llm(
                _make_job(),
                TEST_PREFERENCES,
                TEST_PROFILE,
                heuristic_score=65,
            )

        assert isinstance(result, ScoringResult)
        assert result.used_llm is False
        assert result.score == 65
        assert result.model_used == "heuristic"

    @pytest.mark.asyncio
    async def test_invalid_score_range(self):
        """LLM returns score > 100, clamped to 100."""
        mock_client_instance = AsyncMock()
        mock_client_instance.generate_json = AsyncMock(
            return_value={
                "score": 150,
                "rationale": "Perfect!",
                "breakdown": {
                    "title_match": 100,
                    "skills_overlap": 100,
                    "location_match": 100,
                    "salary_match": 100,
                    "company_size": 100,
                    "seniority_match": 100,
                },
            }
        )
        mock_client_cls = MagicMock(return_value=mock_client_instance)

        with patch("app.core.llm_clients.OpenAIClient", mock_client_cls):
            result = await score_job_with_llm(
                _make_job(), TEST_PREFERENCES, TEST_PROFILE
            )

        assert result.score == 100  # clamped
        assert result.used_llm is True

    @pytest.mark.asyncio
    async def test_missing_fields(self):
        """LLM returns empty dict, falls back gracefully."""
        mock_client_instance = AsyncMock()
        mock_client_instance.generate_json = AsyncMock(return_value={})
        mock_client_cls = MagicMock(return_value=mock_client_instance)

        with patch("app.core.llm_clients.OpenAIClient", mock_client_cls):
            result = await score_job_with_llm(
                _make_job(),
                TEST_PREFERENCES,
                TEST_PROFILE,
                heuristic_score=55,
            )

        assert result.used_llm is False
        assert result.score == 55

    @pytest.mark.asyncio
    async def test_cost_tracking(self):
        """Verify track_llm_cost called with correct model name."""
        mock_client_instance = AsyncMock()
        mock_client_instance.generate_json = AsyncMock(return_value=VALID_LLM_RESPONSE)
        mock_client_cls = MagicMock(return_value=mock_client_instance)

        mock_track = AsyncMock()
        mock_cost_module = MagicMock()
        mock_cost_module.track_llm_cost = mock_track

        with patch("app.core.llm_clients.OpenAIClient", mock_client_cls), \
             patch.dict(sys.modules, {"app.observability.cost_tracker": mock_cost_module}):
            result = await score_job_with_llm(
                _make_job(),
                TEST_PREFERENCES,
                TEST_PROFILE,
                user_id="user-123",
            )

        assert result.used_llm is True
        mock_track.assert_awaited_once()
        call_args = mock_track.call_args
        assert call_args[0][0] == "user-123"  # user_id
        assert call_args[0][1] == "gpt-3.5-turbo"  # model
        assert isinstance(call_args[0][2], int)  # input_tokens
        assert isinstance(call_args[0][3], int)  # output_tokens

    @pytest.mark.asyncio
    async def test_no_user_id_skips_cost_tracking(self):
        """Call without user_id does not invoke track_llm_cost."""
        mock_client_instance = AsyncMock()
        mock_client_instance.generate_json = AsyncMock(return_value=VALID_LLM_RESPONSE)
        mock_client_cls = MagicMock(return_value=mock_client_instance)

        mock_track = AsyncMock()
        mock_cost_module = MagicMock()
        mock_cost_module.track_llm_cost = mock_track

        with patch("app.core.llm_clients.OpenAIClient", mock_client_cls), \
             patch.dict(sys.modules, {"app.observability.cost_tracker": mock_cost_module}):
            result = await score_job_with_llm(
                _make_job(),
                TEST_PREFERENCES,
                TEST_PROFILE,
                user_id=None,
            )

        assert result.used_llm is True
        mock_track.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_negative_score_clamped(self):
        """LLM returns negative score, clamped to 0."""
        mock_client_instance = AsyncMock()
        mock_client_instance.generate_json = AsyncMock(
            return_value={"score": -10, "rationale": "Bad", "breakdown": {}}
        )
        mock_client_cls = MagicMock(return_value=mock_client_instance)

        with patch("app.core.llm_clients.OpenAIClient", mock_client_cls):
            result = await score_job_with_llm(
                _make_job(), TEST_PREFERENCES, TEST_PROFILE
            )

        assert result.score == 0
        assert result.used_llm is True
