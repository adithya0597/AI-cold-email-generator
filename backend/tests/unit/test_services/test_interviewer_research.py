"""Tests for Interviewer Research Service (Story 8-3).

Covers: research(), LLM synthesis, conversation starters, graceful degradation,
privacy (public data only), integration with InterviewIntelAgent.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.research.interviewer_research import (
    InterviewerProfile,
    InterviewerResearchService,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    return InterviewerResearchService()


@pytest.fixture
def mock_llm_response():
    """Standard LLM response for interviewer research."""
    return {
        "current_role": "VP of Engineering at TechCorp",
        "tenure": "3 years",
        "career_highlights": [
            "Led migration to microservices at ScaleCo",
            "Founded DevTools startup (acquired 2020)",
        ],
        "public_content": [
            {
                "type": "article",
                "title": "Scaling Engineering Teams",
                "url": "https://blog.example.com/scaling",
            },
            {
                "type": "talk",
                "title": "Building Platform Teams",
                "url": "https://conf.example.com/talk",
            },
        ],
        "speaking_topics": ["Platform Engineering", "Team Scaling", "DevOps"],
        "shared_interests": ["Open Source", "Mentorship"],
    }


# ---------------------------------------------------------------------------
# AC1: Interviewer profile structure
# ---------------------------------------------------------------------------


class TestInterviewerProfileStructure:
    @pytest.mark.asyncio
    async def test_returns_profile_list(self, service, mock_llm_response):
        """research() returns list of InterviewerProfile."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            results = await service.research(["Alice Smith"])

        assert len(results) == 1
        assert isinstance(results[0], InterviewerProfile)

    @pytest.mark.asyncio
    async def test_profile_has_required_fields(self, service, mock_llm_response):
        """Profile includes current_role, tenure, career_highlights, public_content."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            results = await service.research(["Alice Smith"])

        profile = results[0]
        assert profile.name == "Alice Smith"
        assert profile.current_role == "VP of Engineering at TechCorp"
        assert profile.tenure == "3 years"
        assert len(profile.career_highlights) == 2
        assert len(profile.public_content) == 2
        assert len(profile.speaking_topics) == 3
        assert profile.data_quality == "complete"

    @pytest.mark.asyncio
    async def test_multiple_interviewers(self, service, mock_llm_response):
        """research() handles multiple interviewer names."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            results = await service.research(["Alice Smith", "Bob Jones"])

        assert len(results) == 2
        assert results[0].name == "Alice Smith"
        assert results[1].name == "Bob Jones"

    @pytest.mark.asyncio
    async def test_to_dict_serialization(self, service, mock_llm_response):
        """to_dict() produces JSON-serializable dictionary."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            results = await service.research(["Alice Smith"])

        d = results[0].to_dict()
        assert isinstance(d, dict)
        assert "name" in d
        assert "current_role" in d
        assert "tenure" in d
        assert "career_highlights" in d
        assert "public_content" in d
        assert "speaking_topics" in d
        assert "conversation_starters" in d
        assert "data_quality" in d

    @pytest.mark.asyncio
    async def test_public_content_structure(self, service, mock_llm_response):
        """Public content items have type, title, url keys."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            results = await service.research(["Alice Smith"])

        for item in results[0].public_content:
            assert "type" in item
            assert "title" in item
            assert "url" in item


# ---------------------------------------------------------------------------
# AC2: Privacy — public data only
# ---------------------------------------------------------------------------


class TestPrivacy:
    @pytest.mark.asyncio
    async def test_no_private_fields(self, service, mock_llm_response):
        """Profile does not contain private data fields."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            results = await service.research(["Alice Smith"])

        d = results[0].to_dict()
        private_fields = ["email", "phone", "address", "salary", "age", "ssn"]
        for field_name in private_fields:
            assert field_name not in d


# ---------------------------------------------------------------------------
# AC3: Conversation starters
# ---------------------------------------------------------------------------


class TestConversationStarters:
    @pytest.mark.asyncio
    async def test_starters_generated(self, service, mock_llm_response):
        """Conversation starters are generated from profile data."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            results = await service.research(["Alice Smith"])

        assert len(results[0].conversation_starters) > 0

    @pytest.mark.asyncio
    async def test_starters_have_correct_structure(self, service, mock_llm_response):
        """Each starter has topic, opener, source."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            results = await service.research(["Alice Smith"])

        for starter in results[0].conversation_starters:
            assert "topic" in starter
            assert "opener" in starter
            assert "source" in starter

    @pytest.mark.asyncio
    async def test_starters_from_speaking_topics(self, service, mock_llm_response):
        """Starters generated from speaking topics."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            results = await service.research(["Alice Smith"])

        topic_starters = [
            s for s in results[0].conversation_starters
            if s["source"] == "speaking_topics"
        ]
        assert len(topic_starters) > 0


# ---------------------------------------------------------------------------
# AC5: Graceful degradation
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    @pytest.mark.asyncio
    async def test_llm_failure_returns_partial(self, service):
        """When LLM fails, returns partial profile."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(side_effect=Exception("LLM down"))

            results = await service.research(["Alice Smith"])

        assert len(results) == 1
        assert results[0].data_quality == "partial"
        assert results[0].name == "Alice Smith"

    @pytest.mark.asyncio
    async def test_empty_llm_response_partial(self, service):
        """When LLM returns empty dict, result is partial."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value={})

            results = await service.research(["Alice Smith"])

        assert results[0].data_quality == "partial"

    @pytest.mark.asyncio
    async def test_partial_failure_does_not_block_others(self, service, mock_llm_response):
        """If one interviewer fails, others still succeed."""
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

            results = await service.research(["Alice Smith", "Bob Jones"])

        assert len(results) == 2
        assert results[0].data_quality == "partial"
        assert results[1].data_quality == "complete"


# ---------------------------------------------------------------------------
# AC4: Integration with InterviewIntelAgent
# ---------------------------------------------------------------------------


class TestAgentIntegration:
    @pytest.mark.asyncio
    async def test_agent_uses_service(self):
        """InterviewIntelAgent._run_interviewer_research() calls InterviewerResearchService."""
        from app.agents.core.interview_intel_agent import InterviewIntelAgent

        agent = InterviewIntelAgent()
        mock_profile = InterviewerProfile(
            name="Alice Smith",
            current_role="VP Engineering",
            career_highlights=["Led scaling"],
            data_quality="complete",
        )

        with patch(
            "app.services.research.interviewer_research.InterviewerResearchService"
        ) as MockService:
            instance = MockService.return_value
            instance.research = AsyncMock(return_value=[mock_profile])

            result = await agent._run_interviewer_research(["Alice Smith"])

        assert len(result) == 1
        assert result[0]["name"] == "Alice Smith"
        assert result[0]["current_role"] == "VP Engineering"
        instance.research.assert_called_once_with(["Alice Smith"])
