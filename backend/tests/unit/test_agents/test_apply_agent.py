"""Tests for the Apply Agent (Story 5-7).

Covers: application recording, daily limit enforcement, submission method
selection, missing materials handling, and error cases.
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


def _sample_profile():
    return {
        "headline": "Senior Software Engineer",
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "experience": [
            {
                "title": "Senior Software Engineer",
                "company": "TechCorp",
                "start_date": "2021-01",
                "end_date": "Present",
                "description": "Built microservices",
            },
        ],
    }


def _sample_job_row(url="https://example.com/apply"):
    return {
        "id": "job-uuid-123",
        "title": "Backend Engineer",
        "company": "BigTech Inc",
        "description": "We need a Python developer.",
        "location": "San Francisco, CA",
        "url": url,
        "salary_min": 150000,
        "salary_max": 200000,
        "employment_type": "full-time",
        "remote": True,
    }


# ---------------------------------------------------------------------------
# Test: Happy path (AC1, AC2)
# ---------------------------------------------------------------------------


class TestApplyAgentHappyPath:
    """Tests for agent happy path."""

    @pytest.mark.asyncio
    async def test_execute_records_application_successfully(self):
        """Agent records application and returns success output."""
        # Daily limit check: 2 applications today (under limit)
        mock_limit_cm, mock_limit_sess = _mock_session_cm()
        mock_limit_result = MagicMock()
        mock_limit_result.scalar.return_value = 2
        mock_limit_sess.execute = AsyncMock(return_value=mock_limit_result)

        # Job load
        mock_job_cm, mock_job_sess = _mock_session_cm()
        mock_job_result = MagicMock()
        mock_job_result.mappings.return_value.first.return_value = _sample_job_row()
        mock_job_sess.execute = AsyncMock(return_value=mock_job_result)

        # Materials: resume found, cover letter found
        mock_mat_cm, mock_mat_sess = _mock_session_cm()
        mock_resume_result = MagicMock()
        mock_resume_result.scalar.return_value = "resume-doc-uuid"
        mock_cl_result = MagicMock()
        mock_cl_result.scalar.return_value = "cl-doc-uuid"
        mock_mat_sess.execute = AsyncMock(
            side_effect=[mock_resume_result, mock_cl_result]
        )

        # Record application
        mock_record_cm, mock_record_sess = _mock_session_cm()
        mock_record_sess.execute = AsyncMock()
        mock_record_sess.commit = AsyncMock()

        # Activity recording
        mock_activity_cm, mock_activity_sess = _mock_session_cm()
        mock_activity_sess.execute = AsyncMock()
        mock_activity_sess.commit = AsyncMock()

        session_calls = [mock_limit_cm, mock_job_cm, mock_mat_cm, mock_record_cm, mock_activity_cm]

        with (
            patch(
                "app.agents.orchestrator.get_user_context",
                new_callable=AsyncMock,
                return_value={
                    "profile": _sample_profile(),
                    "preferences": {"tier": "pro"},
                },
            ),
            patch("app.db.engine.AsyncSessionLocal", side_effect=session_calls),
        ):
            from app.agents.pro.apply_agent import ApplyAgent

            agent = ApplyAgent()
            result = await agent.execute("user123", {"job_id": "job-uuid-123"})

        assert result.action == "application_submitted"
        assert result.data["application_id"]
        assert result.data["job_id"] == "job-uuid-123"
        assert result.data["submission_method"] == "api"
        assert result.data["resume_document_id"] == "resume-doc-uuid"
        assert result.data["cover_letter_document_id"] == "cl-doc-uuid"
        assert result.confidence == 0.9


# ---------------------------------------------------------------------------
# Test: Daily limit enforcement (AC4)
# ---------------------------------------------------------------------------


class TestApplyAgentDailyLimit:
    """Tests for daily application limit enforcement."""

    @pytest.mark.asyncio
    async def test_free_tier_limit_reached(self):
        """Agent refuses when free tier user hits 5 daily applications."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5  # At limit
        mock_sess.execute = AsyncMock(return_value=mock_result)

        with (
            patch(
                "app.agents.orchestrator.get_user_context",
                new_callable=AsyncMock,
                return_value={
                    "profile": _sample_profile(),
                    "preferences": {"tier": "free"},
                },
            ),
            patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm),
        ):
            from app.agents.pro.apply_agent import ApplyAgent

            agent = ApplyAgent()
            result = await agent.execute("user123", {"job_id": "job-uuid-123"})

        assert result.action == "application_failed"
        assert result.data["error"] == "daily_limit_reached"
        assert result.data["daily_limit"] == 5
        assert result.data["today_count"] == 5

    @pytest.mark.asyncio
    async def test_pro_tier_limit_not_reached(self):
        """Pro tier user with 24 applications today can still apply."""
        # Daily limit: 24 < 25
        mock_limit_cm, mock_limit_sess = _mock_session_cm()
        mock_limit_result = MagicMock()
        mock_limit_result.scalar.return_value = 24
        mock_limit_sess.execute = AsyncMock(return_value=mock_limit_result)

        # Job load
        mock_job_cm, mock_job_sess = _mock_session_cm()
        mock_job_result = MagicMock()
        mock_job_result.mappings.return_value.first.return_value = _sample_job_row()
        mock_job_sess.execute = AsyncMock(return_value=mock_job_result)

        # Materials
        mock_mat_cm, mock_mat_sess = _mock_session_cm()
        mock_resume = MagicMock()
        mock_resume.scalar.return_value = "resume-id"
        mock_cl = MagicMock()
        mock_cl.scalar.return_value = None
        mock_mat_sess.execute = AsyncMock(side_effect=[mock_resume, mock_cl])

        # Record
        mock_rec_cm, mock_rec_sess = _mock_session_cm()
        mock_rec_sess.execute = AsyncMock()
        mock_rec_sess.commit = AsyncMock()

        # Activity
        mock_act_cm, mock_act_sess = _mock_session_cm()
        mock_act_sess.execute = AsyncMock()
        mock_act_sess.commit = AsyncMock()

        session_calls = [mock_limit_cm, mock_job_cm, mock_mat_cm, mock_rec_cm, mock_act_cm]

        with (
            patch(
                "app.agents.orchestrator.get_user_context",
                new_callable=AsyncMock,
                return_value={
                    "profile": _sample_profile(),
                    "preferences": {"tier": "pro"},
                },
            ),
            patch("app.db.engine.AsyncSessionLocal", side_effect=session_calls),
        ):
            from app.agents.pro.apply_agent import ApplyAgent

            agent = ApplyAgent()
            result = await agent.execute("user123", {"job_id": "job-uuid-123"})

        assert result.action == "application_submitted"

    def test_daily_limits_constants(self):
        """Verify daily limit constants match spec."""
        from app.agents.pro.apply_agent import DAILY_APPLICATION_LIMITS

        assert DAILY_APPLICATION_LIMITS["free"] == 5
        assert DAILY_APPLICATION_LIMITS["pro"] == 25
        assert DAILY_APPLICATION_LIMITS["h1b_pro"] == 25
        assert DAILY_APPLICATION_LIMITS["career_insurance"] == 50
        assert DAILY_APPLICATION_LIMITS["enterprise"] == 100


