"""Tests for Introduction Request Message Drafts Service (Story 9-3).

Covers: generate(), message content, length, fallback, to_dict(), agent integration.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.network.intro_drafts import IntroDraft, IntroDraftService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    return IntroDraftService()


@pytest.fixture
def mock_llm_response():
    """Standard LLM response for intro draft generation."""
    return {
        "message": (
            "Hi Alice! I noticed we share a connection through the tech "
            "community. I'm really interested in the engineering culture "
            "at Acme Corp and would love to hear your perspective. Would "
            "you be open to a brief chat sometime? No worries if not possible."
        ),
        "tone": "professional",
    }


@pytest.fixture
def warm_paths():
    return [
        {
            "contact_name": "Alice Smith",
            "company": "Acme Corp",
            "path_type": "1st_degree",
            "strength": "strong",
            "relationship_context": "Former colleague",
        },
        {
            "contact_name": "Bob Jones",
            "company": "Globex Inc",
            "path_type": "2nd_degree",
            "strength": "medium",
            "relationship_context": "Friend of friend",
        },
    ]


@pytest.fixture
def user_profile():
    return {
        "skills": ["Python", "Machine Learning", "Data Engineering"],
        "experience": [
            {"title": "Software Engineer", "company": "TechCo"},
        ],
    }


# ---------------------------------------------------------------------------
# AC1: Message content
# ---------------------------------------------------------------------------


class TestMessageContent:
    @pytest.mark.asyncio
    async def test_returns_intro_draft_list(
        self, service, mock_llm_response, warm_paths, user_profile
    ):
        """generate() returns list of IntroDraft objects."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.generate(warm_paths, user_profile)

        assert len(result) == 2
        assert all(isinstance(d, IntroDraft) for d in result)

    @pytest.mark.asyncio
    async def test_message_has_personalized_content(
        self, service, mock_llm_response, warm_paths, user_profile
    ):
        """Message contains personalized elements."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.generate(warm_paths[:1], user_profile)

        msg = result[0].message
        assert len(msg) > 0

    @pytest.mark.asyncio
    async def test_message_has_easy_out(
        self, service, mock_llm_response, warm_paths, user_profile
    ):
        """Message includes an easy-out phrase."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.generate(warm_paths[:1], user_profile)

        msg = result[0].message.lower()
        assert "no worries" in msg or "no pressure" in msg

    @pytest.mark.asyncio
    async def test_empty_paths_returns_empty(self, service, user_profile):
        """generate() returns empty list for no warm paths."""
        result = await service.generate([], user_profile)
        assert result == []


# ---------------------------------------------------------------------------
# AC2: Message length
# ---------------------------------------------------------------------------


class TestMessageLength:
    @pytest.mark.asyncio
    async def test_word_count_tracked(
        self, service, mock_llm_response, warm_paths, user_profile
    ):
        """IntroDraft tracks word count."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.generate(warm_paths[:1], user_profile)

        assert result[0].word_count > 0


# ---------------------------------------------------------------------------
# AC6: Graceful degradation / fallback
# ---------------------------------------------------------------------------


class TestFallback:
    @pytest.mark.asyncio
    async def test_llm_failure_returns_fallback(
        self, service, warm_paths, user_profile
    ):
        """When LLM fails, returns generic template."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(
                side_effect=Exception("LLM down")
            )

            result = await service.generate(warm_paths[:1], user_profile)

        assert len(result) == 1
        assert result[0].data_quality == "partial"
        assert "no worries" in result[0].message.lower()

    @pytest.mark.asyncio
    async def test_empty_llm_response_returns_fallback(
        self, service, warm_paths, user_profile
    ):
        """When LLM returns empty, returns generic template."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value={})

            result = await service.generate(warm_paths[:1], user_profile)

        assert len(result) == 1
        assert result[0].data_quality == "partial"

    def test_get_fallback_includes_contact(self, service):
        """Fallback template includes contact name."""
        path = {"contact_name": "Alice", "company": "Acme"}
        fallback = service._get_fallback(path)
        assert "Alice" in fallback.message
        assert "Acme" in fallback.message


# ---------------------------------------------------------------------------
# to_dict() serialization
# ---------------------------------------------------------------------------


class TestToDict:
    def test_to_dict_includes_all_fields(self):
        """to_dict() includes ALL dataclass fields."""
        draft = IntroDraft(
            recipient_name="Alice",
            connection_name="Bob",
            target_company="Acme",
            message="Hi there!",
            tone="professional",
            word_count=2,
            data_quality="complete",
        )
        d = draft.to_dict()
        assert d["recipient_name"] == "Alice"
        assert d["connection_name"] == "Bob"
        assert d["target_company"] == "Acme"
        assert d["message"] == "Hi there!"
        assert d["tone"] == "professional"
        assert d["word_count"] == 2
        assert d["data_quality"] == "complete"
        assert len(d) == 7


# ---------------------------------------------------------------------------
# AC5: Agent integration
# ---------------------------------------------------------------------------


class TestAgentIntegration:
    @pytest.mark.asyncio
    async def test_agent_calls_service(self):
        """NetworkAgent._generate_intro_drafts() delegates to IntroDraftService."""
        from app.agents.core.network_agent import NetworkAgent

        agent = NetworkAgent()
        mock_drafts = [
            IntroDraft(
                recipient_name="Alice",
                target_company="Acme",
                message="Hi!",
                word_count=1,
                data_quality="complete",
            )
        ]

        with patch(
            "app.services.network.intro_drafts.IntroDraftService"
        ) as MockService:
            instance = MockService.return_value
            instance.generate = AsyncMock(return_value=mock_drafts)

            result = await agent._generate_intro_drafts(
                [{"contact_name": "Alice"}], {}
            )

        assert len(result) == 1
        assert result[0]["recipient_name"] == "Alice"
        instance.generate.assert_called_once()
