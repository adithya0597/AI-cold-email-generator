"""Tests for the Follow-up Agent (Story 6-7).

Covers: timing calculation, aggressiveness preference, draft generation,
no applications needing follow-up, and agent output format.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.core.followup_agent import (
    AGGRESSIVENESS_MULTIPLIERS,
    TIMING_RULES,
    FollowUpAgent,
    _add_business_days,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_session_cm():
    """Create a mock async session context manager."""
    mock_sess = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_sess)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm, mock_sess


def _sample_app(status="applied", applied_at="2025-01-01T00:00:00+00:00", updated_at=None):
    return {
        "id": "app-uuid-123",
        "status": status,
        "applied_at": applied_at,
        "updated_at": updated_at,
        "job_title": "Software Engineer",
        "company": "Acme Corp",
    }


# ---------------------------------------------------------------------------
# Test: Business day calculation
# ---------------------------------------------------------------------------


class TestBusinessDays:
    def test_add_business_days_skips_weekends(self):
        """Friday + 1 business day = Monday."""
        friday = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Friday
        result = _add_business_days(friday, 1)
        assert result.weekday() == 0  # Monday

    def test_add_business_days_five(self):
        """Monday + 5 business days = next Monday."""
        monday = datetime(2025, 1, 6, tzinfo=timezone.utc)  # Monday
        result = _add_business_days(monday, 5)
        assert result.weekday() == 0  # next Monday
        assert result.day == 13


# ---------------------------------------------------------------------------
# Test: Timing calculation per milestone
# ---------------------------------------------------------------------------


class TestFollowUpTiming:
    @pytest.mark.asyncio
    async def test_applied_status_uses_6_business_days(self):
        """Applied applications get 6 business day follow-up window."""
        agent = FollowUpAgent()
        app = _sample_app(status="applied", applied_at="2025-01-06T00:00:00+00:00")
        result = agent._calculate_followup_date(app, "normal")
        # Jan 6 (Mon) + 6 bdays = Jan 14 (Tue)
        assert result is not None
        assert result.day == 14

    @pytest.mark.asyncio
    async def test_interview_status_uses_2_business_days(self):
        """Interview applications get 2 business day follow-up window."""
        agent = FollowUpAgent()
        app = _sample_app(status="interview", applied_at="2025-01-06T00:00:00+00:00")
        result = agent._calculate_followup_date(app, "normal")
        # Jan 6 (Mon) + 2 bdays = Jan 8 (Wed)
        assert result is not None
        assert result.day == 8

    @pytest.mark.asyncio
    async def test_unknown_status_returns_none(self):
        """Statuses not in TIMING_RULES return None."""
        agent = FollowUpAgent()
        app = _sample_app(status="offer")
        result = agent._calculate_followup_date(app, "normal")
        assert result is None


# ---------------------------------------------------------------------------
# Test: Aggressiveness preference
# ---------------------------------------------------------------------------


class TestAggressivenessPreference:
    @pytest.mark.asyncio
    async def test_conservative_adds_more_days(self):
        """Conservative preference increases the follow-up window."""
        agent = FollowUpAgent()
        app = _sample_app(status="applied", applied_at="2025-01-06T00:00:00+00:00")

        normal = agent._calculate_followup_date(app, "normal")
        conservative = agent._calculate_followup_date(app, "conservative")

        assert normal is not None
        assert conservative is not None
        assert conservative > normal

    @pytest.mark.asyncio
    async def test_aggressive_reduces_days(self):
        """Aggressive preference reduces the follow-up window."""
        agent = FollowUpAgent()
        app = _sample_app(status="applied", applied_at="2025-01-06T00:00:00+00:00")

        normal = agent._calculate_followup_date(app, "normal")
        aggressive = agent._calculate_followup_date(app, "aggressive")

        assert normal is not None
        assert aggressive is not None
        assert aggressive < normal


# ---------------------------------------------------------------------------
# Test: No applications needing follow-up
# ---------------------------------------------------------------------------


class TestNoFollowupsNeeded:
    @pytest.mark.asyncio
    async def test_no_applications_returns_none_needed(self):
        """Agent returns followup_none_needed when no applications found."""
        agent = FollowUpAgent()

        with patch.object(agent, "_load_pending_applications", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = []

            result = await agent.execute("user-123", {})

        assert result.action == "followup_none_needed"
        assert result.data["suggestions_count"] == 0


# ---------------------------------------------------------------------------
# Test: Draft generation
# ---------------------------------------------------------------------------


class TestDraftGeneration:
    @pytest.mark.asyncio
    async def test_generate_followup_draft_with_llm(self):
        """Draft generation calls OpenAI and parses JSON response."""
        agent = FollowUpAgent()
        app = _sample_app()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"subject": "Follow-up: SE at Acme", "body": "Dear team..."}'

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("openai.AsyncOpenAI", return_value=mock_client):
            draft = await agent._generate_followup_draft(app)

        assert draft["subject"] == "Follow-up: SE at Acme"
        assert draft["body"] == "Dear team..."

    @pytest.mark.asyncio
    async def test_generate_followup_draft_fallback_on_error(self):
        """Draft generation falls back to template when LLM fails."""
        agent = FollowUpAgent()
        app = _sample_app()

        with patch("openai.AsyncOpenAI", side_effect=Exception("API error")):
            draft = await agent._generate_followup_draft(app)

        assert "Software Engineer" in draft["subject"]
        assert "Acme Corp" in draft["body"]


# ---------------------------------------------------------------------------
# Test: Full agent execution with suggestions
# ---------------------------------------------------------------------------


class TestFullExecution:
    @pytest.mark.asyncio
    async def test_creates_suggestions_for_overdue_applications(self):
        """Agent creates suggestions for applications past follow-up date."""
        agent = FollowUpAgent()

        # Application from 30 days ago — definitely overdue
        app = _sample_app(
            status="applied",
            applied_at="2024-12-01T00:00:00+00:00",
        )

        with (
            patch.object(agent, "_load_pending_applications", new_callable=AsyncMock) as mock_load,
            patch.object(agent, "_generate_followup_draft", new_callable=AsyncMock) as mock_draft,
            patch.object(agent, "_store_suggestions", new_callable=AsyncMock) as mock_store,
        ):
            mock_load.return_value = [app]
            mock_draft.return_value = {"subject": "Follow-up", "body": "Hello"}

            result = await agent.execute("user-123", {"aggressiveness": "normal"})

        assert result.action == "followup_suggestions_created"
        assert result.data["suggestions_count"] == 1
        mock_store.assert_called_once()