# ---------------------------------------------------------------------------
# Test: Submission method selection (AC3)
# ---------------------------------------------------------------------------


class TestApplyAgentMethodSelection:
    """Tests for submission method selection."""

    def test_api_method_when_url_present(self):
        """Selects 'api' when job has application URL."""
        from app.agents.pro.apply_agent import ApplyAgent

        agent = ApplyAgent()
        job = {"url": "https://example.com/apply", "description": "Job desc"}
        assert agent._select_submission_method(job) == "api"

    def test_email_fallback_when_email_in_description(self):
        """Selects 'email_fallback' when description has email."""
        from app.agents.pro.apply_agent import ApplyAgent

        agent = ApplyAgent()
        job = {
            "url": "",
            "description": "Send resume to hr@bigtech.com for consideration.",
        }
        assert agent._select_submission_method(job) == "email_fallback"

    def test_manual_required_when_no_url_or_email(self):
        """Returns 'manual_required' when no automated method available."""
        from app.agents.pro.apply_agent import ApplyAgent

        agent = ApplyAgent()
        job = {"url": "", "description": "Apply through our internal portal."}
        assert agent._select_submission_method(job) == "manual_required"

    def test_api_takes_priority_over_email(self):
        """When both URL and email present, api takes priority."""
        from app.agents.pro.apply_agent import ApplyAgent

        agent = ApplyAgent()
        job = {
            "url": "https://example.com/apply",
            "description": "Or email hr@bigtech.com",
        }
        assert agent._select_submission_method(job) == "api"


