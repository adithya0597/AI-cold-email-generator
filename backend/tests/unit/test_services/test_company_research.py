"""Tests for Company Research Service (Story 8-2).

Covers: research(), LLM synthesis, conversation hooks, graceful degradation,
integration with InterviewIntelAgent.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.research.company_research import (
    CompanyResearchResult,
    CompanyResearchService,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    return CompanyResearchService()


@pytest.fixture
def mock_llm_response():
    """Standard LLM response for company research."""
    return {
        "mission": "To organize the world's information and make it universally accessible",
        "recent_news": [
            {
                "title": "Company launches new AI product",
                "summary": "Major AI product launch announced",
                "source_url": "https://example.com/news",
                "date": "2025-12-01",
            },
            {
                "title": "Q3 earnings exceed expectations",
                "summary": "Revenue grew 15% year over year",
                "source_url": "https://example.com/earnings",
                "date": "2025-10-15",
            },
        ],
        "products": ["Search", "Cloud Platform", "AI Services"],
        "competitors": ["Microsoft", "Amazon", "Apple"],
        "culture_indicators": [
            "Innovation-focused",
            "Flat hierarchy",
            "20% time for side projects",
        ],
        "challenges_opportunities": [
            "Regulatory scrutiny in AI space",
            "Expanding into enterprise market",
        ],
        "sources": [
            "https://example.com/about",
            "https://example.com/news",
        ],
    }


# ---------------------------------------------------------------------------
# AC1: Company research data structure
# ---------------------------------------------------------------------------


class TestResearchDataStructure:
    @pytest.mark.asyncio
    async def test_returns_complete_result(self, service, mock_llm_response):
        """research() returns CompanyResearchResult with all fields populated."""
        with patch(
            "app.core.llm_clients.LLMClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.research("Google")

        assert isinstance(result, CompanyResearchResult)
        assert result.mission != ""
        assert len(result.recent_news) == 2
        assert len(result.products) == 3
        assert len(result.competitors) == 3
        assert len(result.culture_indicators) == 3
        assert len(result.challenges_opportunities) == 2
        assert result.data_quality == "complete"

    @pytest.mark.asyncio
    async def test_news_items_have_correct_structure(self, service, mock_llm_response):
        """Each news item has title, summary, source_url, date."""
        with patch(
            "app.core.llm_clients.LLMClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.research("Google")

        for news in result.recent_news:
            assert "title" in news
            assert "summary" in news
            assert "source_url" in news
            assert "date" in news

    @pytest.mark.asyncio
    async def test_to_dict_serialization(self, service, mock_llm_response):
        """to_dict() produces JSON-serializable dictionary."""
        with patch(
            "app.core.llm_clients.LLMClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.research("Google")

        d = result.to_dict()
        assert isinstance(d, dict)
        assert "mission" in d
        assert "recent_news" in d
        assert "products" in d
        assert "competitors" in d
        assert "culture_indicators" in d
        assert "conversation_hooks" in d
        assert "data_quality" in d
        assert "sources" in d


# ---------------------------------------------------------------------------
# AC2: Source attribution
# ---------------------------------------------------------------------------


class TestSourceAttribution:
    @pytest.mark.asyncio
    async def test_sources_populated(self, service, mock_llm_response):
        """Result includes source attributions."""
        with patch(
            "app.core.llm_clients.LLMClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.research("Google")

        assert len(result.sources) > 0

    @pytest.mark.asyncio
    async def test_news_items_have_source_url(self, service, mock_llm_response):
        """News items include source_url for attribution."""
        with patch(
            "app.core.llm_clients.LLMClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.research("Google")

        for news in result.recent_news:
            assert news["source_url"] != ""


# ---------------------------------------------------------------------------
# AC3: Conversation hooks
# ---------------------------------------------------------------------------


class TestConversationHooks:
    @pytest.mark.asyncio
    async def test_hooks_generated(self, service, mock_llm_response):
        """Conversation hooks are generated from research data."""
        with patch(
            "app.core.llm_clients.LLMClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.research("Google")

        assert len(result.conversation_hooks) > 0

    @pytest.mark.asyncio
    async def test_hooks_have_correct_structure(self, service, mock_llm_response):
        """Each hook has topic, talking_point, source, relevance."""
        with patch(
            "app.core.llm_clients.LLMClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.research("Google")

        for hook in result.conversation_hooks:
            assert "topic" in hook
            assert "talking_point" in hook
            assert "source" in hook
            assert "relevance" in hook

    @pytest.mark.asyncio
    async def test_hooks_from_mission(self, service, mock_llm_response):
        """Hook generated from company mission."""
        with patch(
            "app.core.llm_clients.LLMClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.research("Google")

        mission_hooks = [h for h in result.conversation_hooks if h["topic"] == "Company Mission"]
        assert len(mission_hooks) == 1

    @pytest.mark.asyncio
    async def test_hooks_from_news(self, service, mock_llm_response):
        """Hooks generated from recent news."""
        with patch(
            "app.core.llm_clients.LLMClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.research("Google")

        news_titles = {n["title"] for n in mock_llm_response["recent_news"]}
        news_hooks = [h for h in result.conversation_hooks if h["topic"] in news_titles]
        assert len(news_hooks) > 0


# ---------------------------------------------------------------------------
# AC5: Graceful degradation
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    @pytest.mark.asyncio
    async def test_llm_failure_returns_partial(self, service):
        """When LLM fails, returns partial result."""
        with patch(
            "app.core.llm_clients.LLMClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(side_effect=Exception("LLM down"))

            result = await service.research("Google")

        assert result.data_quality == "partial"
        assert "Google" in result.mission

    @pytest.mark.asyncio
    async def test_empty_llm_response_partial(self, service):
        """When LLM returns empty dict, result is partial."""
        with patch(
            "app.core.llm_clients.LLMClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value={})

            result = await service.research("Acme")

        assert result.data_quality == "partial"

    @pytest.mark.asyncio
    async def test_hook_failure_still_returns_result(self, service, mock_llm_response):
        """When hook generation fails, research result still returned."""
        with patch(
            "app.core.llm_clients.LLMClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            with patch.object(
                service,
                "_generate_conversation_hooks",
                new_callable=AsyncMock,
                side_effect=Exception("Hook gen failed"),
            ):
                result = await service.research("Google")

        # Research data present, hooks empty
        assert result.data_quality == "complete"
        assert result.mission != ""
        assert result.conversation_hooks == []


# ---------------------------------------------------------------------------
# AC4: Integration with InterviewIntelAgent
# ---------------------------------------------------------------------------


class TestAgentIntegration:
    @pytest.mark.asyncio
    async def test_agent_uses_service(self):
        """InterviewIntelAgent._run_company_research() calls CompanyResearchService."""
        from app.agents.core.interview_intel_agent import InterviewIntelAgent

        agent = InterviewIntelAgent()
        mock_result = CompanyResearchResult(
            mission="Test mission",
            products=["Product A"],
            data_quality="complete",
        )

        with patch(
            "app.services.research.company_research.CompanyResearchService"
        ) as MockService:
            instance = MockService.return_value
            instance.research = AsyncMock(return_value=mock_result)

            result = await agent._run_company_research("TestCorp")

        assert result["mission"] == "Test mission"
        assert result["products"] == ["Product A"]
        assert result["data_quality"] == "complete"
        instance.research.assert_called_once_with("TestCorp")

    @pytest.mark.asyncio
    async def test_existing_agent_tests_compatible(self):
        """Agent execute() still produces correct output with real service."""
        from app.agents.core.interview_intel_agent import InterviewIntelAgent

        agent = InterviewIntelAgent()
        mock_result = CompanyResearchResult(
            mission="Acme Corp builds widgets",
            recent_news=[],
            products=["Widget Pro"],
            competitors=["WidgetCo"],
            culture_indicators=["Fast-paced"],
            data_quality="complete",
        )

        with patch(
            "app.services.research.company_research.CompanyResearchService"
        ) as MockService, patch(
            "app.agents.core.interview_intel_agent.InterviewIntelAgent._load_user_profile",
            new_callable=AsyncMock,
            return_value={},
        ):
            MockService.return_value.research = AsyncMock(return_value=mock_result)
            output = await agent.execute("user-1", {
                "application_id": "app-1",
                "company_name": "Acme Corp",
            })

        briefing = output.data["briefing"]
        # Keys from 8-1 still present
        assert "mission" in briefing["company_research"]
        assert "recent_news" in briefing["company_research"]
        assert "products" in briefing["company_research"]
        assert "competitors" in briefing["company_research"]
        assert "culture_indicators" in briefing["company_research"]
        # New keys from 8-2
        assert "conversation_hooks" in briefing["company_research"]
        assert "data_quality" in briefing["company_research"]
