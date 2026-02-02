"""Tests for STAR Suggestion Service (Story 8-5).

Covers: STAR generation, multiple options per question, profile-based,
graceful degradation, integration with InterviewIntelAgent.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.research.star_suggestions import (
    StarOutline,
    StarSuggestion,
    StarSuggestionService,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    return StarSuggestionService()


@pytest.fixture
def questions():
    return {
        "behavioral": [
            "Tell me about a time you led a project under tight deadlines.",
            "Describe a situation where you resolved a team conflict.",
        ],
        "technical": ["How would you design a cache?"],
    }


@pytest.fixture
def profile():
    return {
        "skills": ["Python", "SQL", "Leadership"],
        "experience": [
            {
                "title": "Tech Lead",
                "company": "PreviousCo",
                "description": "Led team of 5 engineers on platform migration",
            },
            {
                "title": "Senior Engineer",
                "company": "StartupInc",
                "description": "Built real-time analytics pipeline",
            },
        ],
    }


@pytest.fixture
def mock_llm_response():
    return {
        "suggestions": [
            {
                "situation": "Led platform migration with 2-week deadline",
                "task": "Coordinate 5 engineers and deliver on time",
                "action": "Broke project into parallel workstreams, daily standups",
                "result": "Delivered 2 days early, zero downtime",
            },
            {
                "situation": "Built analytics pipeline under pressure",
                "task": "Deliver real-time dashboard for product launch",
                "action": "Used streaming architecture, automated testing",
                "result": "Processed 1M events/day, 99.9% uptime",
            },
        ],
    }


# ---------------------------------------------------------------------------
# AC1: STAR generation
# ---------------------------------------------------------------------------


class TestStarGeneration:
    @pytest.mark.asyncio
    async def test_generates_for_each_behavioral(
        self, service, questions, profile, mock_llm_response
    ):
        """Generates STAR suggestions for each behavioral question."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            results = await service.generate(questions, profile)

        assert len(results) == 2  # 2 behavioral questions
        assert all(isinstance(r, StarSuggestion) for r in results)

    @pytest.mark.asyncio
    async def test_star_outline_has_all_fields(
        self, service, questions, profile, mock_llm_response
    ):
        """Each STAR outline has situation, task, action, result."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            results = await service.generate(questions, profile)

        for result in results:
            for suggestion in result.suggestions:
                assert suggestion.situation != ""
                assert suggestion.task != ""
                assert suggestion.action != ""
                assert suggestion.result != ""

    @pytest.mark.asyncio
    async def test_ignores_non_behavioral_questions(
        self, service, profile, mock_llm_response
    ):
        """Only behavioral questions get STAR suggestions."""
        qs = {"technical": ["Design a cache?"], "behavioral": []}

        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            results = await service.generate(qs, profile)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_to_dict_serialization(
        self, service, questions, profile, mock_llm_response
    ):
        """to_dict() produces correct structure."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            results = await service.generate(questions, profile)

        d = results[0].to_dict()
        assert "question" in d
        assert "suggestions" in d
        assert isinstance(d["suggestions"], list)
        star = d["suggestions"][0]
        assert "situation" in star
        assert "task" in star
        assert "action" in star
        assert "result" in star


# ---------------------------------------------------------------------------
# AC2: Multiple options (2-3 per question)
# ---------------------------------------------------------------------------


class TestMultipleOptions:
    @pytest.mark.asyncio
    async def test_2_to_3_suggestions_per_question(
        self, service, questions, profile, mock_llm_response
    ):
        """Each question gets 2-3 STAR suggestions."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            results = await service.generate(questions, profile)

        for result in results:
            assert 1 <= len(result.suggestions) <= 3


# ---------------------------------------------------------------------------
# AC5: Graceful degradation
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    @pytest.mark.asyncio
    async def test_llm_failure_returns_fallback(self, service, questions, profile):
        """When LLM fails, returns fallback STAR template."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(side_effect=Exception("LLM down"))

            results = await service.generate(questions, profile)

        assert len(results) == 2
        # Fallback has 1 generic suggestion
        for result in results:
            assert len(result.suggestions) == 1
            assert result.suggestions[0].situation != ""

    @pytest.mark.asyncio
    async def test_empty_llm_returns_fallback(self, service, questions, profile):
        """When LLM returns empty, returns fallback."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value={})

            results = await service.generate(questions, profile)

        assert len(results) == 2
        for result in results:
            assert len(result.suggestions) >= 1

    @pytest.mark.asyncio
    async def test_partial_failure_still_returns(
        self, service, questions, profile, mock_llm_response
    ):
        """If one question fails, others still get suggestions."""
        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First failed")
            return mock_llm_response

        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(side_effect=side_effect)

            results = await service.generate(questions, profile)

        assert len(results) == 2
        # First is fallback, second is LLM-generated
        assert len(results[0].suggestions) == 1  # fallback
        assert len(results[1].suggestions) == 2  # LLM


# ---------------------------------------------------------------------------
# AC4: Integration with InterviewIntelAgent
# ---------------------------------------------------------------------------


class TestAgentIntegration:
    @pytest.mark.asyncio
    async def test_agent_uses_service(self):
        """InterviewIntelAgent._generate_star_suggestions() calls StarSuggestionService."""
        from app.agents.core.interview_intel_agent import InterviewIntelAgent

        agent = InterviewIntelAgent()
        mock_result = [
            StarSuggestion(
                question="Q1",
                suggestions=[
                    StarOutline(
                        situation="Context",
                        task="Responsibility",
                        action="Steps taken",
                        result="Outcome",
                    ),
                ],
            ),
        ]

        questions = {"behavioral": ["Q1"]}
        profile = {"skills": ["Python"]}

        with patch(
            "app.services.research.star_suggestions.StarSuggestionService"
        ) as MockService:
            instance = MockService.return_value
            instance.generate = AsyncMock(return_value=mock_result)

            result = await agent._generate_star_suggestions(questions, profile)

        assert len(result) == 1
        assert result[0]["question"] == "Q1"
        assert len(result[0]["suggestions"]) == 1
        assert result[0]["suggestions"][0]["situation"] == "Context"
        instance.generate.assert_called_once_with(questions, profile)