# ---------------------------------------------------------------------------
# Test: Error handling
# ---------------------------------------------------------------------------


class TestApplyAgentErrorHandling:
    """Tests for agent error handling."""

    @pytest.mark.asyncio
    async def test_missing_job_id_returns_failure(self):
        """Agent returns failure when no job_id provided."""
        from app.agents.pro.apply_agent import ApplyAgent

        agent = ApplyAgent()
        result = await agent.execute("user123", {})

        assert result.action == "application_failed"
        assert result.data["error"] == "missing_job_id"

    @pytest.mark.asyncio
    async def test_empty_profile_returns_failure(self):
        """Agent returns failure when user has no profile data."""
        with patch(
            "app.agents.orchestrator.get_user_context",
            new_callable=AsyncMock,
            return_value={"profile": {}, "preferences": {}},
        ):
            from app.agents.pro.apply_agent import ApplyAgent

            agent = ApplyAgent()
            result = await agent.execute("user123", {"job_id": "job-uuid-123"})

        assert result.action == "application_failed"
        assert result.data["error"] == "empty_profile"

    @pytest.mark.asyncio
    async def test_job_not_found_returns_failure(self):
        """Agent returns failure when job doesn't exist."""
        # Limit check passes
        mock_limit_cm, mock_limit_sess = _mock_session_cm()
        mock_limit_result = MagicMock()
        mock_limit_result.scalar.return_value = 0
        mock_limit_sess.execute = AsyncMock(return_value=mock_limit_result)

        # Job not found
        mock_job_cm, mock_job_sess = _mock_session_cm()
        mock_job_result = MagicMock()
        mock_job_result.mappings.return_value.first.return_value = None
        mock_job_sess.execute = AsyncMock(return_value=mock_job_result)

        # Failure activity
        mock_fail_cm, mock_fail_sess = _mock_session_cm()
        mock_fail_sess.execute = AsyncMock()
        mock_fail_sess.commit = AsyncMock()

        with (
            patch(
                "app.agents.orchestrator.get_user_context",
                new_callable=AsyncMock,
                return_value={
                    "profile": _sample_profile(),
                    "preferences": {"tier": "free"},
                },
            ),
            patch(
                "app.db.engine.AsyncSessionLocal",
                side_effect=[mock_limit_cm, mock_job_cm, mock_fail_cm],
            ),
        ):
            from app.agents.pro.apply_agent import ApplyAgent

            agent = ApplyAgent()
            result = await agent.execute("user123", {"job_id": "nonexistent"})

        assert result.action == "application_failed"
        assert result.data["error"] == "job_not_found"

    @pytest.mark.asyncio
    async def test_missing_materials_returns_failure(self):
        """Agent returns failure when no resume available for this job."""
        # Limit check passes
        mock_limit_cm, mock_limit_sess = _mock_session_cm()
        mock_limit_result = MagicMock()
        mock_limit_result.scalar.return_value = 0
        mock_limit_sess.execute = AsyncMock(return_value=mock_limit_result)

        # Job found
        mock_job_cm, mock_job_sess = _mock_session_cm()
        mock_job_result = MagicMock()
        mock_job_result.mappings.return_value.first.return_value = _sample_job_row()
        mock_job_sess.execute = AsyncMock(return_value=mock_job_result)

        # Materials: no resume
        mock_mat_cm, mock_mat_sess = _mock_session_cm()
        mock_resume = MagicMock()
        mock_resume.scalar.return_value = None
        mock_mat_sess.execute = AsyncMock(return_value=mock_resume)

        # Failure activity
        mock_fail_cm, mock_fail_sess = _mock_session_cm()
        mock_fail_sess.execute = AsyncMock()
        mock_fail_sess.commit = AsyncMock()

        with (
            patch(
                "app.agents.orchestrator.get_user_context",
                new_callable=AsyncMock,
                return_value={
                    "profile": _sample_profile(),
                    "preferences": {"tier": "free"},
                },
            ),
            patch(
                "app.db.engine.AsyncSessionLocal",
                side_effect=[mock_limit_cm, mock_job_cm, mock_mat_cm, mock_fail_cm],
            ),
        ):
            from app.agents.pro.apply_agent import ApplyAgent

            agent = ApplyAgent()
            result = await agent.execute("user123", {"job_id": "job-uuid-123"})

        assert result.action == "application_failed"
        assert result.data["error"] == "missing_materials"

    @pytest.mark.asyncio
    async def test_manual_required_returns_failure(self):
        """Agent returns failure when no automated method available."""
        # Limit check passes
        mock_limit_cm, mock_limit_sess = _mock_session_cm()
        mock_limit_result = MagicMock()
        mock_limit_result.scalar.return_value = 0
        mock_limit_sess.execute = AsyncMock(return_value=mock_limit_result)

        # Job with no URL and no email
        mock_job_cm, mock_job_sess = _mock_session_cm()
        job = _sample_job_row(url="")
        job["description"] = "Apply through our portal."
        mock_job_result = MagicMock()
        mock_job_result.mappings.return_value.first.return_value = job
        mock_job_sess.execute = AsyncMock(return_value=mock_job_result)

        # Failure activity
        mock_fail_cm, mock_fail_sess = _mock_session_cm()
        mock_fail_sess.execute = AsyncMock()
        mock_fail_sess.commit = AsyncMock()

        with (
            patch(
                "app.agents.orchestrator.get_user_context",
                new_callable=AsyncMock,
                return_value={
                    "profile": _sample_profile(),
                    "preferences": {"tier": "free"},
                },
            ),
            patch(
                "app.db.engine.AsyncSessionLocal",
                side_effect=[mock_limit_cm, mock_job_cm, mock_fail_cm],
            ),
        ):
            from app.agents.pro.apply_agent import ApplyAgent

            agent = ApplyAgent()
            result = await agent.execute("user123", {"job_id": "job-uuid-123"})

        assert result.action == "application_failed"
        assert result.data["error"] == "manual_required"


