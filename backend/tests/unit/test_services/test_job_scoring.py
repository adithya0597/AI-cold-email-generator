"""
Tests for LLM job scoring service.

Mocks OpenAIClient and cost_tracker to avoid real API calls.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.job_scoring import (
    ScoringResult,
    _derive_confidence,
    build_heuristic_rationale,
    parse_rationale,
    score_job_with_llm,
)


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
    "top_reasons": [
        "Your Python skills match the job requirements",
        "Location in San Francisco matches your preference",
        "Salary range aligns with your target",
    ],
    "concerns": ["Company size information not available"],
    "confidence": "High",
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
        assert len(result.top_reasons) == 3
        assert len(result.concerns) == 1
        assert result.confidence == "High"

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


# ---------------------------------------------------------------------------
# Structured rationale tests (6.1)
# ---------------------------------------------------------------------------


class TestStructuredRationale:
    """Tests for LLM structured rationale fields in ScoringResult."""

    @pytest.mark.asyncio
    async def test_llm_returns_full_structured_rationale(self):
        """LLM returning top_reasons, concerns, confidence populates ScoringResult."""
        llm_response = {
            "score": 85,
            "rationale": "Great match",
            "top_reasons": ["Skill match", "Location match", "Salary fit"],
            "concerns": ["Remote preference"],
            "confidence": "High",
            "breakdown": {
                "title_match": 90,
                "skills_overlap": 80,
                "location_match": 95,
                "salary_match": 85,
                "company_size": 70,
                "seniority_match": 80,
            },
        }
        mock_client_instance = AsyncMock()
        mock_client_instance.generate_json = AsyncMock(return_value=llm_response)
        mock_client_cls = MagicMock(return_value=mock_client_instance)

        with patch("app.core.llm_clients.OpenAIClient", mock_client_cls):
            result = await score_job_with_llm(
                _make_job(), TEST_PREFERENCES, TEST_PROFILE
            )

        assert result.top_reasons == ["Skill match", "Location match", "Salary fit"]
        assert result.concerns == ["Remote preference"]
        assert result.confidence == "High"

    @pytest.mark.asyncio
    async def test_llm_missing_top_reasons_uses_rationale(self):
        """Missing top_reasons defaults to [rationale]."""
        llm_response = {
            "score": 70,
            "rationale": "Good match",
            "breakdown": {
                "title_match": 70,
                "skills_overlap": 70,
                "location_match": 70,
                "salary_match": 70,
                "company_size": 70,
                "seniority_match": 70,
            },
        }
        mock_client_instance = AsyncMock()
        mock_client_instance.generate_json = AsyncMock(return_value=llm_response)
        mock_client_cls = MagicMock(return_value=mock_client_instance)

        with patch("app.core.llm_clients.OpenAIClient", mock_client_cls):
            result = await score_job_with_llm(
                _make_job(), TEST_PREFERENCES, TEST_PROFILE
            )

        assert result.top_reasons == ["Good match"]

    @pytest.mark.asyncio
    async def test_llm_invalid_confidence_derives_from_score(self):
        """Invalid confidence string is replaced by score-derived value."""
        llm_response = {
            "score": 80,
            "rationale": "Match",
            "confidence": "SuperHigh",
            "breakdown": {
                "title_match": 80,
                "skills_overlap": 80,
                "location_match": 80,
                "salary_match": 80,
                "company_size": 80,
                "seniority_match": 80,
            },
        }
        mock_client_instance = AsyncMock()
        mock_client_instance.generate_json = AsyncMock(return_value=llm_response)
        mock_client_cls = MagicMock(return_value=mock_client_instance)

        with patch("app.core.llm_clients.OpenAIClient", mock_client_cls):
            result = await score_job_with_llm(
                _make_job(), TEST_PREFERENCES, TEST_PROFILE
            )

        assert result.confidence == "High"  # derived from score 80


# ---------------------------------------------------------------------------
# Heuristic rationale tests (6.2)
# ---------------------------------------------------------------------------


class TestHeuristicRationale:
    """Tests for build_heuristic_rationale function."""

    def test_high_scoring_dimensions_become_reasons(self):
        """High-scoring dimensions (>= 70% of max) produce top_reasons."""
        breakdown = {
            "title": (23, 25),
            "location": (18, 20),
            "salary": (18, 20),
            "skills": (16, 20),
            "seniority": (13, 15),
            "company_size": (8, 10),
        }
        result = build_heuristic_rationale(
            score=87,
            breakdown=breakdown,
            job=_make_job(),
            preferences=TEST_PREFERENCES,
            profile=TEST_PROFILE,
        )
        assert len(result["top_reasons"]) >= 1
        assert result["confidence"] == "High"

    def test_low_scoring_dimensions_become_concerns(self):
        """Low-scoring dimensions (< 30% of max) produce concerns."""
        breakdown = {
            "title": (5, 25),
            "location": (0, 20),
            "salary": (5, 20),
            "skills": (4, 20),
            "seniority": (3, 15),
            "company_size": (2, 10),
        }
        result = build_heuristic_rationale(
            score=15,
            breakdown=breakdown,
            job=_make_job(),
            preferences=TEST_PREFERENCES,
            profile=TEST_PROFILE,
        )
        assert len(result["concerns"]) >= 1
        assert result["confidence"] == "Low"

    def test_empty_breakdown(self):
        """Empty breakdown returns valid dict with empty reasons/concerns."""
        result = build_heuristic_rationale(
            score=50,
            breakdown={},
            job=_make_job(),
            preferences=TEST_PREFERENCES,
            profile=TEST_PROFILE,
        )
        assert isinstance(result, dict)
        assert result["top_reasons"] == []
        assert result["concerns"] == []
        assert "summary" in result
        assert "confidence" in result


# ---------------------------------------------------------------------------
# Confidence derivation tests (6.3)
# ---------------------------------------------------------------------------


class TestConfidenceDerivation:
    """Tests for _derive_confidence helper."""

    def test_high_confidence(self):
        assert _derive_confidence(80) == "High"

    def test_medium_confidence(self):
        assert _derive_confidence(60) == "Medium"

    def test_low_confidence(self):
        assert _derive_confidence(30) == "Low"

    def test_boundary_75(self):
        assert _derive_confidence(75) == "High"

    def test_boundary_50(self):
        assert _derive_confidence(50) == "Medium"

    def test_boundary_49(self):
        assert _derive_confidence(49) == "Low"


# ---------------------------------------------------------------------------
# Parse rationale tests (6.4)
# ---------------------------------------------------------------------------


class TestParseRationale:
    """Tests for parse_rationale utility function."""

    def test_none_input(self):
        """None input returns valid dict with empty top_reasons."""
        result = parse_rationale(None)
        assert result["summary"] == ""
        assert result["top_reasons"] == []
        assert result["concerns"] == []
        assert result["confidence"] == "Medium"

    def test_plain_text(self):
        """Plain text rationale is wrapped in fallback structure."""
        result = parse_rationale("75% match: title (20/25)")
        assert result["summary"] == "75% match: title (20/25)"
        assert result["top_reasons"] == ["75% match: title (20/25)"]
        assert result["concerns"] == []
        assert result["confidence"] == "Medium"

    def test_valid_json(self):
        """Valid JSON with top_reasons is returned as-is."""
        import json

        input_data = {
            "summary": "Good",
            "top_reasons": ["A", "B"],
            "concerns": ["C"],
            "confidence": "High",
        }
        result = parse_rationale(json.dumps(input_data))
        assert result["summary"] == "Good"
        assert result["top_reasons"] == ["A", "B"]
        assert result["concerns"] == ["C"]
        assert result["confidence"] == "High"

    def test_json_without_top_reasons(self):
        """JSON without top_reasons is wrapped in fallback structure."""
        import json

        result = parse_rationale(json.dumps({"score": 85}))
        assert "top_reasons" in result
        assert "concerns" in result
        assert "confidence" in result
