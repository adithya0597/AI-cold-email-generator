"""Tests for Question Generation Service (Story 8-4).

Covers: question generation, categories, seniority tailoring,
fallback questions, integration with InterviewIntelAgent.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.research.question_generation import (
    GeneratedQuestions,
    QuestionGenerationService,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    return QuestionGenerationService()


@pytest.fixture
def mock_llm_response():
    """Standard LLM response for question generation."""
    return {
        "behavioral": [
            "Tell me about a time you led a cross-functional project.",
            "Describe a situation where you had to make a tough trade-off.",
            "How do you handle disagreements with stakeholders?",
        ],
        "technical": [
            "How would you design a real-time notification system?",
            "Explain your approach to database schema design.",
            "How do you ensure API backward compatibility?",
        ],
        "company_specific": [
            "Why do you want to work at Acme Corp?",
            "What challenges do you think Acme Corp faces in the market?",
            "How would you improve Acme Corp's developer experience?",
        ],
        "role_specific": [
            "How would you approach your first 90 days?",
            "Describe your ideal team structure for this role.",
            "How do you balance feature work with tech debt?",
        ],
    }


# ---------------------------------------------------------------------------
# AC1: Question generation (10-15 questions)
# ---------------------------------------------------------------------------


class TestQuestionGeneration:
    @pytest.mark.asyncio
    async def test_generates_10_plus_questions(self, service, mock_llm_response):
        """generate() returns 10+ questions total."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.generate("Backend Engineer", "Acme Corp", "senior")

        assert isinstance(result, GeneratedQuestions)
        assert result.total_count >= 10

    @pytest.mark.asyncio
    async def test_returns_generated_questions(self, service, mock_llm_response):
        """generate() returns GeneratedQuestions with all categories populated."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.generate("Backend Engineer", "Acme Corp", "senior")

        assert len(result.behavioral) == 3
        assert len(result.technical) == 3
        assert len(result.company_specific) == 3
        assert len(result.role_specific) == 3
        assert result.data_quality == "complete"


# ---------------------------------------------------------------------------
# AC2: Categories
# ---------------------------------------------------------------------------


class TestCategories:
    @pytest.mark.asyncio
    async def test_all_four_categories_present(self, service, mock_llm_response):
        """Questions are categorized into 4 groups."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.generate("Backend Engineer", "Acme Corp", "mid")

        d = result.to_dict()
        assert "behavioral" in d
        assert "technical" in d
        assert "company_specific" in d
        assert "role_specific" in d

    @pytest.mark.asyncio
    async def test_to_dict_returns_correct_format(self, service, mock_llm_response):
        """to_dict() returns dict[str, list[str]] format."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.generate("Backend Engineer", "Acme Corp", "mid")

        d = result.to_dict()
        for key in ("behavioral", "technical", "company_specific", "role_specific"):
            assert isinstance(d[key], list)
            for q in d[key]:
                assert isinstance(q, str)


# ---------------------------------------------------------------------------
# AC3: Seniority tailoring
# ---------------------------------------------------------------------------


class TestSeniorityTailoring:
    def test_normalize_junior(self, service):
        assert service._normalize_seniority("junior") == "junior"
        assert service._normalize_seniority("entry") == "junior"
        assert service._normalize_seniority("intern") == "junior"

    def test_normalize_senior(self, service):
        assert service._normalize_seniority("senior") == "senior"
        assert service._normalize_seniority("staff") == "senior"
        assert service._normalize_seniority("principal") == "senior"
        assert service._normalize_seniority("lead") == "senior"

    def test_normalize_mid(self, service):
        assert service._normalize_seniority("mid") == "mid"
        assert service._normalize_seniority("unknown") == "mid"

    @pytest.mark.asyncio
    async def test_fallback_uses_seniority(self, service):
        """Fallback questions are tailored to seniority."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(side_effect=Exception("LLM down"))

            junior = await service.generate("Dev", "Acme", "junior")
            senior = await service.generate("Dev", "Acme", "senior")

        # Different seniority should produce different questions
        assert junior.behavioral != senior.behavioral


# ---------------------------------------------------------------------------
# AC5: Graceful degradation / fallback
# ---------------------------------------------------------------------------


class TestFallback:
    @pytest.mark.asyncio
    async def test_llm_failure_returns_fallback(self, service):
        """When LLM fails, returns fallback questions."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(side_effect=Exception("LLM down"))

            result = await service.generate("Backend Engineer", "Acme Corp", "mid")

        assert result.data_quality == "fallback"
        assert result.total_count >= 10

    @pytest.mark.asyncio
    async def test_empty_llm_returns_fallback(self, service):
        """When LLM returns empty, returns fallback questions."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value={})

            result = await service.generate("Backend Engineer", "Acme Corp", "mid")

        assert result.data_quality == "fallback"
        assert result.total_count >= 10

    @pytest.mark.asyncio
    async def test_fallback_includes_company_name(self, service):
        """Fallback questions include company name."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(side_effect=Exception("LLM down"))

            result = await service.generate("Dev", "TechCorp", "mid")

        company_qs = result.company_specific
        assert any("TechCorp" in q for q in company_qs)


# ---------------------------------------------------------------------------
# AC4: Integration with InterviewIntelAgent
# ---------------------------------------------------------------------------


class TestAgentIntegration:
    @pytest.mark.asyncio
    async def test_agent_uses_service(self):
        """InterviewIntelAgent._generate_questions() calls QuestionGenerationService."""
        from app.agents.core.interview_intel_agent import InterviewIntelAgent

        agent = InterviewIntelAgent()
        mock_result = GeneratedQuestions(
            behavioral=["Q1", "Q2"],
            technical=["Q3"],
            company_specific=["Q4"],
            role_specific=["Q5"],
            data_quality="complete",
        )

        with patch(
            "app.services.research.question_generation.QuestionGenerationService"
        ) as MockService:
            instance = MockService.return_value
            instance.generate = AsyncMock(return_value=mock_result)

            result = await agent._generate_questions("Dev", "Acme", "mid")

        assert result["behavioral"] == ["Q1", "Q2"]
        assert result["technical"] == ["Q3"]
        instance.generate.assert_called_once_with("Dev", "Acme", "mid")
