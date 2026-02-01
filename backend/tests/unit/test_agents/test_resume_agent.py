"""Tests for the Resume Agent (Story 5-1).

Covers: LLM tailoring, document storage, AgentOutput structure,
job analysis, keyword gap calculation, brake integration, error handling,
and anti-hallucination system prompt verification.
"""

import json
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


def _sample_profile():
    return {
        "headline": "Senior Software Engineer",
        "skills": ["Python", "FastAPI", "PostgreSQL", "React", "Docker"],
        "experience": [
            {
                "title": "Senior Software Engineer",
                "company": "TechCorp",
                "start_date": "2021-01",
                "end_date": "Present",
                "description": "Built microservices with Python and FastAPI",
            },
            {
                "title": "Software Engineer",
                "company": "StartupInc",
                "start_date": "2018-06",
                "end_date": "2020-12",
                "description": "Full-stack development with React and Node.js",
            },
        ],
        "education": [
            {
                "institution": "MIT",
                "degree": "BS",
                "field": "Computer Science",
                "graduation_year": "2018",
            }
        ],
    }


def _sample_job_row():
    return {
        "id": "job-uuid-123",
        "title": "Backend Engineer",
        "company": "BigTech Inc",
        "description": (
            "We are looking for a backend engineer with experience in Python, "
            "FastAPI, PostgreSQL, and distributed systems. The ideal candidate "
            "has 3+ years of experience building scalable APIs."
        ),
        "location": "San Francisco, CA",
        "salary_min": 150000,
        "salary_max": 200000,
        "employment_type": "full-time",
        "remote": True,
    }


def _sample_tailored_resume():
    from app.agents.pro.resume_agent import TailoredResume, TailoredSection

    return TailoredResume(
        sections=[
            TailoredSection(
                section_name="summary",
                original_content="Senior Software Engineer with 5 years experience",
                tailored_content="Senior Backend Engineer with 5 years building scalable Python APIs",
                changes_made=["Reframed as backend-focused", "Added API emphasis"],
            ),
            TailoredSection(
                section_name="experience",
                original_content="Built microservices with Python and FastAPI",
                tailored_content="Designed and built distributed microservices using Python and FastAPI, serving 10K+ requests/sec",
                changes_made=["Added scale metrics", "Emphasized distributed systems"],
            ),
            TailoredSection(
                section_name="skills",
                original_content="Python, FastAPI, PostgreSQL, React, Docker",
                tailored_content="Python, FastAPI, PostgreSQL, Docker, Distributed Systems",
                changes_made=["Reordered for relevance", "Added distributed systems keyword"],
            ),
        ],
        keywords_incorporated=["python", "fastapi", "postgresql", "backend", "scalable"],
        keywords_missing=["distributed systems", "kubernetes"],
        ats_score=82,
        tailoring_rationale="Emphasized backend and API experience to match Backend Engineer role at BigTech Inc",
    )


# ---------------------------------------------------------------------------
# Test: Happy path
# ---------------------------------------------------------------------------


class TestResumeAgentHappyPath:
    """Tests for the full execute() workflow."""

    @pytest.mark.asyncio
    async def test_execute_happy_path(self):
        """Agent loads job, calls LLM, stores document, returns AgentOutput."""
        mock_cm, mock_sess = _mock_session_cm()
        tailored = _sample_tailored_resume()

        # Mock job query result
        mock_job_result = MagicMock()
        mock_job_result.mappings.return_value.first.return_value = _sample_job_row()

        # Mock version query result
        mock_version_result = MagicMock()
        mock_version_result.scalar.return_value = 1

        mock_sess.execute = AsyncMock(side_effect=[mock_job_result, mock_version_result, None])
        mock_sess.commit = AsyncMock()

        # Mock OpenAI
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(parsed=tailored))]
        mock_completion.usage = MagicMock(prompt_tokens=500, completion_tokens=300)

        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_completion)

        mock_context = AsyncMock(return_value={
            "profile": _sample_profile(),
            "preferences": {},
        })

        with (
            patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm),
            patch("app.agents.orchestrator.get_user_context", mock_context),
            patch("openai.AsyncOpenAI", return_value=mock_client),
            patch("app.observability.cost_tracker.track_llm_cost", new_callable=AsyncMock),
        ):
            from app.agents.pro.resume_agent import ResumeAgent

            agent = ResumeAgent()
            output = await agent.execute(user_id="user_test_123", task_data={"job_id": "job-uuid-123"})

        assert output.action == "resume_tailored"
        assert output.data["ats_score"] == 82
        assert "document_id" in output.data
        assert "sections_modified" in output.data
        assert "keyword_gaps" in output.data
        assert output.confidence == 0.82


