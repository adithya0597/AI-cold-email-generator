"""Tests for Interview Intel Agent (Story 8-1).

Covers: agent execution, research stubs, briefing assembly,
delivery scheduling, brake check, Celery task pattern.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base import AgentOutput, BrakeActive
from app.agents.core.interview_intel_agent import InterviewIntelAgent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def agent():
    return InterviewIntelAgent()


@pytest.fixture
def base_task_data():
    return {
        "application_id": "app-123",
        "company_name": "Acme Corp",
        "role_title": "Backend Engineer",
        "seniority": "senior",
    }


@pytest.fixture
def task_data_with_interviewers(base_task_data):
    return {
        **base_task_data,
        "interviewer_names": ["Alice Smith", "Bob Jones"],
    }


@pytest.fixture
def task_data_with_datetime(base_task_data):
    future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    return {
        **base_task_data,
        "interview_datetime": future,
    }


# ---------------------------------------------------------------------------
# Task 1: InterviewIntelAgent.execute() tests
# ---------------------------------------------------------------------------


class TestInterviewIntelAgentExecute:
    @pytest.mark.asyncio
    async def test_produces_correct_output_structure(self, agent, base_task_data):
        """execute() returns AgentOutput with briefing containing all sections."""
        with patch(
            "app.agents.core.interview_intel_agent.InterviewIntelAgent._load_user_profile",
            new_callable=AsyncMock,
            return_value={"skills": ["Python", "SQL"]},
        ):
            result = await agent.execute("user-1", base_task_data)

        assert isinstance(result, AgentOutput)
        assert result.action == "interview_prep_complete"
        assert result.confidence > 0

        briefing = result.data["briefing"]
        assert briefing["application_id"] == "app-123"
        assert briefing["company_name"] == "Acme Corp"
        assert briefing["role_title"] == "Backend Engineer"
        assert "company_research" in briefing
        assert "questions" in briefing
        assert "star_suggestions" in briefing
        assert "summary" in briefing

    @pytest.mark.asyncio
    async def test_skips_interviewer_research_when_no_names(
        self, agent, base_task_data
    ):
        """execute() skips interviewer research when no names provided."""
        with patch(
            "app.agents.core.interview_intel_agent.InterviewIntelAgent._load_user_profile",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await agent.execute("user-1", base_task_data)

        briefing = result.data["briefing"]
        assert briefing["interviewer_research"] == []
        assert briefing["summary"]["interviewers_researched"] == 0

    @pytest.mark.asyncio
    async def test_includes_interviewer_research_when_names_given(
        self, agent, task_data_with_interviewers
    ):
        """execute() includes interviewer research when names are provided."""
        with patch(
            "app.agents.core.interview_intel_agent.InterviewIntelAgent._load_user_profile",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await agent.execute("user-1", task_data_with_interviewers)

        briefing = result.data["briefing"]
        assert len(briefing["interviewer_research"]) == 2
        assert briefing["interviewer_research"][0]["name"] == "Alice Smith"
        assert briefing["interviewer_research"][1]["name"] == "Bob Jones"
        assert briefing["summary"]["interviewers_researched"] == 2

    @pytest.mark.asyncio
    async def test_skips_delivery_when_no_datetime(self, agent, base_task_data):
        """execute() does not schedule delivery when interview_datetime missing."""
        with patch(
            "app.agents.core.interview_intel_agent.InterviewIntelAgent._load_user_profile",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await agent.execute("user-1", base_task_data)

        assert result.data["delivery"] == {}

    @pytest.mark.asyncio
    async def test_returns_error_when_no_application_id(self, agent):
        """execute() returns error AgentOutput when application_id missing."""
        with patch(
            "app.agents.core.interview_intel_agent.InterviewIntelAgent._load_user_profile",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await agent.execute("user-1", {})

        assert result.action == "interview_prep_failed"
        assert result.data["error"] == "missing_application_id"

    @pytest.mark.asyncio
    async def test_questions_have_all_categories(self, agent, base_task_data):
        """execute() generates questions in all 4 categories."""
        with patch(
            "app.agents.core.interview_intel_agent.InterviewIntelAgent._load_user_profile",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await agent.execute("user-1", base_task_data)

        questions = result.data["briefing"]["questions"]
        assert "behavioral" in questions
        assert "technical" in questions
        assert "company_specific" in questions
        assert "role_specific" in questions
        assert len(questions["behavioral"]) > 0

    @pytest.mark.asyncio
    async def test_star_suggestions_match_behavioral_questions(
        self, agent, base_task_data
    ):
        """STAR suggestions are generated for each behavioral question."""
        with patch(
            "app.agents.core.interview_intel_agent.InterviewIntelAgent._load_user_profile",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await agent.execute("user-1", base_task_data)

        briefing = result.data["briefing"]
        behavioral_count = len(briefing["questions"]["behavioral"])
        assert len(briefing["star_suggestions"]) == behavioral_count

        for suggestion in briefing["star_suggestions"]:
            assert "question" in suggestion
            assert "suggestions" in suggestion
            star = suggestion["suggestions"][0]
            assert "situation" in star
            assert "task" in star
            assert "action" in star
            assert "result" in star


# ---------------------------------------------------------------------------
# Task 3: Delivery scheduling tests
# ---------------------------------------------------------------------------


class TestDeliveryScheduling:
    @pytest.mark.asyncio
    async def test_schedules_24h_before(self, agent, task_data_with_datetime):
        """Delivery is scheduled 24h before interview datetime."""
        mock_task_result = MagicMock()
        mock_task_result.id = "celery-task-456"

        with patch(
            "app.agents.core.interview_intel_agent.InterviewIntelAgent._load_user_profile",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "app.worker.celery_app.celery_app"
        ) as mock_celery:
            mock_celery.send_task.return_value = mock_task_result
            result = await agent.execute("user-1", task_data_with_datetime)

        delivery = result.data["delivery"]
        assert delivery["scheduled"] is True
        assert delivery["celery_task_id"] == "celery-task-456"

        # Verify send_task was called correctly
        mock_celery.send_task.assert_called_once()
        call_args = mock_celery.send_task.call_args
        assert call_args[0][0] == "app.worker.tasks.briefing_generate"
        assert call_args[1]["kwargs"] == {"channels": ["in_app", "email"]}
        assert call_args[1]["eta"] is not None

    @pytest.mark.asyncio
    async def test_immediate_when_less_than_24h(self, agent, base_task_data):
        """Delivery is scheduled immediately when interview < 24h away."""
        soon = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        task_data = {**base_task_data, "interview_datetime": soon}

        mock_task_result = MagicMock()
        mock_task_result.id = "celery-task-789"

        with patch(
            "app.agents.core.interview_intel_agent.InterviewIntelAgent._load_user_profile",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "app.worker.celery_app.celery_app"
        ) as mock_celery:
            mock_celery.send_task.return_value = mock_task_result
            result = await agent.execute("user-1", task_data)

        delivery = result.data["delivery"]
        assert delivery["scheduled"] is True

        # Delivery time should be approximately now (not 24h before)
        delivery_dt = datetime.fromisoformat(delivery["delivery_time"])
        now = datetime.now(timezone.utc)
        assert abs((delivery_dt - now).total_seconds()) < 5

    @pytest.mark.asyncio
    async def test_invalid_datetime_skips_scheduling(self, agent, base_task_data):
        """Invalid interview_datetime results in no delivery scheduled."""
        task_data = {**base_task_data, "interview_datetime": "not-a-date"}

        with patch(
            "app.agents.core.interview_intel_agent.InterviewIntelAgent._load_user_profile",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await agent.execute("user-1", task_data)

        delivery = result.data["delivery"]
        assert delivery["scheduled"] is False
        assert delivery["reason"] == "invalid_datetime"


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
                await agent.run("user-1", {"application_id": "app-1"})


# ---------------------------------------------------------------------------
# AC5: Celery task pattern
# ---------------------------------------------------------------------------


class TestCeleryTaskPattern:
    def test_task_is_registered(self):
        """agent_interview_intel task exists in Celery app."""
        from app.worker.tasks import agent_interview_intel

        assert agent_interview_intel.name == "app.worker.tasks.agent_interview_intel"

    def test_task_queue_is_agents(self):
        """Task is routed to the 'agents' queue."""
        from app.worker.tasks import agent_interview_intel

        assert agent_interview_intel.queue == "agents"

    def test_task_has_retries(self):
        """Task has max_retries=2."""
        from app.worker.tasks import agent_interview_intel

        assert agent_interview_intel.max_retries == 2


# ---------------------------------------------------------------------------
# Confidence computation
# ---------------------------------------------------------------------------


class TestConfidenceComputation:
    def test_full_confidence(self, agent):
        """All sections present → high confidence."""
        confidence = agent._compute_confidence(
            company_research={"mission": "Build things"},
            interviewer_research=[{"name": "Alice"}],
            questions={"behavioral": ["Q1"]},
            star_suggestions=[{"question": "Q1"}],
        )
        assert confidence == 1.0

    def test_no_interviewers_still_high(self, agent):
        """No interviewer research (none expected) → still high confidence."""
        confidence = agent._compute_confidence(
            company_research={"mission": "Build things"},
            interviewer_research=[],
            questions={"behavioral": ["Q1"]},
            star_suggestions=[{"question": "Q1"}],
        )
        assert confidence == 1.0

    def test_missing_sections_lower_confidence(self, agent):
        """Missing sections reduce confidence."""
        confidence = agent._compute_confidence(
            company_research={},
            interviewer_research=[],
            questions={},
            star_suggestions=[],
        )
        assert confidence < 0.5