# ---------------------------------------------------------------------------
# Test: Submission confirmation activity (5-10 AC1, AC2)
# ---------------------------------------------------------------------------


class TestApplyAgentSubmissionConfirmation:
    """Tests for activity recording on successful submission."""

    @pytest.mark.asyncio
    async def test_activity_recorded_on_success(self):
        """Agent records agent_activity with job details on success."""
        # Daily limit
        mock_limit_cm, mock_limit_sess = _mock_session_cm()
        mock_limit_result = MagicMock()
        mock_limit_result.scalar.return_value = 0
        mock_limit_sess.execute = AsyncMock(return_value=mock_limit_result)

        # Job
        mock_job_cm, mock_job_sess = _mock_session_cm()
        mock_job_result = MagicMock()
        mock_job_result.mappings.return_value.first.return_value = _sample_job_row()
        mock_job_sess.execute = AsyncMock(return_value=mock_job_result)

        # Materials
        mock_mat_cm, mock_mat_sess = _mock_session_cm()
        mock_resume = MagicMock()
        mock_resume.scalar.return_value = "resume-uuid"
        mock_cl = MagicMock()
        mock_cl.scalar.return_value = "cl-uuid"
        mock_mat_sess.execute = AsyncMock(side_effect=[mock_resume, mock_cl])

        # Record application
        mock_rec_cm, mock_rec_sess = _mock_session_cm()
        mock_rec_sess.execute = AsyncMock()
        mock_rec_sess.commit = AsyncMock()

        # Activity recording
        mock_act_cm, mock_act_sess = _mock_session_cm()
        mock_act_sess.execute = AsyncMock()
        mock_act_sess.commit = AsyncMock()

        session_calls = [mock_limit_cm, mock_job_cm, mock_mat_cm, mock_rec_cm, mock_act_cm]

        with (
            patch(
                "app.agents.orchestrator.get_user_context",
                new_callable=AsyncMock,
                return_value={
                    "profile": _sample_profile(),
                    "preferences": {"tier": "pro"},
                },
            ),
            patch("app.db.engine.AsyncSessionLocal", side_effect=session_calls),
        ):
            from app.agents.pro.apply_agent import ApplyAgent

            agent = ApplyAgent()
            result = await agent.execute("user123", {"job_id": "job-uuid-123"})

        assert result.action == "application_submitted"

        # Verify activity was recorded
        activity_call = mock_act_sess.execute.call_args_list[0]
        sql_params = activity_call[0][1]
        assert sql_params["event_type"] == "agent.apply.completed"
        assert sql_params["agent_type"] == "apply"
        assert sql_params["severity"] == "info"
        assert "Backend Engineer" in sql_params["title"]
        assert "BigTech Inc" in sql_params["title"]

    @pytest.mark.asyncio
    async def test_activity_data_includes_required_fields(self):
        """Activity data JSON includes job title, company, method, material IDs."""
        import json

        # Same setup as above but we inspect the data field
        mock_limit_cm, mock_limit_sess = _mock_session_cm()
        mock_limit_result = MagicMock()
        mock_limit_result.scalar.return_value = 0
        mock_limit_sess.execute = AsyncMock(return_value=mock_limit_result)

        mock_job_cm, mock_job_sess = _mock_session_cm()
        mock_job_result = MagicMock()
        mock_job_result.mappings.return_value.first.return_value = _sample_job_row()
        mock_job_sess.execute = AsyncMock(return_value=mock_job_result)

        mock_mat_cm, mock_mat_sess = _mock_session_cm()
        mock_resume = MagicMock()
        mock_resume.scalar.return_value = "resume-uuid"
        mock_cl = MagicMock()
        mock_cl.scalar.return_value = None
        mock_mat_sess.execute = AsyncMock(side_effect=[mock_resume, mock_cl])

        mock_rec_cm, mock_rec_sess = _mock_session_cm()
        mock_rec_sess.execute = AsyncMock()
        mock_rec_sess.commit = AsyncMock()

        mock_act_cm, mock_act_sess = _mock_session_cm()
        mock_act_sess.execute = AsyncMock()
        mock_act_sess.commit = AsyncMock()

        session_calls = [mock_limit_cm, mock_job_cm, mock_mat_cm, mock_rec_cm, mock_act_cm]

        with (
            patch(
                "app.agents.orchestrator.get_user_context",
                new_callable=AsyncMock,
                return_value={
                    "profile": _sample_profile(),
                    "preferences": {"tier": "pro"},
                },
            ),
            patch("app.db.engine.AsyncSessionLocal", side_effect=session_calls),
        ):
            from app.agents.pro.apply_agent import ApplyAgent

            agent = ApplyAgent()
            await agent.execute("user123", {"job_id": "job-uuid-123"})

        # Parse the data JSON from activity insert
        activity_call = mock_act_sess.execute.call_args_list[0]
        data_json = activity_call[0][1]["data"]
        data = json.loads(data_json)

        assert data["job_title"] == "Backend Engineer"
        assert data["company"] == "BigTech Inc"
        assert data["submission_method"] == "api"
        assert data["resume_document_id"] == "resume-uuid"
        assert data["cover_letter_document_id"] is None


