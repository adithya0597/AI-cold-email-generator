"""
Unit tests for the preference learning service.

Tests detect_patterns and apply_learned_preferences with mocked
database sessions using SimpleNamespace objects.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.preference_learning import (
    apply_learned_preferences,
    detect_patterns,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_swipe_event(user_id, action="dismissed", company="Acme Corp",
                      location="SF", remote=True, salary_min=100000,
                      salary_max=150000, employment_type="Full-time"):
    return SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        match_id=uuid4(),
        action=action,
        job_company=company,
        job_location=location,
        job_remote=remote,
        job_salary_min=salary_min,
        job_salary_max=salary_max,
        job_employment_type=employment_type,
    )


def _make_learned_pref(user_id, pattern_type="company", pattern_value="Acme Corp",
                       confidence=0.80, occurrences=5, status="pending",
                       deleted_at=None):
    return SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        pattern_type=pattern_type,
        pattern_value=pattern_value,
        confidence=Decimal(str(confidence)),
        occurrences=occurrences,
        status=status,
        deleted_at=deleted_at,
    )


def _make_job(company="Acme Corp", location="SF", remote=True,
              employment_type="Full-time"):
    return SimpleNamespace(
        company=company,
        location=location,
        remote=remote,
        employment_type=employment_type,
    )


def _mock_db_for_detect(events, existing_prefs=None):
    """Create a mock db session that returns events and existing prefs."""
    mock_db = AsyncMock()
    added_objects = []

    # First call: swipe events query
    events_result = MagicMock()
    events_result.scalars.return_value.all.return_value = events

    # Second call: existing learned preferences query
    prefs_result = MagicMock()
    prefs_result.scalars.return_value.all.return_value = existing_prefs or []

    mock_db.execute = AsyncMock(side_effect=[events_result, prefs_result])
    mock_db.flush = AsyncMock()

    original_add = mock_db.add
    def capture_add(obj):
        added_objects.append(obj)
        return original_add(obj)
    mock_db.add = capture_add

    return mock_db, added_objects


def _mock_db_for_apply(preferences):
    """Create a mock db session that returns learned preferences."""
    mock_db = AsyncMock()
    prefs_result = MagicMock()
    prefs_result.scalars.return_value.all.return_value = preferences
    mock_db.execute = AsyncMock(return_value=prefs_result)
    return mock_db


# ---------------------------------------------------------------------------
# Tests: detect_patterns
# ---------------------------------------------------------------------------

class TestDetectPatterns:
    @pytest.mark.asyncio
    async def test_finds_company_pattern_above_threshold(self):
        """3+ dismissals at >60% rate creates a LearnedPreference."""
        user_id = uuid4()
        events = [
            _make_swipe_event(user_id, action="dismissed", company="BadCo"),
            _make_swipe_event(user_id, action="dismissed", company="BadCo"),
            _make_swipe_event(user_id, action="dismissed", company="BadCo"),
            _make_swipe_event(user_id, action="saved", company="BadCo"),
        ]
        mock_db, added = _mock_db_for_detect(events)

        result = await detect_patterns(user_id, mock_db)

        # Should detect company=BadCo pattern (3/4 = 75% dismiss rate)
        company_prefs = [p for p in added if p.pattern_type == "company"]
        assert len(company_prefs) >= 1
        pref = company_prefs[0]
        assert pref.pattern_value == "BadCo"
        assert float(pref.confidence) == 0.75
        assert pref.occurrences == 4

    @pytest.mark.asyncio
    async def test_ignores_below_threshold_patterns(self):
        """2 dismissals is below the minimum of 3."""
        user_id = uuid4()
        events = [
            _make_swipe_event(user_id, action="dismissed", company="OkCo"),
            _make_swipe_event(user_id, action="dismissed", company="OkCo"),
            _make_swipe_event(user_id, action="saved", company="OkCo"),
        ]
        mock_db, added = _mock_db_for_detect(events)

        result = await detect_patterns(user_id, mock_db)

        company_prefs = [p for p in added if p.pattern_type == "company" and p.pattern_value == "OkCo"]
        assert len(company_prefs) == 0

    @pytest.mark.asyncio
    async def test_ignores_low_dismiss_rate(self):
        """3 dismissals out of 6 total = 50%, below 60% threshold."""
        user_id = uuid4()
        events = [
            _make_swipe_event(user_id, action="dismissed", company="MixedCo"),
            _make_swipe_event(user_id, action="dismissed", company="MixedCo"),
            _make_swipe_event(user_id, action="dismissed", company="MixedCo"),
            _make_swipe_event(user_id, action="saved", company="MixedCo"),
            _make_swipe_event(user_id, action="saved", company="MixedCo"),
            _make_swipe_event(user_id, action="saved", company="MixedCo"),
        ]
        mock_db, added = _mock_db_for_detect(events)

        result = await detect_patterns(user_id, mock_db)

        company_prefs = [p for p in added if p.pattern_type == "company" and p.pattern_value == "MixedCo"]
        assert len(company_prefs) == 0

    @pytest.mark.asyncio
    async def test_does_not_duplicate_existing_preference(self):
        """If a LearnedPreference already exists, don't create another."""
        user_id = uuid4()
        events = [
            _make_swipe_event(user_id, action="dismissed", company="BadCo"),
            _make_swipe_event(user_id, action="dismissed", company="BadCo"),
            _make_swipe_event(user_id, action="dismissed", company="BadCo"),
        ]
        existing = [_make_learned_pref(user_id, pattern_type="company", pattern_value="BadCo")]
        mock_db, added = _mock_db_for_detect(events, existing_prefs=existing)

        result = await detect_patterns(user_id, mock_db)

        company_prefs = [p for p in added if p.pattern_type == "company" and p.pattern_value == "BadCo"]
        assert len(company_prefs) == 0

    @pytest.mark.asyncio
    async def test_skips_soft_deleted_preferences_in_existing_check(self):
        """Soft-deleted (rejected) preferences should not block new detection.
        Note: the query filters by deleted_at IS NULL, so soft-deleted prefs
        are not returned."""
        user_id = uuid4()
        events = [
            _make_swipe_event(user_id, action="dismissed", company="BadCo"),
            _make_swipe_event(user_id, action="dismissed", company="BadCo"),
            _make_swipe_event(user_id, action="dismissed", company="BadCo"),
        ]
        # Simulate that the existing pref query returns nothing (soft-deleted prefs filtered out)
        mock_db, added = _mock_db_for_detect(events, existing_prefs=[])

        result = await detect_patterns(user_id, mock_db)

        company_prefs = [p for p in added if p.pattern_type == "company" and p.pattern_value == "BadCo"]
        assert len(company_prefs) == 1

    @pytest.mark.asyncio
    async def test_caps_confidence_at_095(self):
        """100% dismiss rate should be capped at 0.95."""
        user_id = uuid4()
        events = [
            _make_swipe_event(user_id, action="dismissed", company="TerribleCo"),
            _make_swipe_event(user_id, action="dismissed", company="TerribleCo"),
            _make_swipe_event(user_id, action="dismissed", company="TerribleCo"),
        ]
        mock_db, added = _mock_db_for_detect(events)

        result = await detect_patterns(user_id, mock_db)

        company_prefs = [p for p in added if p.pattern_type == "company" and p.pattern_value == "TerribleCo"]
        assert len(company_prefs) == 1
        assert float(company_prefs[0].confidence) == 0.95

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_events(self):
        """No swipe events should return empty list."""
        user_id = uuid4()
        mock_db = AsyncMock()
        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=events_result)

        result = await detect_patterns(user_id, mock_db)
        assert result == []


