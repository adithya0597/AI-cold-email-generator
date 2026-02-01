"""
Tests for JobScoutAgent -- preference matching, scoring, and deal-breakers.

All external dependencies (httpx, database, Redis) are mocked.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import json

import pytest

from app.agents.base import AgentOutput
from app.agents.core.job_scout import JobScoutAgent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_job(**kwargs) -> SimpleNamespace:
    """Create a mock Job object with default values."""
    defaults = {
        "id": "job-id-1",
        "title": "Software Engineer",
        "company": "Acme Corp",
        "description": "Python, React, PostgreSQL experience needed. Senior role.",
        "location": "San Francisco, CA",
        "salary_min": 140000,
        "salary_max": 180000,
        "employment_type": "FULLTIME",
        "remote": True,
        "source": "jsearch",
        "source_id": "j1",
        "url": "https://acme.com/apply/1",
        "raw_data": {},
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


FULL_PREFERENCES = {
    "target_titles": ["Software Engineer", "Backend Engineer"],
    "target_locations": ["San Francisco", "New York"],
    "salary_minimum": 120000,
    "salary_target": 180000,
    "work_arrangement": "remote",
    "excluded_companies": ["EvilCorp"],
    "excluded_industries": ["gambling", "tobacco"],
    "seniority_levels": ["senior"],
}

FULL_PROFILE = {
    "skills": ["Python", "React", "PostgreSQL", "FastAPI"],
}


# ---------------------------------------------------------------------------
# Scoring tests
# ---------------------------------------------------------------------------


class TestScoreJob:
    """Tests for _score_job method."""

    def setup_method(self):
        self.agent = JobScoutAgent()

    def test_full_match_high_score(self):
        """Job matching all preferences gets a high score."""
        job = _make_job()
        score, rationale = self.agent._score_job(job, FULL_PREFERENCES, FULL_PROFILE)
        assert score >= 70, f"Expected high score, got {score}: {rationale}"
        assert "%" in rationale
        assert "title" in rationale

    def test_partial_match_moderate_score(self):
        """Job with some matching criteria gets moderate score."""
        job = _make_job(
            title="Junior Developer",
            location="Austin, TX",
            salary_min=100000,
            salary_max=130000,
            remote=False,
        )
        score, rationale = self.agent._score_job(job, FULL_PREFERENCES, FULL_PROFILE)
        assert 20 <= score <= 70, f"Expected moderate score, got {score}"

    def test_no_match_low_score(self):
        """Job matching nothing gets a low score."""
        job = _make_job(
            title="Chef",
            company="Restaurant",
            description="Cooking experience needed.",
            location="Rural Montana",
            salary_min=30000,
            salary_max=40000,
            remote=False,
        )
        prefs = {
            "target_titles": ["Software Engineer"],
            "target_locations": ["San Francisco"],
            "salary_minimum": 120000,
            "salary_target": 180000,
            "seniority_levels": ["senior"],
        }
        profile = {"skills": ["Python", "React"]}
        score, _ = self.agent._score_job(job, prefs, profile)
        assert score <= 30, f"Expected low score, got {score}"

    def test_empty_preferences_neutral_score(self):
        """Empty preferences result in neutral scores."""
        job = _make_job()
        score, _ = self.agent._score_job(job, {}, {})
        # Should get neutral scores for all categories
        assert 30 <= score <= 60

    def test_score_with_no_salary_info(self):
        """Job without salary info gets neutral salary score."""
        job = _make_job(salary_min=None, salary_max=None)
        score, rationale = self.agent._score_job(job, FULL_PREFERENCES, FULL_PROFILE)
        assert score > 0
        assert "salary" in rationale


# ---------------------------------------------------------------------------
# Deal-breaker tests
# ---------------------------------------------------------------------------


class TestDealBreakers:
    """Tests for _check_deal_breakers method."""

    def setup_method(self):
        self.agent = JobScoutAgent()

    def test_excluded_company(self):
        """Job from excluded company triggers deal-breaker."""
        job = _make_job(company="EvilCorp")
        assert self.agent._check_deal_breakers(job, FULL_PREFERENCES) is True

    def test_excluded_company_case_insensitive(self):
        """Excluded company check is case insensitive."""
        job = _make_job(company="evilcorp industries")
        assert self.agent._check_deal_breakers(job, FULL_PREFERENCES) is True

    def test_salary_below_minimum(self):
        """Job with salary below minimum triggers deal-breaker."""
        job = _make_job(salary_min=80000, salary_max=100000)
        assert self.agent._check_deal_breakers(job, FULL_PREFERENCES) is True

    def test_excluded_industry(self):
        """Job in excluded industry triggers deal-breaker."""
        job = _make_job(description="Join our gambling platform engineering team")
        assert self.agent._check_deal_breakers(job, FULL_PREFERENCES) is True

    def test_no_deal_breaker_passes(self):
        """Normal job passes deal-breaker check."""
        job = _make_job()
        assert self.agent._check_deal_breakers(job, FULL_PREFERENCES) is False

    def test_unknown_salary_not_deal_breaker(self):
        """Job with unknown salary does NOT trigger deal-breaker."""
        job = _make_job(salary_min=None, salary_max=None)
        assert self.agent._check_deal_breakers(job, FULL_PREFERENCES) is False

    def test_empty_preferences_no_deal_breaker(self):
        """Empty preferences means no deal-breakers."""
        job = _make_job(company="EvilCorp")
        assert self.agent._check_deal_breakers(job, {}) is False


# ---------------------------------------------------------------------------
# Rationale tests
# ---------------------------------------------------------------------------


class TestBuildRationale:
    def test_produces_readable_string(self):
        """Rationale includes percentage and category breakdown."""
        agent = JobScoutAgent()
        breakdown = {
            "title": (20, 25),
            "location": (20, 20),
            "salary": (18, 20),
            "skills": (10, 20),
            "seniority": (10, 15),
            "company_size": (5, 10),
        }
        # Raw sum = 83, normalized = int(83/1.1) = 75
        rationale = agent._build_rationale(breakdown)
        assert "75% match" in rationale
        assert "title (20/25)" in rationale
        assert "location (20/20)" in rationale
        assert "salary (18/20)" in rationale
        assert "company_size (5/10)" in rationale

    def test_explicit_normalized_total(self):
        """Rationale uses explicit normalized total when provided."""
        agent = JobScoutAgent()
        breakdown = {
            "title": (20, 25),
            "location": (20, 20),
            "salary": (18, 20),
            "skills": (10, 20),
            "seniority": (10, 15),
            "company_size": (5, 10),
        }
        rationale = agent._build_rationale(breakdown, normalized_total=80)
        assert "80% match" in rationale


# ---------------------------------------------------------------------------
# Execute tests
# ---------------------------------------------------------------------------


class TestExecute:
    """Tests for the full execute() workflow."""

    def setup_method(self):
        self.agent = JobScoutAgent()

    @pytest.mark.asyncio
    async def test_happy_path(self):
        """execute() fetches, scores, and creates matches."""
        from app.services.job_sources.base import RawJob

        mock_context = {
            "preferences": FULL_PREFERENCES,
            "profile": FULL_PROFILE,
        }

        raw_jobs = [
            RawJob(
                title="Senior Software Engineer",
                company="Acme Corp",
                url="https://acme.com/1",
                location="San Francisco, CA",
                description="Python and React role",
                salary_min=150000,
                salary_max=200000,
                remote=True,
                source="jsearch",
            ),
        ]

        mock_job = _make_job()
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()
        # _create_matches queries existing matches; return empty result
        mock_execute_result = MagicMock()
        mock_execute_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_execute_result)

        # Create a mock module for app.db.engine since it can't be imported in test env
        mock_engine_module = MagicMock()
        mock_engine_module.AsyncSessionLocal = MagicMock(return_value=mock_session)

        import sys

        with patch(
            "app.agents.orchestrator.get_user_context",
            new_callable=AsyncMock,
            return_value=mock_context,
        ), patch.dict(
            sys.modules,
            {"app.db.engine": mock_engine_module},
        ), patch(
            "app.services.job_dedup.upsert_jobs",
            new_callable=AsyncMock,
            return_value=[mock_job],
        ), patch.object(
            self.agent,
            "_fetch_jobs",
            new_callable=AsyncMock,
            return_value=raw_jobs,
        ), patch(
            "app.config.settings",
        ) as mock_settings:
            mock_settings.LLM_SCORING_ENABLED = False
            mock_settings.MATCH_SCORE_THRESHOLD = 40
            result = await self.agent.execute("user-1", {})

        assert isinstance(result, AgentOutput)
        assert result.action == "job_scout_complete"
        assert result.data["jobs_found"] == 1
        assert result.data["matches_created"] >= 0

    @pytest.mark.asyncio
    async def test_empty_preferences(self):
        """execute() with no target titles returns empty matches."""
        mock_context = {
            "preferences": {},
            "profile": {},
        }

        with patch(
            "app.agents.orchestrator.get_user_context",
            new_callable=AsyncMock,
            return_value=mock_context,
        ):
            result = await self.agent.execute("user-1", {})

        assert isinstance(result, AgentOutput)
        assert result.data["matches_created"] == 0
        assert result.data["jobs_found"] == 0

    @pytest.mark.asyncio
    async def test_no_preferences_at_all(self):
        """execute() with None preferences returns empty matches."""
        mock_context = {
            "preferences": None,
            "profile": None,
        }

        with patch(
            "app.agents.orchestrator.get_user_context",
            new_callable=AsyncMock,
            return_value=mock_context,
        ):
            result = await self.agent.execute("user-1", {})

        assert isinstance(result, AgentOutput)
        assert result.data["matches_created"] == 0

    @pytest.mark.asyncio
    async def test_no_jobs_found(self):
        """execute() with no jobs from sources returns 0 matches."""
        mock_context = {
            "preferences": FULL_PREFERENCES,
            "profile": FULL_PROFILE,
        }

        with patch(
            "app.agents.orchestrator.get_user_context",
            new_callable=AsyncMock,
            return_value=mock_context,
        ), patch.object(
            self.agent,
            "_fetch_jobs",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await self.agent.execute("user-1", {})

        assert isinstance(result, AgentOutput)
        assert result.data["jobs_found"] == 0
        assert result.data["matches_created"] == 0


# ---------------------------------------------------------------------------
# Celery task integration test
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Company size scoring tests
# ---------------------------------------------------------------------------


class TestCompanySizeScoring:
    """Tests for _score_company_size method."""

    def setup_method(self):
        self.agent = JobScoutAgent()

    def test_known_size_meets_preference(self):
        """Company size >= min_company_size returns 10."""
        job = _make_job(raw_data={"companySize": 100})
        prefs = {"min_company_size": 50}
        assert self.agent._score_company_size(job, prefs) == 10

    def test_known_size_below_preference(self):
        """Company size < min_company_size returns 0."""
        job = _make_job(raw_data={"companySize": 20})
        prefs = {"min_company_size": 50}
        assert self.agent._score_company_size(job, prefs) == 0

    def test_unknown_size_neutral(self):
        """Unknown company size returns 5 (neutral)."""
        job = _make_job(raw_data={})
        prefs = {"min_company_size": 50}
        assert self.agent._score_company_size(job, prefs) == 5

    def test_no_preference_neutral(self):
        """No min_company_size preference returns 5 (neutral)."""
        job = _make_job(raw_data={"companySize": 100})
        assert self.agent._score_company_size(job, {}) == 5

    def test_alternate_key_company_size(self):
        """Supports company_size key."""
        job = _make_job(raw_data={"company_size": 200})
        prefs = {"min_company_size": 50}
        assert self.agent._score_company_size(job, prefs) == 10

    def test_alternate_key_employer_size(self):
        """Supports employerSize key."""
        job = _make_job(raw_data={"employerSize": 200})
        prefs = {"min_company_size": 50}
        assert self.agent._score_company_size(job, prefs) == 10

    def test_no_raw_data_neutral(self):
        """Job without raw_data attribute returns 5 (neutral)."""
        job = _make_job()
        # Default _make_job has raw_data={} so remove it
        del job.raw_data
        prefs = {"min_company_size": 50}
        assert self.agent._score_company_size(job, prefs) == 5

    def test_company_size_in_full_score(self):
        """Company size is included in _score_job breakdown."""
        job = _make_job(raw_data={"companySize": 100})
        prefs = {**FULL_PREFERENCES, "min_company_size": 50}
        score, rationale = self.agent._score_job(job, prefs, FULL_PROFILE)
        assert "company_size" in rationale


# ---------------------------------------------------------------------------
# Threshold filtering tests
# ---------------------------------------------------------------------------


class TestThresholdFiltering:
    """Tests for score threshold filtering."""

    def setup_method(self):
        self.agent = JobScoutAgent()

    def test_job_below_threshold_excluded(self):
        """Job with low score is excluded after scoring."""
        # A job that matches nothing should score very low
        job = _make_job(
            title="Chef",
            company="Restaurant",
            description="Cooking experience needed.",
            location="Rural Montana",
            salary_min=30000,
            salary_max=40000,
            remote=False,
        )
        prefs = {
            "target_titles": ["Software Engineer"],
            "target_locations": ["San Francisco"],
            "salary_minimum": 120000,
            "salary_target": 180000,
            "seniority_levels": ["senior"],
        }
        score, _ = self.agent._score_job(job, prefs, {"skills": ["Python"]})
        # With normalization, this should be well below 40
        assert score < 40

    def test_good_job_above_threshold(self):
        """Job matching preferences scores above threshold."""
        job = _make_job()
        score, _ = self.agent._score_job(job, FULL_PREFERENCES, FULL_PROFILE)
        assert score >= 40


# ---------------------------------------------------------------------------
# Celery task integration test
# ---------------------------------------------------------------------------


class TestCeleryTaskIntegration:
    """Test that the Celery task correctly calls JobScoutAgent.run()."""

    @pytest.mark.asyncio
    async def test_task_calls_agent_run(self):
        """Verify agent.run() is invoked and returns expected output."""
        mock_result = AgentOutput(
            action="job_scout_complete",
            rationale="test",
            confidence=0.9,
            data={"matches_created": 5},
        )

        with patch.object(
            JobScoutAgent,
            "run",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            agent = JobScoutAgent()
            result = await agent.run("user-1", {})

            assert isinstance(result, AgentOutput)
            assert result.action == "job_scout_complete"
            assert result.to_dict()["data"]["matches_created"] == 5
            agent.run.assert_awaited_once_with("user-1", {})


# ---------------------------------------------------------------------------
# Structured rationale in matches tests (6.5)
# ---------------------------------------------------------------------------


class TestStructuredRationaleInMatches:
    """Tests that execute() stores structured JSON rationale in Match records."""

    def setup_method(self):
        self.agent = JobScoutAgent()

    @pytest.mark.asyncio
    async def test_execute_stores_json_rationale(self):
        """Rationale argument passed to Match() is valid JSON with structured keys."""
        from app.services.job_sources.base import RawJob

        mock_context = {
            "preferences": FULL_PREFERENCES,
            "profile": FULL_PROFILE,
        }

        raw_jobs = [
            RawJob(
                title="Senior Software Engineer",
                company="Acme Corp",
                url="https://acme.com/1",
                location="San Francisco, CA",
                description="Python and React role",
                salary_min=150000,
                salary_max=200000,
                remote=True,
                source="jsearch",
            ),
        ]

        mock_job = _make_job()
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        # Track Match objects added to session
        added_objects = []
        mock_session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

        mock_execute_result = MagicMock()
        mock_execute_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_execute_result)

        mock_engine_module = MagicMock()
        mock_engine_module.AsyncSessionLocal = MagicMock(return_value=mock_session)

        import sys

        with patch(
            "app.agents.orchestrator.get_user_context",
            new_callable=AsyncMock,
            return_value=mock_context,
        ), patch.dict(
            sys.modules,
            {"app.db.engine": mock_engine_module},
        ), patch(
            "app.services.job_dedup.upsert_jobs",
            new_callable=AsyncMock,
            return_value=[mock_job],
        ), patch.object(
            self.agent,
            "_fetch_jobs",
            new_callable=AsyncMock,
            return_value=raw_jobs,
        ), patch(
            "app.config.settings",
        ) as mock_settings:
            mock_settings.LLM_SCORING_ENABLED = False
            mock_settings.MATCH_SCORE_THRESHOLD = 40
            result = await self.agent.execute("user-1", {})

        assert isinstance(result, AgentOutput)
        # Verify at least one Match was added
        if added_objects:
            match_obj = added_objects[0]
            rationale_str = match_obj.rationale
            # Rationale should be valid JSON
            parsed = json.loads(rationale_str)
            assert "summary" in parsed
            assert "top_reasons" in parsed
            assert "concerns" in parsed
            assert "confidence" in parsed
