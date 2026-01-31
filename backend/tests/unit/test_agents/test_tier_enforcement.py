"""
Tests for autonomy tier enforcement (L0--L3).

Verifies Phase 3 Success Criterion #4:
    "Autonomy level (L0-L3) is enforced -- an L0 user's agents only suggest,
     an L2 user's agents act but surface in approval digest, and this is
     verifiable via test."

Uses a simple ``TestAgent(BaseAgent)`` subclass with a dummy ``execute()``
to exercise the ``@requires_tier`` decorator and ``AutonomyGate`` class
in isolation (no database, no Redis, no Celery).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.base import AgentOutput, BaseAgent, BrakeActive, TierViolation
from app.agents.tier_enforcer import AutonomyGate, requires_tier


# ---------------------------------------------------------------------------
# Test agent with tier-decorated methods
# ---------------------------------------------------------------------------


class TestAgent(BaseAgent):
    """Minimal agent for tier enforcement testing."""

    agent_type = "test"

    @requires_tier("l0", action_type="read")
    async def read_action(self, user_id: str, query: str = "") -> AgentOutput:
        return AgentOutput(
            action="search",
            rationale="Found results",
            confidence=0.9,
            data={"query": query},
        )

    @requires_tier("l2", action_type="write")
    async def write_action(self, user_id: str, payload: dict | None = None) -> AgentOutput:
        return AgentOutput(
            action="apply",
            rationale="Applied to job",
            confidence=0.85,
            data=payload or {},
        )


# ---------------------------------------------------------------------------
# L0 tests -- suggestions only
# ---------------------------------------------------------------------------


class TestL0SuggestionOnly:
    """L0 users can only receive suggestions. Write actions are always blocked."""

    @pytest.mark.asyncio
    async def test_l0_user_gets_suggestion_only(
        self, test_user_id, mock_user_l0, redis_brake_inactive
    ):
        """L0 read action runs but output.action is prefixed with 'suggest:'."""
        agent = TestAgent()
        output = await agent.read_action(test_user_id, query="python developer")

        assert output.action.startswith("suggest:"), (
            f"L0 output must be prefixed with 'suggest:', got '{output.action}'"
        )
        assert output.action == "suggest:search"
        assert output.confidence == 0.9

    @pytest.mark.asyncio
    async def test_l0_user_cannot_write(
        self, test_user_id, mock_user_l0, redis_brake_inactive
    ):
        """L0 user write action raises TierViolation."""
        agent = TestAgent()

        with pytest.raises(TierViolation, match="L0 users cannot perform write actions"):
            await agent.write_action(test_user_id, payload={"job_id": "123"})


# ---------------------------------------------------------------------------
# L1 tests -- read allowed, write blocked
# ---------------------------------------------------------------------------


class TestL1ReadOnly:
    """L1 users can read and get recommendations. Write actions are blocked."""

    @pytest.mark.asyncio
    async def test_l1_user_can_read(
        self, test_user_id, mock_user_l1, redis_brake_inactive
    ):
        """L1 read action executes normally (no suggest: prefix)."""
        agent = TestAgent()
        output = await agent.read_action(test_user_id, query="data engineer")

        assert output.action == "search"
        assert output.confidence == 0.9

    @pytest.mark.asyncio
    async def test_l1_user_cannot_write(
        self, test_user_id, mock_user_l1, redis_brake_inactive
    ):
        """L1 user write action raises TierViolation."""
        agent = TestAgent()

        with pytest.raises(TierViolation, match="L1 users cannot perform write actions"):
            await agent.write_action(test_user_id, payload={"job_id": "456"})


# ---------------------------------------------------------------------------
# L2 tests -- read executes, write queues for approval
# ---------------------------------------------------------------------------


class TestL2Supervised:
    """L2 users can read directly. Write actions are routed to approval queue."""

    @pytest.mark.asyncio
    async def test_l2_read_action_executes_directly(
        self, test_user_id, mock_user_l2, redis_brake_inactive
    ):
        """L2 read action executes without approval."""
        agent = TestAgent()
        output = await agent.read_action(test_user_id, query="ml engineer")

        assert output.action == "search"
        assert output.requires_approval is False

    @pytest.mark.asyncio
    async def test_l2_write_action_queues_for_approval(
        self, test_user_id, mock_user_l2, redis_brake_inactive
    ):
        """L2 write action returns requires_approval=True via _queue_for_approval."""
        agent = TestAgent()

        # Mock _queue_for_approval so we don't need a real DB/Redis
        approval_output = AgentOutput(
            action="queued_for_approval",
            rationale="write_action requires L2 approval",
            confidence=1.0,
            requires_approval=True,
        )
        agent._queue_for_approval = AsyncMock(return_value=approval_output)

        output = await agent.write_action(test_user_id, payload={"job_id": "789"})

        assert output.requires_approval is True
        assert output.action == "queued_for_approval"
        agent._queue_for_approval.assert_awaited_once()


# ---------------------------------------------------------------------------
# L3 tests -- full autonomous execution
# ---------------------------------------------------------------------------


class TestL3Autonomous:
    """L3 users execute all actions directly (volume caps are agent-specific)."""

    @pytest.mark.asyncio
    async def test_l3_executes_directly(
        self, test_user_id, mock_user_l3, redis_brake_inactive
    ):
        """L3 actions execute without approval."""
        agent = TestAgent()
        output = await agent.write_action(test_user_id, payload={"job_id": "999"})

        assert output.action == "apply"
        assert output.requires_approval is False
        assert output.confidence == 0.85


# ---------------------------------------------------------------------------
# Brake interaction tests -- brake overrides ALL tiers
# ---------------------------------------------------------------------------


class TestBrakeOverride:
    """The emergency brake blocks all agent activity regardless of tier."""

    @pytest.mark.asyncio
    async def test_brake_blocks_all_tiers(
        self, test_user_id, mock_user_l3, redis_brake_active
    ):
        """Even L3 is blocked when the brake is active."""
        agent = TestAgent()

        with pytest.raises(BrakeActive):
            await agent.write_action(test_user_id, payload={"job_id": "000"})

    @pytest.mark.asyncio
    async def test_brake_check_happens_before_tier_check(
        self, test_user_id, redis_brake_active
    ):
        """Brake check is the FIRST thing that happens (before tier lookup).

        When brake is active, _get_user_tier should never be called because
        the brake check raises BrakeActive first.
        """
        agent = TestAgent()

        with patch(
            "app.agents.tier_enforcer._get_user_tier",
            new_callable=AsyncMock,
        ) as mock_tier:
            with pytest.raises(BrakeActive):
                await agent.write_action(test_user_id)

            # _get_user_tier must NOT have been called -- brake was checked first
            mock_tier.assert_not_awaited()


# ---------------------------------------------------------------------------
# AutonomyGate programmatic API tests
# ---------------------------------------------------------------------------


class TestAutonomyGate:
    """Tests for the non-decorator AutonomyGate.check() interface."""

    @pytest.mark.asyncio
    async def test_gate_l0_read_returns_suggest(
        self, test_user_id, mock_user_l0, redis_brake_inactive
    ):
        gate = AutonomyGate()
        result = await gate.check(test_user_id, "read")
        assert result == "suggest"

    @pytest.mark.asyncio
    async def test_gate_l0_write_returns_blocked(
        self, test_user_id, mock_user_l0, redis_brake_inactive
    ):
        gate = AutonomyGate()
        result = await gate.check(test_user_id, "write")
        assert result == "blocked"

    @pytest.mark.asyncio
    async def test_gate_l1_read_returns_execute(
        self, test_user_id, mock_user_l1, redis_brake_inactive
    ):
        gate = AutonomyGate()
        result = await gate.check(test_user_id, "read")
        assert result == "execute"

    @pytest.mark.asyncio
    async def test_gate_l1_write_returns_blocked(
        self, test_user_id, mock_user_l1, redis_brake_inactive
    ):
        gate = AutonomyGate()
        result = await gate.check(test_user_id, "write")
        assert result == "blocked"

    @pytest.mark.asyncio
    async def test_gate_l2_read_returns_execute(
        self, test_user_id, mock_user_l2, redis_brake_inactive
    ):
        gate = AutonomyGate()
        result = await gate.check(test_user_id, "read")
        assert result == "execute"

    @pytest.mark.asyncio
    async def test_gate_l2_write_returns_queue_approval(
        self, test_user_id, mock_user_l2, redis_brake_inactive
    ):
        gate = AutonomyGate()
        result = await gate.check(test_user_id, "write")
        assert result == "queue_approval"

    @pytest.mark.asyncio
    async def test_gate_l3_write_returns_execute(
        self, test_user_id, mock_user_l3, redis_brake_inactive
    ):
        gate = AutonomyGate()
        result = await gate.check(test_user_id, "write")
        assert result == "execute"

    @pytest.mark.asyncio
    async def test_gate_brake_returns_blocked(
        self, test_user_id, redis_brake_active
    ):
        """Brake overrides all tiers in the gate as well."""
        gate = AutonomyGate()
        # Brake is checked before tier -- no mock_user fixture needed
        # because check_brake returns True before _get_user_tier is called.
        result = await gate.check(test_user_id, "read")
        assert result == "blocked"