# ---------------------------------------------------------------------------
# Test: Job analysis
# ---------------------------------------------------------------------------


class TestJobAnalysis:
    """Tests for _analyze_job helper."""

    def test_analyze_job_extracts_keywords(self):
        from app.agents.pro.resume_agent import ResumeAgent

        agent = ResumeAgent()
        job = _sample_job_row()
        analysis = agent._analyze_job(job)

        assert analysis["title"] == "Backend Engineer"
        assert analysis["company"] == "BigTech Inc"
        assert len(analysis["keywords"]) > 0
        assert "python" in analysis["keywords"]

    def test_analyze_job_handles_empty_description(self):
        from app.agents.pro.resume_agent import ResumeAgent

        agent = ResumeAgent()
        job = {"title": "Engineer", "company": "Co", "description": ""}
        analysis = agent._analyze_job(job)

        assert analysis["title"] == "Engineer"
        assert analysis["keywords"] == []


# ---------------------------------------------------------------------------
# Test: Keyword gap calculation
# ---------------------------------------------------------------------------


class TestKeywordGaps:
    """Tests for _calculate_keyword_gaps helper."""

    def test_keyword_gaps_identifies_matches_and_missing(self):
        from app.agents.pro.resume_agent import ResumeAgent

        agent = ResumeAgent()
        job_analysis = {"keywords": ["python", "fastapi", "kubernetes", "react"]}
        tailored = _sample_tailored_resume()

        gaps = agent._calculate_keyword_gaps(job_analysis, tailored)

        assert "python" in gaps["matched"]
        assert "fastapi" in gaps["matched"]
        assert isinstance(gaps["match_rate"], float)
        assert 0 <= gaps["match_rate"] <= 1

    def test_keyword_gaps_empty_keywords(self):
        from app.agents.pro.resume_agent import ResumeAgent

        agent = ResumeAgent()
        job_analysis = {"keywords": []}
        tailored = _sample_tailored_resume()

        gaps = agent._calculate_keyword_gaps(job_analysis, tailored)
        assert gaps["match_rate"] == 0  # 0/max(0,1) = 0


# ---------------------------------------------------------------------------
# Test: Document version incrementing
# ---------------------------------------------------------------------------


class TestDocumentStorage:
    """Tests for _store_document with version incrementing."""

    @pytest.mark.asyncio
    async def test_store_document_increments_version(self):
        """Second tailoring for same job gets version=2."""
        mock_cm, mock_sess = _mock_session_cm()

        # First call: version query returns 2 (meaning existing version 1)
        mock_version_result = MagicMock()
        mock_version_result.scalar.return_value = 2
        mock_sess.execute = AsyncMock(side_effect=[mock_version_result, None])
        mock_sess.commit = AsyncMock()

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.agents.pro.resume_agent import ResumeAgent

            agent = ResumeAgent()
            tailored = _sample_tailored_resume()
            doc_id = await agent._store_document("user_test_123", "job-uuid-123", tailored)

        assert doc_id  # Non-empty string
        # Verify the INSERT was called with version=2
        insert_call = mock_sess.execute.call_args_list[1]
        params = insert_call[0][1] if len(insert_call[0]) > 1 else insert_call[1].get("parameters", {})
        assert params["ver"] == 2


# ---------------------------------------------------------------------------
# Test: Brake check integration
# ---------------------------------------------------------------------------


class TestBrakeIntegration:
    """Tests that brake check is handled by BaseAgent.run()."""

    @pytest.mark.asyncio
    async def test_brake_active_raises(self):
        """When brake is active, run() raises BrakeActive."""
        with patch("app.agents.brake.check_brake", new_callable=AsyncMock, return_value=True):
            from app.agents.base import BrakeActive
            from app.agents.pro.resume_agent import ResumeAgent

            agent = ResumeAgent()
            with pytest.raises(BrakeActive):
                await agent.run(user_id="user_test_123", task_data={"job_id": "job-uuid-123"})


