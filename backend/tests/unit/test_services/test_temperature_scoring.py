"""Tests for Relationship Temperature Scoring Service (Story 9-5).

Covers: score_contacts(), temperature classification, recency decay,
frequency scoring, depth scoring, ready_for_outreach, to_dict(), empty history.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.network.temperature_scoring import (
    RelationshipTemperatureService,
    TemperatureScore,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    return RelationshipTemperatureService()


def _ts(days_ago: int = 0) -> str:
    """Helper to create ISO timestamp N days ago."""
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.isoformat()


# ---------------------------------------------------------------------------
# AC1: Temperature score display
# ---------------------------------------------------------------------------


class TestScoreContacts:
    def test_returns_temperature_scores(self, service):
        """score_contacts() returns list of TemperatureScore."""
        history = [
            {
                "contact_name": "Alice",
                "engagement_type": "comment",
                "timestamp": _ts(1),
                "temperature_impact": 0.1,
            },
        ]
        result = service.score_contacts(history)
        assert len(result) == 1
        assert isinstance(result[0], TemperatureScore)
        assert result[0].contact_name == "Alice"

    def test_groups_by_contact(self, service):
        """score_contacts() groups records by contact name."""
        history = [
            {"contact_name": "Alice", "engagement_type": "comment", "timestamp": _ts(1)},
            {"contact_name": "Alice", "engagement_type": "like", "timestamp": _ts(2)},
            {"contact_name": "Bob", "engagement_type": "comment", "timestamp": _ts(5)},
        ]
        result = service.score_contacts(history)
        assert len(result) == 2
        names = {s.contact_name for s in result}
        assert names == {"Alice", "Bob"}

    def test_empty_history_returns_empty(self, service):
        """score_contacts() returns empty for no engagement history."""
        result = service.score_contacts([])
        assert result == []


# ---------------------------------------------------------------------------
# AC1: Temperature classification boundaries
# ---------------------------------------------------------------------------


class TestClassification:
    def test_cold(self, service):
        """0-0.25 → cold."""
        assert service._classify_temperature(0.0) == "cold"
        assert service._classify_temperature(0.1) == "cold"
        assert service._classify_temperature(0.24) == "cold"

    def test_warming(self, service):
        """0.25-0.5 → warming."""
        assert service._classify_temperature(0.25) == "warming"
        assert service._classify_temperature(0.35) == "warming"
        assert service._classify_temperature(0.49) == "warming"

    def test_warm(self, service):
        """0.5-0.75 → warm."""
        assert service._classify_temperature(0.5) == "warm"
        assert service._classify_temperature(0.6) == "warm"
        assert service._classify_temperature(0.74) == "warm"

    def test_hot(self, service):
        """0.75-1.0 → hot."""
        assert service._classify_temperature(0.75) == "hot"
        assert service._classify_temperature(0.9) == "hot"
        assert service._classify_temperature(1.0) == "hot"


# ---------------------------------------------------------------------------
# AC2: Recency decay scoring
# ---------------------------------------------------------------------------


class TestRecencyScoring:
    def test_today_is_one(self, service):
        """Interaction today → 1.0."""
        score = service._compute_recency_score(datetime.now(timezone.utc))
        assert score == 1.0

    def test_90_days_is_zero(self, service):
        """Interaction 90+ days ago → 0.0."""
        old = datetime.now(timezone.utc) - timedelta(days=91)
        score = service._compute_recency_score(old)
        assert score == 0.0

    def test_45_days_is_half(self, service):
        """Interaction ~45 days ago → ~0.5."""
        mid = datetime.now(timezone.utc) - timedelta(days=45)
        score = service._compute_recency_score(mid)
        assert 0.4 <= score <= 0.6

    def test_none_is_zero(self, service):
        """No interaction → 0.0."""
        score = service._compute_recency_score(None)
        assert score == 0.0


# ---------------------------------------------------------------------------
# AC2: Frequency scoring
# ---------------------------------------------------------------------------


class TestFrequencyScoring:
    def test_zero_interactions(self, service):
        """No interactions → 0.0."""
        assert service._compute_frequency_score(0) == 0.0

    def test_one_interaction(self, service):
        """1 interaction → 0.3."""
        assert service._compute_frequency_score(1) == 0.3

    def test_five_interactions(self, service):
        """5 interactions → 0.7."""
        assert service._compute_frequency_score(5) == 0.7

    def test_ten_interactions(self, service):
        """10+ interactions → 1.0."""
        assert service._compute_frequency_score(10) == 1.0


# ---------------------------------------------------------------------------
# AC2: Depth scoring (comment > like)
# ---------------------------------------------------------------------------


class TestDepthScoring:
    def test_conversation_highest(self, service):
        """Conversations score highest."""
        score = service._compute_depth_score(["conversation"])
        assert score == 1.0

    def test_comment_higher_than_like(self, service):
        """Comments score higher than likes."""
        comment_score = service._compute_depth_score(["comment"])
        like_score = service._compute_depth_score(["like"])
        assert comment_score > like_score

    def test_mixed_types(self, service):
        """Mixed interaction types averaged."""
        score = service._compute_depth_score(["comment", "like"])
        assert 0.3 < score < 0.8

    def test_empty_types(self, service):
        """No interaction types → 0.0."""
        assert service._compute_depth_score([]) == 0.0


# ---------------------------------------------------------------------------
# AC3: Ready for outreach
# ---------------------------------------------------------------------------


class TestReadyForOutreach:
    def test_warm_is_ready(self, service):
        """Warm contacts are ready for outreach."""
        history = [
            {"contact_name": "Alice", "engagement_type": "conversation", "timestamp": _ts(0)},
            {"contact_name": "Alice", "engagement_type": "comment", "timestamp": _ts(1)},
            {"contact_name": "Alice", "engagement_type": "comment", "timestamp": _ts(2)},
            {"contact_name": "Alice", "engagement_type": "comment", "timestamp": _ts(3)},
            {"contact_name": "Alice", "engagement_type": "comment", "timestamp": _ts(4)},
        ]
        result = service.score_contacts(history)
        assert result[0].ready_for_outreach is True

    def test_cold_not_ready(self, service):
        """Cold contacts are not ready for outreach."""
        history = [
            {"contact_name": "Bob", "engagement_type": "like", "timestamp": _ts(80)},
        ]
        result = service.score_contacts(history)
        assert result[0].ready_for_outreach is False


# ---------------------------------------------------------------------------
# to_dict() serialization
# ---------------------------------------------------------------------------


class TestToDict:
    def test_to_dict_includes_all_fields(self):
        """to_dict() includes ALL dataclass fields."""
        ts = TemperatureScore(
            contact_name="Alice",
            score="warm",
            numeric_score=0.65,
            factors={"recency": 0.8, "frequency": 0.5, "depth": 0.6},
            ready_for_outreach=True,
            last_interaction="2025-12-01T10:00:00Z",
            interaction_count=5,
            data_quality="complete",
        )
        d = ts.to_dict()
        assert d["contact_name"] == "Alice"
        assert d["score"] == "warm"
        assert d["numeric_score"] == 0.65
        assert d["factors"] == {"recency": 0.8, "frequency": 0.5, "depth": 0.6}
        assert d["ready_for_outreach"] is True
        assert d["last_interaction"] == "2025-12-01T10:00:00Z"
        assert d["interaction_count"] == 5
        assert d["data_quality"] == "complete"
        assert len(d) == 8
