"""Tests for Content Engagement Tracking Service (Story 9-4).

Covers: find_opportunities(), comment drafts, engagement recording,
history retrieval, graceful degradation, to_dict(), agent integration.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.network.engagement_tracking import (
    EngagementOpportunity,
    EngagementRecord,
    EngagementTrackingService,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    return EngagementTrackingService()


@pytest.fixture
def mock_llm_response():
    """Standard LLM response for engagement opportunities."""
    return {
        "opportunities": [
            {
                "content_topic": "AI in Healthcare",
                "content_type": "article",
                "suggested_comment": (
                    "Great analysis on AI applications in healthcare. "
                    "I've been working on similar challenges with ML pipelines."
                ),
                "opportunity_reason": "Shared interest in AI applications",
                "relevance_score": 0.8,
            },
            {
                "content_topic": "Team Leadership",
                "content_type": "post",
                "suggested_comment": "Really resonates — thanks for sharing!",
                "opportunity_reason": "Build familiarity",
                "relevance_score": 0.5,
            },
        ]
    }


@pytest.fixture
def contacts():
    return [
        {"name": "Alice Smith", "company": "Acme Corp", "role": "Engineer"},
        {"name": "Bob Jones", "company": "Globex Inc", "role": "Manager"},
    ]


@pytest.fixture
def user_profile():
    return {"skills": ["Python", "Machine Learning"]}


# ---------------------------------------------------------------------------
# AC1: Engagement opportunity surfacing
# ---------------------------------------------------------------------------


class TestFindOpportunities:
    @pytest.mark.asyncio
    async def test_returns_opportunity_list(
        self, service, mock_llm_response, contacts, user_profile
    ):
        """find_opportunities() returns list of EngagementOpportunity."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.find_opportunities(contacts, user_profile)

        assert len(result) > 0
        assert all(isinstance(o, EngagementOpportunity) for o in result)

    @pytest.mark.asyncio
    async def test_empty_contacts_returns_empty(self, service, user_profile):
        """find_opportunities() returns empty for no contacts."""
        result = await service.find_opportunities([], user_profile)
        assert result == []

    @pytest.mark.asyncio
    async def test_opportunities_have_contact_names(
        self, service, mock_llm_response, contacts, user_profile
    ):
        """Each opportunity has the contact_name set."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.find_opportunities(
                contacts[:1], user_profile
            )

        for opp in result:
            assert opp.contact_name == "Alice Smith"


# ---------------------------------------------------------------------------
# AC2: Comment draft suggestions
# ---------------------------------------------------------------------------


class TestCommentDrafts:
    @pytest.mark.asyncio
    async def test_suggested_comment_populated(
        self, service, mock_llm_response, contacts, user_profile
    ):
        """Opportunities include suggested comment drafts."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.find_opportunities(
                contacts[:1], user_profile
            )

        for opp in result:
            assert opp.suggested_comment != ""


# ---------------------------------------------------------------------------
# AC3: Engagement history (record & retrieve)
# ---------------------------------------------------------------------------


class TestEngagementHistory:
    def test_engagement_record_to_dict(self):
        """EngagementRecord.to_dict() includes all fields."""
        record = EngagementRecord(
            contact_name="Alice",
            engagement_type="comment",
            content_reference="post-123",
            timestamp="2025-12-01T10:00:00Z",
            temperature_impact=0.1,
        )
        d = record.to_dict()
        assert d["contact_name"] == "Alice"
        assert d["engagement_type"] == "comment"
        assert d["content_reference"] == "post-123"
        assert d["timestamp"] == "2025-12-01T10:00:00Z"
        assert d["temperature_impact"] == 0.1
        assert len(d) == 5


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    @pytest.mark.asyncio
    async def test_llm_failure_returns_partial(
        self, service, contacts, user_profile
    ):
        """When LLM fails, returns partial opportunities."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(
                side_effect=Exception("LLM down")
            )

            result = await service.find_opportunities(
                contacts[:1], user_profile
            )

        assert len(result) > 0
        assert result[0].data_quality == "partial"

    @pytest.mark.asyncio
    async def test_empty_llm_response(self, service, contacts, user_profile):
        """When LLM returns empty, returns partial opportunities."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value={})

            result = await service.find_opportunities(
                contacts[:1], user_profile
            )

        assert len(result) > 0
        assert result[0].data_quality == "partial"


# ---------------------------------------------------------------------------
# to_dict() serialization
# ---------------------------------------------------------------------------


class TestToDict:
    def test_opportunity_to_dict_includes_all_fields(self):
        """EngagementOpportunity.to_dict() includes ALL fields."""
        opp = EngagementOpportunity(
            contact_name="Alice",
            content_topic="AI trends",
            content_type="article",
            suggested_comment="Great read!",
            opportunity_reason="Shared interest",
            relevance_score=0.8,
            data_quality="complete",
        )
        d = opp.to_dict()
        assert d["contact_name"] == "Alice"
        assert d["content_topic"] == "AI trends"
        assert d["content_type"] == "article"
        assert d["suggested_comment"] == "Great read!"
        assert d["opportunity_reason"] == "Shared interest"
        assert d["relevance_score"] == 0.8
        assert d["data_quality"] == "complete"
        assert len(d) == 7

    def test_record_to_dict_includes_all_fields(self):
        """EngagementRecord.to_dict() includes ALL fields."""
        record = EngagementRecord(
            contact_name="Bob",
            engagement_type="like",
            content_reference="ref-1",
            timestamp="2025-12-01",
            temperature_impact=0.05,
        )
        d = record.to_dict()
        assert len(d) == 5


# ---------------------------------------------------------------------------
# AC6: Agent integration
# ---------------------------------------------------------------------------


class TestAgentIntegration:
    @pytest.mark.asyncio
    async def test_agent_calls_service(self):
        """NetworkAgent._identify_opportunities() delegates to EngagementTrackingService."""
        from app.agents.core.network_agent import NetworkAgent

        agent = NetworkAgent()
        mock_opps = [
            EngagementOpportunity(
                contact_name="Alice",
                content_topic="AI",
                suggested_comment="Nice!",
                data_quality="complete",
            )
        ]

        with patch(
            "app.services.network.engagement_tracking.EngagementTrackingService"
        ) as MockService:
            instance = MockService.return_value
            instance.find_opportunities = AsyncMock(return_value=mock_opps)

            result = await agent._identify_opportunities(
                [{"name": "Alice"}], {}
            )

        assert len(result) == 1
        assert result[0]["contact_name"] == "Alice"
        instance.find_opportunities.assert_called_once()
