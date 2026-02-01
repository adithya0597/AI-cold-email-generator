"""Tests for briefing approval cards (Story 5-9).

Covers: approval card data gathering, no-LLM briefing inclusion,
and empty state when no pending approvals.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _mock_approval_row(item_id=None, job_title="Backend Engineer", company="BigTech"):
    """Create a mock ApprovalQueueItem row."""
    row = MagicMock()
    row.id = item_id or uuid4()
    row.payload = {
        "job_id": "job-uuid-123",
        "job_title": job_title,
        "company": company,
        "submission_method": "api",
    }
    row.rationale = "High match score"
    row.created_at = datetime(2026, 2, 1, 10, 0, tzinfo=timezone.utc)
    return row


# ---------------------------------------------------------------------------
# Test: _get_pending_approval_cards
# ---------------------------------------------------------------------------


class TestGetPendingApprovalCards:
    """Tests for the approval cards data-gathering function."""

    @pytest.mark.asyncio
    async def test_returns_structured_card_data(self):
        """Returns cards with item_id, job_title, company, method, rationale."""
        mock_sess = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            _mock_approval_row(job_title="Frontend Dev", company="StartupCo"),
            _mock_approval_row(job_title="Backend Engineer", company="BigTech"),
        ]
        mock_sess.execute = AsyncMock(return_value=mock_result)

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.agents.briefing.generator import _get_pending_approval_cards

            cards = await _get_pending_approval_cards("user123")

        assert len(cards) == 2
        assert cards[0]["job_title"] == "Frontend Dev"
        assert cards[0]["company"] == "StartupCo"
        assert cards[0]["submission_method"] == "api"
        assert cards[0]["rationale"] == "High match score"
        assert "item_id" in cards[0]

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_pending(self):
        """Returns empty list when no pending approval items."""
        mock_sess = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_sess.execute = AsyncMock(return_value=mock_result)

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.agents.briefing.generator import _get_pending_approval_cards

            cards = await _get_pending_approval_cards("user123")

        assert cards == []

    @pytest.mark.asyncio
    async def test_graceful_fallback_on_error(self):
        """Returns empty list when database query fails."""
        with patch(
            "app.db.engine.AsyncSessionLocal",
            side_effect=Exception("DB connection failed"),
        ):
            from app.agents.briefing.generator import _get_pending_approval_cards

            cards = await _get_pending_approval_cards("user123")

        assert cards == []


# ---------------------------------------------------------------------------
# Test: _build_no_llm_briefing includes approval cards
# ---------------------------------------------------------------------------


class TestNoLlmBriefingWithCards:
    """Tests for no-LLM briefing including approval cards."""

    def test_includes_pending_approval_cards(self):
        """No-LLM briefing includes pending_approval_cards from raw data."""
        from app.agents.briefing.generator import _build_no_llm_briefing

        raw_data = {
            "recent_matches": [],
            "application_updates": [],
            "pending_approvals": 2,
            "agent_warnings": [],
            "pending_approval_cards": [
                {
                    "item_id": "item-1",
                    "job_title": "Backend Engineer",
                    "company": "BigTech",
                    "submission_method": "api",
                    "rationale": "High match",
                },
                {
                    "item_id": "item-2",
                    "job_title": "Frontend Dev",
                    "company": "StartupCo",
                    "submission_method": "email_fallback",
                    "rationale": "Good fit",
                },
            ],
        }

        briefing = _build_no_llm_briefing(raw_data)

        assert "pending_approval_cards" in briefing
        assert len(briefing["pending_approval_cards"]) == 2
        assert briefing["pending_approval_cards"][0]["job_title"] == "Backend Engineer"
        assert briefing["pending_approval_cards"][1]["company"] == "StartupCo"

    def test_empty_cards_when_no_approvals(self):
        """No-LLM briefing has empty cards list when no pending approvals."""
        from app.agents.briefing.generator import _build_no_llm_briefing

        raw_data = {
            "recent_matches": [],
            "application_updates": [],
            "pending_approvals": 0,
            "agent_warnings": [],
            "pending_approval_cards": [],
        }

        briefing = _build_no_llm_briefing(raw_data)

        assert briefing["pending_approval_cards"] == []

    def test_cards_default_to_empty_when_key_missing(self):
        """No-LLM briefing defaults cards to empty list if key missing."""
        from app.agents.briefing.generator import _build_no_llm_briefing

        raw_data = {
            "recent_matches": [],
            "application_updates": [],
            "pending_approvals": 0,
            "agent_warnings": [],
        }

        briefing = _build_no_llm_briefing(raw_data)

        assert briefing["pending_approval_cards"] == []