# ---------------------------------------------------------------------------
# Test: LLM failure graceful handling
# ---------------------------------------------------------------------------


class TestLLMFailure:
    """Tests for graceful error handling when LLM fails."""

    @pytest.mark.asyncio
    async def test_llm_failure_returns_error_output(self):
        """When LLM raises, agent returns a failure AgentOutput instead of crashing."""
        mock_cm, mock_sess = _mock_session_cm()

        # Mock job query
        mock_job_result = MagicMock()
        mock_job_result.mappings.return_value.first.return_value = _sample_job_row()
        mock_sess.execute = AsyncMock(return_value=mock_job_result)

        # Mock OpenAI to raise
        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse = AsyncMock(
            side_effect=Exception("LLM rate limited")
        )

        mock_context = AsyncMock(return_value={
            "profile": _sample_profile(),
            "preferences": {},
        })

        with (
            patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm),
            patch("app.agents.orchestrator.get_user_context", mock_context),
            patch("openai.AsyncOpenAI", return_value=mock_client),
        ):
            from app.agents.pro.resume_agent import ResumeAgent

            agent = ResumeAgent()
            output = await agent.execute(
                user_id="user_test_123", task_data={"job_id": "job-uuid-123"}
            )

        assert output.action == "resume_tailoring_failed"
        assert output.data["error"] == "llm_failure"
        assert output.confidence == 0.0

    @pytest.mark.asyncio
    async def test_missing_job_id_returns_error(self):
        """When no job_id in task_data, returns error output."""
        mock_context = AsyncMock(return_value={
            "profile": _sample_profile(),
            "preferences": {},
        })

        with patch("app.agents.orchestrator.get_user_context", mock_context):
            from app.agents.pro.resume_agent import ResumeAgent

            agent = ResumeAgent()
            output = await agent.execute(user_id="user_test_123", task_data={})

        assert output.action == "resume_tailoring_failed"
        assert output.data["error"] == "missing_job_id"

    @pytest.mark.asyncio
    async def test_empty_profile_returns_error(self):
        """When user has no profile data, returns error output."""
        mock_context = AsyncMock(return_value={
            "profile": {},
            "preferences": {},
        })

        with patch("app.agents.orchestrator.get_user_context", mock_context):
            from app.agents.pro.resume_agent import ResumeAgent

            agent = ResumeAgent()
            output = await agent.execute(
                user_id="user_test_123", task_data={"job_id": "job-uuid-123"}
            )

        assert output.action == "resume_tailoring_failed"
        assert output.data["error"] == "empty_profile"

    @pytest.mark.asyncio
    async def test_job_not_found_returns_error(self):
        """When job doesn't exist in DB, returns error output."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_job_result = MagicMock()
        mock_job_result.mappings.return_value.first.return_value = None
        mock_sess.execute = AsyncMock(return_value=mock_job_result)

        mock_context = AsyncMock(return_value={
            "profile": _sample_profile(),
            "preferences": {},
        })

        with (
            patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm),
            patch("app.agents.orchestrator.get_user_context", mock_context),
        ):
            from app.agents.pro.resume_agent import ResumeAgent

            agent = ResumeAgent()
            output = await agent.execute(
                user_id="user_test_123", task_data={"job_id": "nonexistent"}
            )

        assert output.action == "resume_tailoring_failed"
        assert output.data["error"] == "job_not_found"


# ---------------------------------------------------------------------------
# Test: Anti-hallucination system prompt
# ---------------------------------------------------------------------------


class TestAntiHallucination:
    """Tests that the system prompt contains anti-hallucination instructions."""

    def test_system_prompt_contains_never_invent(self):
        from app.agents.pro.resume_agent import _SYSTEM_PROMPT

        assert "NEVER invent" in _SYSTEM_PROMPT
        assert "fabricate" in _SYSTEM_PROMPT
        assert "embellish" in _SYSTEM_PROMPT

    def test_system_prompt_contains_only_use_existing(self):
        from app.agents.pro.resume_agent import _SYSTEM_PROMPT

        assert "ONLY use experience, skills, and qualifications present" in _SYSTEM_PROMPT
