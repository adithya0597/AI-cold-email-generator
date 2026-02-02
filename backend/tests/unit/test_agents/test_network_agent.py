"""Tests for Network Agent (Stories 9-1 through 9-6).

Covers: agent execution, service delegation, analysis assembly,
approval flag, brake check, Celery task pattern, confidence,
temperature scores, approval queueing.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.base import AgentOutput, BrakeActive
from app.agents.core.network_agent import NetworkAgent
from app.services.network.warm_path import WarmPath
from app.services.network.intro_drafts import IntroDraft
from app.services.network.engagement_tracking import EngagementOpportunity


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def agent():
    return NetworkAgent()


@pytest.fixture
def base_task_data():
    return {
        "target_companies": ["Acme Corp", "Globex Inc"],
    }


@pytest.fixture
def mock_warm_paths():
    return [
        WarmPath(
            contact_name="Connection at Acme Corp",
            company="Acme Corp",
            path_type="2nd_degree",
            strength="medium",
            suggested_action="Ask for intro to Acme Corp",
            data_quality="complete",
        ),
        WarmPath(
            contact_name="Connection at Globex Inc",
            company="Globex Inc",
            path_type="2nd_degree",
            strength="medium",
            suggested_action="Ask for intro to Globex Inc",
            data_quality="complete",
        ),
    ]


@pytest.fixture
def mock_drafts():
    return [
        IntroDraft(
            recipient_name="Connection at Acme Corp",
            target_company="Acme Corp",
            message="Hi! I'd love to connect.",
            word_count=6,
            data_quality="complete",
        ),
        IntroDraft(
            recipient_name="Connection at Globex Inc",
            target_company="Globex Inc",
            message="Hi! I'd love to connect.",
            word_count=6,
            data_quality="complete",
        ),
    ]


@pytest.fixture
def mock_opportunities():
    return [
        EngagementOpportunity(
            contact_name="Connection at Acme Corp",
            content_topic="Tech trends",
            suggested_comment="Great post!",
            data_quality="complete",
        ),
        EngagementOpportunity(
            contact_name="Connection at Globex Inc",
            content_topic="Industry news",
            suggested_comment="Interesting!",
            data_quality="complete",
        ),
    ]


def _patch_all_services(mock_warm_paths, mock_drafts, mock_opportunities):
    """Return a combined patch context for all network services."""
    return (
        patch(
            "app.services.network.warm_path.WarmPathService",
        ),
        patch(
            "app.services.network.intro_drafts.IntroDraftService",
        ),
        patch(
            "app.services.network.engagement_tracking.EngagementTrackingService",
        ),
        patch(
            "app.services.network.approval.NetworkApprovalService",
        ),
    )


# ---------------------------------------------------------------------------
# Task 1: NetworkAgent.execute() tests
# ---------------------------------------------------------------------------


class TestNetworkAgentExecute:
    @pytest.mark.asyncio
    async def test_produces_correct_output_structure(
        self, agent, base_task_data, mock_warm_paths, mock_drafts, mock_opportunities
    ):
        """execute() returns AgentOutput with all analysis sections."""
        with patch(
            "app.services.network.warm_path.WarmPathService"
        ) as MockWP, patch(
            "app.services.network.intro_drafts.IntroDraftService"
        ) as MockID, patch(
            "app.services.network.engagement_tracking.EngagementTrackingService"
        ) as MockET, patch(
            "app.services.network.approval.NetworkApprovalService"
        ) as MockApproval:
            MockWP.return_value.analyze = AsyncMock(return_value=mock_warm_paths)
            MockID.return_value.generate = AsyncMock(return_value=mock_drafts)
            MockET.return_value.find_opportunities = AsyncMock(return_value=mock_opportunities)
            MockApproval.return_value.queue_outreach = AsyncMock(return_value="item-1")

            result = await agent.execute("user-1", base_task_data)

        assert isinstance(result, AgentOutput)
        assert result.action == "network_analysis_complete"
        assert result.confidence > 0

        data = result.data
        assert "target_companies" in data
        assert "warm_paths" in data
        assert "opportunities" in data
        assert "intro_drafts" in data
        assert "summary" in data
        assert "temperature_scores" in data

    @pytest.mark.asyncio
    async def test_warm_paths_populated(
        self, agent, base_task_data, mock_warm_paths, mock_drafts, mock_opportunities
    ):
        """execute() returns warm paths from service."""
        with patch(
            "app.services.network.warm_path.WarmPathService"
        ) as MockWP, patch(
            "app.services.network.intro_drafts.IntroDraftService"
        ) as MockID, patch(
            "app.services.network.engagement_tracking.EngagementTrackingService"
        ) as MockET, patch(
            "app.services.network.approval.NetworkApprovalService"
        ) as MockApproval:
            MockWP.return_value.analyze = AsyncMock(return_value=mock_warm_paths)
            MockID.return_value.generate = AsyncMock(return_value=mock_drafts)
            MockET.return_value.find_opportunities = AsyncMock(return_value=mock_opportunities)
            MockApproval.return_value.queue_outreach = AsyncMock(return_value="item-1")

            result = await agent.execute("user-1", base_task_data)

        warm_paths = result.data["warm_paths"]
        assert len(warm_paths) == 2

    @pytest.mark.asyncio
    async def test_opportunities_populated(
        self, agent, base_task_data, mock_warm_paths, mock_drafts, mock_opportunities
    ):
        """execute() returns opportunities from service."""
        with patch(
            "app.services.network.warm_path.WarmPathService"
        ) as MockWP, patch(
            "app.services.network.intro_drafts.IntroDraftService"
        ) as MockID, patch(
            "app.services.network.engagement_tracking.EngagementTrackingService"
        ) as MockET, patch(
            "app.services.network.approval.NetworkApprovalService"
        ) as MockApproval:
            MockWP.return_value.analyze = AsyncMock(return_value=mock_warm_paths)
            MockID.return_value.generate = AsyncMock(return_value=mock_drafts)
            MockET.return_value.find_opportunities = AsyncMock(return_value=mock_opportunities)
            MockApproval.return_value.queue_outreach = AsyncMock(return_value="item-1")

            result = await agent.execute("user-1", base_task_data)

        opportunities = result.data["opportunities"]
        assert len(opportunities) == 2

    @pytest.mark.asyncio
    async def test_intro_drafts_generated(
        self, agent, base_task_data, mock_warm_paths, mock_drafts, mock_opportunities
    ):
        """execute() generates intro drafts from service."""
        with patch(
            "app.services.network.warm_path.WarmPathService"
        ) as MockWP, patch(
            "app.services.network.intro_drafts.IntroDraftService"
        ) as MockID, patch(
            "app.services.network.engagement_tracking.EngagementTrackingService"
        ) as MockET, patch(
            "app.services.network.approval.NetworkApprovalService"
        ) as MockApproval:
            MockWP.return_value.analyze = AsyncMock(return_value=mock_warm_paths)
            MockID.return_value.generate = AsyncMock(return_value=mock_drafts)
            MockET.return_value.find_opportunities = AsyncMock(return_value=mock_opportunities)
            MockApproval.return_value.queue_outreach = AsyncMock(return_value="item-1")

            result = await agent.execute("user-1", base_task_data)

        drafts = result.data["intro_drafts"]
        assert len(drafts) == 2

    @pytest.mark.asyncio
    async def test_empty_target_companies_returns_guidance(self, agent):
        """execute() returns guidance when no target companies provided."""
        result = await agent.execute("user-1", {"target_companies": []})

        assert result.action == "network_analysis_complete"
        assert result.confidence == 0.5
        assert "guidance" in result.data
        assert result.data["warm_paths"] == []
        assert result.data["opportunities"] == []
        assert result.data["intro_drafts"] == []

    @pytest.mark.asyncio
    async def test_no_target_companies_key_returns_guidance(self, agent):
        """execute() returns guidance when target_companies key missing."""
        result = await agent.execute("user-1", {})

        assert result.action == "network_analysis_complete"
        assert "guidance" in result.data

    @pytest.mark.asyncio
    async def test_requires_approval_when_drafts_exist(
        self, agent, base_task_data, mock_warm_paths, mock_drafts, mock_opportunities
    ):
        """requires_approval=True when intro drafts are generated."""
        with patch(
            "app.services.network.warm_path.WarmPathService"
        ) as MockWP, patch(
            "app.services.network.intro_drafts.IntroDraftService"
        ) as MockID, patch(
            "app.services.network.engagement_tracking.EngagementTrackingService"
        ) as MockET, patch(
            "app.services.network.approval.NetworkApprovalService"
        ) as MockApproval:
            MockWP.return_value.analyze = AsyncMock(return_value=mock_warm_paths)
            MockID.return_value.generate = AsyncMock(return_value=mock_drafts)
            MockET.return_value.find_opportunities = AsyncMock(return_value=mock_opportunities)
            MockApproval.return_value.queue_outreach = AsyncMock(return_value="item-1")

            result = await agent.execute("user-1", base_task_data)

        assert len(result.data["intro_drafts"]) > 0
        assert result.requires_approval is True

    @pytest.mark.asyncio
    async def test_no_approval_when_no_drafts(self, agent):
        """requires_approval=False when no intro drafts (empty companies)."""
        result = await agent.execute("user-1", {"target_companies": []})

        assert len(result.data["intro_drafts"]) == 0
        assert result.requires_approval is False

    @pytest.mark.asyncio
    async def test_summary_counts_correct(
        self, agent, base_task_data, mock_warm_paths, mock_drafts, mock_opportunities
    ):
        """Summary section has correct aggregate counts."""
        with patch(
            "app.services.network.warm_path.WarmPathService"
        ) as MockWP, patch(
            "app.services.network.intro_drafts.IntroDraftService"
        ) as MockID, patch(
            "app.services.network.engagement_tracking.EngagementTrackingService"
        ) as MockET, patch(
            "app.services.network.approval.NetworkApprovalService"
        ) as MockApproval:
            MockWP.return_value.analyze = AsyncMock(return_value=mock_warm_paths)
            MockID.return_value.generate = AsyncMock(return_value=mock_drafts)
            MockET.return_value.find_opportunities = AsyncMock(return_value=mock_opportunities)
            MockApproval.return_value.queue_outreach = AsyncMock(return_value="item-1")

            result = await agent.execute("user-1", base_task_data)

        summary = result.data["summary"]
        assert summary["companies_analyzed"] == 2
        assert summary["total_warm_paths"] == 2
        assert summary["total_opportunities"] == 2
        assert summary["total_intro_drafts"] == 2

    @pytest.mark.asyncio
    async def test_queues_drafts_for_approval(
        self, agent, base_task_data, mock_warm_paths, mock_drafts, mock_opportunities
    ):
        """execute() queues each draft for approval (9-6)."""
        with patch(
            "app.services.network.warm_path.WarmPathService"
        ) as MockWP, patch(
            "app.services.network.intro_drafts.IntroDraftService"
        ) as MockID, patch(
            "app.services.network.engagement_tracking.EngagementTrackingService"
        ) as MockET, patch(
            "app.services.network.approval.NetworkApprovalService"
        ) as MockApproval:
            MockWP.return_value.analyze = AsyncMock(return_value=mock_warm_paths)
            MockID.return_value.generate = AsyncMock(return_value=mock_drafts)
            MockET.return_value.find_opportunities = AsyncMock(return_value=mock_opportunities)
            MockApproval.return_value.queue_outreach = AsyncMock(return_value="item-1")

            await agent.execute("user-1", base_task_data)

        # Should have been called once per draft
        assert MockApproval.return_value.queue_outreach.call_count == 2


# ---------------------------------------------------------------------------
# AC6: Emergency brake (inherited from BaseAgent.run())
# ---------------------------------------------------------------------------


class TestBrakeRespect:
    @pytest.mark.asyncio
    async def test_brake_active_raises(self, agent):
        """run() raises BrakeActive when brake is active."""
        with patch(
            "app.agents.brake.check_brake",
            new_callable=AsyncMock,
            return_value=True,
        ):
            with pytest.raises(BrakeActive):
                await agent.run("user-1", {"target_companies": ["Acme"]})


# ---------------------------------------------------------------------------
# AC5: Celery task pattern
# ---------------------------------------------------------------------------


class TestCeleryTaskPattern:
    def test_task_is_registered(self):
        """agent_network task exists in Celery app."""
        from app.worker.tasks import agent_network

        assert agent_network.name == "app.worker.tasks.agent_network"

    def test_task_queue_is_agents(self):
        """Task is routed to the 'agents' queue."""
        from app.worker.tasks import agent_network

        assert agent_network.queue == "agents"

    def test_task_has_retries(self):
        """Task has max_retries=2."""
        from app.worker.tasks import agent_network

        assert agent_network.max_retries == 2


# ---------------------------------------------------------------------------
# Confidence computation
# ---------------------------------------------------------------------------


class TestConfidenceComputation:
    def test_full_confidence(self, agent):
        """All sections present → full confidence."""
        confidence = agent._compute_confidence(
            warm_paths=[{"contact_name": "Alice"}],
            opportunities=[{"contact_name": "Bob"}],
            intro_drafts=[{"recipient_name": "Carol"}],
        )
        assert confidence == 1.0

    def test_no_data_zero_confidence(self, agent):
        """No data → zero confidence."""
        confidence = agent._compute_confidence(
            warm_paths=[],
            opportunities=[],
            intro_drafts=[],
        )
        assert confidence == 0.0

    def test_partial_confidence(self, agent):
        """Some sections present → partial confidence."""
        confidence = agent._compute_confidence(
            warm_paths=[{"contact_name": "Alice"}],
            opportunities=[],
            intro_drafts=[],
        )
        assert confidence == pytest.approx(0.33, abs=0.01)