# ---------------------------------------------------------------------------
# Test: Failure activity recording (5-11 AC1, AC2)
# ---------------------------------------------------------------------------


class TestApplyAgentFailureActivity:
    """Tests for failure activity recording."""

    @pytest.mark.asyncio
    async def test_failure_activity_recorded_for_manual_required(self):
        """Failure activity is recorded with warning severity for manual_required."""
        import json

        mock_limit_cm, mock_limit_sess = _mock_session_cm()
        mock_limit_result = MagicMock()
        mock_limit_result.scalar.return_value = 0
        mock_limit_sess.execute = AsyncMock(return_value=mock_limit_result)

        mock_job_cm, mock_job_sess = _mock_session_cm()
        job = _sample_job_row(url="")
        job["description"] = "Apply via internal portal."
        mock_job_result = MagicMock()
        mock_job_result.mappings.return_value.first.return_value = job
        mock_job_sess.execute = AsyncMock(return_value=mock_job_result)

        mock_fail_cm, mock_fail_sess = _mock_session_cm()
        mock_fail_sess.execute = AsyncMock()
        mock_fail_sess.commit = AsyncMock()

        with (
            patch(
                "app.agents.orchestrator.get_user_context",
                new_callable=AsyncMock,
                return_value={
                    "profile": _sample_profile(),
                    "preferences": {"tier": "free"},
                },
            ),
            patch(
                "app.db.engine.AsyncSessionLocal",
                side_effect=[mock_limit_cm, mock_job_cm, mock_fail_cm],
            ),
        ):
            from app.agents.pro.apply_agent import ApplyAgent

            agent = ApplyAgent()
            result = await agent.execute("user123", {"job_id": "job-uuid-123"})

        assert result.action == "application_failed"

        # Verify failure activity was recorded
        fail_call = mock_fail_sess.execute.call_args_list[0]
        params = fail_call[0][1]
        assert params["event_type"] == "agent.apply.failed"
        assert params["severity"] == "warning"
        assert "manual_required" in params["title"]

        data = json.loads(params["data"])
        assert data["error"] == "manual_required"
        assert data["job_title"] == "Backend Engineer"

    @pytest.mark.asyncio
    async def test_failure_does_not_create_application_record(self):
        """Failed applications don't insert into applications table (don't count against limit)."""
        mock_limit_cm, mock_limit_sess = _mock_session_cm()
        mock_limit_result = MagicMock()
        mock_limit_result.scalar.return_value = 0
        mock_limit_sess.execute = AsyncMock(return_value=mock_limit_result)

        mock_job_cm, mock_job_sess = _mock_session_cm()
        mock_job_result = MagicMock()
        mock_job_result.mappings.return_value.first.return_value = None
        mock_job_sess.execute = AsyncMock(return_value=mock_job_result)

        mock_fail_cm, mock_fail_sess = _mock_session_cm()
        mock_fail_sess.execute = AsyncMock()
        mock_fail_sess.commit = AsyncMock()

        with (
            patch(
                "app.agents.orchestrator.get_user_context",
                new_callable=AsyncMock,
                return_value={
                    "profile": _sample_profile(),
                    "preferences": {"tier": "free"},
                },
            ),
            patch(
                "app.db.engine.AsyncSessionLocal",
                side_effect=[mock_limit_cm, mock_job_cm, mock_fail_cm],
            ),
        ):
            from app.agents.pro.apply_agent import ApplyAgent

            agent = ApplyAgent()
            result = await agent.execute("user123", {"job_id": "nonexistent"})

        assert result.action == "application_failed"
        # Only 3 sessions used: limit check, job load, failure activity
        # NO applications table insert occurred