# ---------------------------------------------------------------------------
# Tests: apply_learned_preferences
# ---------------------------------------------------------------------------

class TestApplyLearnedPreferences:
    @pytest.mark.asyncio
    async def test_reduces_score_for_dismissed_company(self):
        """High-confidence dismissed pattern reduces score."""
        user_id = uuid4()
        prefs = [
            _make_learned_pref(user_id, pattern_type="company",
                              pattern_value="badco", confidence=0.80),
        ]
        mock_db = _mock_db_for_apply(prefs)
        job = _make_job(company="BadCo")

        result = await apply_learned_preferences(user_id, 80, job, mock_db)

        # 80 + int(-15 * 0.80) = 80 + (-12) = 68
        assert result == 68

    @pytest.mark.asyncio
    async def test_increases_score_for_saved_pattern(self):
        """Low dismiss rate (saved pattern) increases score."""
        user_id = uuid4()
        prefs = [
            _make_learned_pref(user_id, pattern_type="company",
                              pattern_value="goodco", confidence=0.30),
        ]
        mock_db = _mock_db_for_apply(prefs)
        job = _make_job(company="GoodCo")

        result = await apply_learned_preferences(user_id, 80, job, mock_db)

        # 80 + int(10 * (1 - 0.30)) = 80 + int(7.0) = 87
        assert result == 87

    @pytest.mark.asyncio
    async def test_returns_unchanged_score_when_no_preferences(self):
        """No learned preferences should return base score."""
        user_id = uuid4()
        mock_db = _mock_db_for_apply([])
        job = _make_job()

        result = await apply_learned_preferences(user_id, 75, job, mock_db)
        assert result == 75

    @pytest.mark.asyncio
    async def test_score_clamped_to_zero_minimum(self):
        """Score should never go below 0."""
        user_id = uuid4()
        prefs = [
            _make_learned_pref(user_id, pattern_type="company",
                              pattern_value="badco", confidence=0.95),
        ]
        mock_db = _mock_db_for_apply(prefs)
        job = _make_job(company="BadCo")

        result = await apply_learned_preferences(user_id, 5, job, mock_db)

        # 5 + int(-15 * 0.95) = 5 + (-14) = -9 → clamped to 0
        assert result == 0

    @pytest.mark.asyncio
    async def test_score_clamped_to_hundred_maximum(self):
        """Score should never exceed 100."""
        user_id = uuid4()
        prefs = [
            _make_learned_pref(user_id, pattern_type="company",
                              pattern_value="goodco", confidence=0.10),
        ]
        mock_db = _mock_db_for_apply(prefs)
        job = _make_job(company="GoodCo")

        result = await apply_learned_preferences(user_id, 98, job, mock_db)

        # 98 + int(10 * 0.90) = 98 + 9 = 107 → clamped to 100
        assert result == 100

    @pytest.mark.asyncio
    async def test_no_match_for_different_company(self):
        """Preference for company A should not affect company B."""
        user_id = uuid4()
        prefs = [
            _make_learned_pref(user_id, pattern_type="company",
                              pattern_value="badco", confidence=0.80),
        ]
        mock_db = _mock_db_for_apply(prefs)
        job = _make_job(company="GoodCo")

        result = await apply_learned_preferences(user_id, 80, job, mock_db)
        assert result == 80
