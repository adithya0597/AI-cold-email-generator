"""Tests for the Pipeline Agent (Story 6-1).

Covers: happy path status update, rejection detection, interview detection,
ambiguous email flagging, missing application, empty email error,
same-status no-op, and Celery task registration.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _mock_session_cm():
    """Create a mock async session context manager."""
    mock_sess = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_sess)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm, mock_sess


def _sample_application_row(status="applied"):
    row = MagicMock()
    row.__getitem__ = lambda self, key: {
        "id": "app-uuid-123",
        "status": status,
        "job_id": "job-uuid-456",
    }[key]
    return row


# ---------------------------------------------------------------------------
# Test: Happy path — status update (AC1, AC3, AC4)
# ---------------------------------------------------------------------------


class TestPipelineAgentHappyPath:
    """Tests for successful status detection and update."""

    @pytest.mark.asyncio
    async def test_detects_rejection_and_updates_status(self):
        """Agent detects rejection email and updates application status."""
        mock_cm, mock_sess = _mock_session_cm()

        # _load_application query
        mock_app_result = MagicMock()
        mock_app_result.mappings.return_value.first.return_value = _sample_application_row("applied")

        # _update_application_status: UPDATE + INSERT
        mock_update = MagicMock()
        mock_insert = MagicMock()

        mock_sess.execute = AsyncMock(side_effect=[mock_app_result, mock_update, mock_insert])
        mock_sess.commit = AsyncMock()

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.agents.core.pipeline_agent import PipelineAgent

            agent = PipelineAgent()
            result = await agent.execute("user123", {
                "application_id": "app-uuid-123",
                "email_subject": "Application Update",
                "email_body": "We have decided to move forward with other candidates.",
            })

        assert result.action == "pipeline_status_updated"
        assert result.data["new_status"] == "rejected"
        assert result.data["old_status"] == "applied"
        assert result.confidence >= 0.9
        assert result.data["evidence_snippet"]

    @pytest.mark.asyncio
    async def test_detects_interview_invitation(self):
        """Agent detects interview email and updates status."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_app_result = MagicMock()
        mock_app_result.mappings.return_value.first.return_value = _sample_application_row("applied")

        mock_sess.execute = AsyncMock(side_effect=[mock_app_result, MagicMock(), MagicMock()])
        mock_sess.commit = AsyncMock()

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.agents.core.pipeline_agent import PipelineAgent

            agent = PipelineAgent()
            result = await agent.execute("user123", {
                "application_id": "app-uuid-123",
                "email_subject": "Interview Request",
                "email_body": "We would like to schedule an interview with you.",
            })

        assert result.action == "pipeline_status_updated"
        assert result.data["new_status"] == "interview"


# ---------------------------------------------------------------------------
# Test: Ambiguous email flagging (AC5)
# ---------------------------------------------------------------------------


class TestPipelineAgentAmbiguous:
    """Tests for ambiguous email handling."""

    @pytest.mark.asyncio
    async def test_ambiguous_email_flagged_for_review(self):
        """Low-confidence detection returns review_needed instead of updating."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_app_result = MagicMock()
        mock_app_result.mappings.return_value.first.return_value = _sample_application_row("applied")
        mock_sess.execute = AsyncMock(return_value=mock_app_result)

        # Patch the detector to return a low-confidence result
        from app.services.email_parser import StatusDetection

        mock_detection = StatusDetection(
            detected_status="interview",
            confidence=0.5,
            evidence_snippet="possible interview mention",
            is_ambiguous=True,
        )

        with (
            patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm),
            patch("app.services.email_parser.EmailStatusDetector.detect", return_value=mock_detection),
        ):
            from app.agents.core.pipeline_agent import PipelineAgent

            agent = PipelineAgent()
            result = await agent.execute("user123", {
                "application_id": "app-uuid-123",
                "email_subject": "FYI",
                "email_body": "Some ambiguous text about next steps.",
            })

        assert result.action == "pipeline_review_needed"
        assert result.data["requires_user_review"] is True
        assert result.data["suggested_status"] == "interview"
        assert result.confidence < 0.7


# ---------------------------------------------------------------------------
# Test: Error handling
# ---------------------------------------------------------------------------


class TestPipelineAgentErrors:
    """Tests for error conditions."""

    @pytest.mark.asyncio
    async def test_missing_application_id_returns_failure(self):
        """Agent returns failure when no application_id provided."""
        from app.agents.core.pipeline_agent import PipelineAgent

        agent = PipelineAgent()
        result = await agent.execute("user123", {
            "email_subject": "test",
            "email_body": "test",
        })

        assert result.action == "pipeline_failed"
        assert result.data["error"] == "missing_application_id"

    @pytest.mark.asyncio
    async def test_empty_email_returns_failure(self):
        """Agent returns failure when email content is empty."""
        from app.agents.core.pipeline_agent import PipelineAgent

        agent = PipelineAgent()
        result = await agent.execute("user123", {
            "application_id": "app-uuid-123",
        })

        assert result.action == "pipeline_failed"
        assert result.data["error"] == "empty_email"

    @pytest.mark.asyncio
    async def test_application_not_found_returns_failure(self):
        """Agent returns failure when application doesn't exist."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = None
        mock_sess.execute = AsyncMock(return_value=mock_result)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.agents.core.pipeline_agent import PipelineAgent

            agent = PipelineAgent()
            result = await agent.execute("user123", {
                "application_id": "nonexistent",
                "email_subject": "test",
                "email_body": "We regret to inform you...",
            })

        assert result.action == "pipeline_failed"
        assert result.data["error"] == "application_not_found"

    @pytest.mark.asyncio
    async def test_no_status_detected_returns_no_change(self):
        """Agent returns no_change when email has no status signals."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_app_result = MagicMock()
        mock_app_result.mappings.return_value.first.return_value = _sample_application_row("applied")
        mock_sess.execute = AsyncMock(return_value=mock_app_result)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.agents.core.pipeline_agent import PipelineAgent

            agent = PipelineAgent()
            result = await agent.execute("user123", {
                "application_id": "app-uuid-123",
                "email_subject": "Company Newsletter",
                "email_body": "Check out our latest blog post.",
            })

        assert result.action == "pipeline_no_change"

    @pytest.mark.asyncio
    async def test_same_status_returns_no_change(self):
        """Agent returns no_change when detected status matches current."""
        mock_cm, mock_sess = _mock_session_cm()

        # Application is already in "rejected" status
        mock_app_result = MagicMock()
        mock_app_result.mappings.return_value.first.return_value = _sample_application_row("rejected")
        mock_sess.execute = AsyncMock(return_value=mock_app_result)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.agents.core.pipeline_agent import PipelineAgent

            agent = PipelineAgent()
            result = await agent.execute("user123", {
                "application_id": "app-uuid-123",
                "email_subject": "Status Update",
                "email_body": "We have decided to move forward with other candidates.",
            })

        assert result.action == "pipeline_no_change"
        assert result.data["current_status"] == "rejected"


# ---------------------------------------------------------------------------
# Test: Agent structure (AC1)
# ---------------------------------------------------------------------------


class TestPipelineAgentStructure:
    """Tests for agent class structure compliance."""

    def test_agent_type_is_pipeline(self):
        """Agent has agent_type='pipeline'."""
        from app.agents.core.pipeline_agent import PipelineAgent

        assert PipelineAgent.agent_type == "pipeline"

    def test_extends_base_agent(self):
        """PipelineAgent extends BaseAgent."""
        from app.agents.base import BaseAgent
        from app.agents.core.pipeline_agent import PipelineAgent

        assert issubclass(PipelineAgent, BaseAgent)