# ---------------------------------------------------------------------------
# Test: Indeed Easy Apply integration (5-12 AC1, AC2, AC3)
# ---------------------------------------------------------------------------


class TestApplyAgentIndeed:
    """Tests for Indeed Easy Apply integration."""

    def test_indeed_source_detected(self):
        """Jobs with source='indeed' get indeed_easy_apply method."""
        from app.agents.pro.apply_agent import ApplyAgent

        agent = ApplyAgent()
        job = {"source": "indeed", "url": "https://indeed.com/apply/123", "description": ""}
        assert agent._select_submission_method(job) == "indeed_easy_apply"

    def test_non_indeed_source_gets_api(self):
        """Jobs with other sources and URL get 'api' method."""
        from app.agents.pro.apply_agent import ApplyAgent

        agent = ApplyAgent()
        job = {"source": "linkedin", "url": "https://linkedin.com/apply", "description": ""}
        assert agent._select_submission_method(job) == "api"

    def test_build_indeed_payload(self):
        """Indeed payload includes required fields."""
        from app.agents.pro.apply_agent import ApplyAgent

        agent = ApplyAgent()
        profile = {"headline": "Senior Engineer"}
        job = {"id": "job-123", "url": "https://indeed.com/apply/123"}
        materials = {"resume_document_id": "res-uuid", "cover_letter_document_id": "cl-uuid"}

        payload = agent._build_indeed_payload(profile, job, materials)

        assert payload["source"] == "indeed"
        assert payload["job_url"] == "https://indeed.com/apply/123"
        assert payload["applicant_name"] == "Senior Engineer"
        assert payload["resume_document_id"] == "res-uuid"

    @pytest.mark.asyncio
    async def test_indeed_daily_limit_check(self):
        """Indeed limit check returns False when at 50 applications."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 50
        mock_sess.execute = AsyncMock(return_value=mock_result)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.agents.pro.apply_agent import ApplyAgent

            agent = ApplyAgent()
            under_limit = await agent._check_indeed_limit("user123")

        assert under_limit is False

    @pytest.mark.asyncio
    async def test_indeed_daily_limit_under(self):
        """Indeed limit check returns True when under 50."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 10
        mock_sess.execute = AsyncMock(return_value=mock_result)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.agents.pro.apply_agent import ApplyAgent

            agent = ApplyAgent()
            under_limit = await agent._check_indeed_limit("user123")

        assert under_limit is True

    def test_indeed_daily_limit_constant(self):
        """Verify INDEED_DAILY_LIMIT is 50."""
        from app.agents.pro.apply_agent import INDEED_DAILY_LIMIT

        assert INDEED_DAILY_LIMIT == 50
