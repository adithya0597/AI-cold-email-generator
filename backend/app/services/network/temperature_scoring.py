"""
Relationship Temperature Scoring Service — computes relationship
strength with target contacts.

Pure computation service (no LLM needed). Scores contacts based on
recency of interaction, frequency of engagement, and depth of interaction.

Temperature levels: cold (0-0.25), warming (0.25-0.5), warm (0.5-0.75), hot (0.75-1.0).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class TemperatureScore:
    """Relationship temperature score for a single contact."""

    contact_name: str = ""
    score: str = "cold"  # "cold", "warming", "warm", "hot"
    numeric_score: float = 0.0
    factors: dict[str, float] = field(default_factory=dict)
    ready_for_outreach: bool = False
    last_interaction: str = ""
    interaction_count: int = 0
    data_quality: str = "complete"  # "complete", "partial", "stub"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "contact_name": self.contact_name,
            "score": self.score,
            "numeric_score": self.numeric_score,
            "factors": self.factors,
            "ready_for_outreach": self.ready_for_outreach,
            "last_interaction": self.last_interaction,
            "interaction_count": self.interaction_count,
            "data_quality": self.data_quality,
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class RelationshipTemperatureService:
    """Computes relationship temperature from engagement history.

    Pure computation — no LLM or external API calls needed.
    """

    def score_contacts(
        self,
        engagement_history: list[dict[str, Any]],
    ) -> list[TemperatureScore]:
        """Compute temperature scores from engagement records.

        Args:
            engagement_history: List of engagement record dicts, each with
                contact_name, engagement_type, timestamp, temperature_impact.

        Returns:
            List of TemperatureScore, one per unique contact.
        """
        if not engagement_history:
            return []

        # Group by contact
        by_contact: dict[str, list[dict[str, Any]]] = {}
        for record in engagement_history:
            name = record.get("contact_name", "Unknown")
            by_contact.setdefault(name, []).append(record)

        scores: list[TemperatureScore] = []
        for contact_name, records in by_contact.items():
            score = self._score_contact(contact_name, records)
            scores.append(score)

        return scores

    def _score_contact(
        self,
        contact_name: str,
        records: list[dict[str, Any]],
    ) -> TemperatureScore:
        """Compute temperature for a single contact."""
        # Parse timestamps
        timestamps: list[datetime] = []
        interaction_types: list[str] = []

        for r in records:
            ts_str = r.get("timestamp", "")
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str)
                    timestamps.append(ts)
                except (ValueError, TypeError):
                    pass
            interaction_types.append(r.get("engagement_type", ""))

        # Compute factor scores
        recency = self._compute_recency_score(
            max(timestamps) if timestamps else None
        )
        frequency = self._compute_frequency_score(len(records))
        depth = self._compute_depth_score(interaction_types)

        # Weighted average
        numeric = round(
            0.4 * recency + 0.3 * frequency + 0.3 * depth, 2
        )
        numeric = min(1.0, max(0.0, numeric))

        label = self._classify_temperature(numeric)
        ready = label in ("warm", "hot")

        last_interaction = ""
        if timestamps:
            last_interaction = max(timestamps).isoformat()

        return TemperatureScore(
            contact_name=contact_name,
            score=label,
            numeric_score=numeric,
            factors={
                "recency": round(recency, 2),
                "frequency": round(frequency, 2),
                "depth": round(depth, 2),
            },
            ready_for_outreach=ready,
            last_interaction=last_interaction,
            interaction_count=len(records),
            data_quality="complete",
        )

    def _compute_recency_score(
        self,
        last_interaction: datetime | None,
    ) -> float:
        """Compute recency score. Decays over 90 days.

        Returns:
            1.0 for today, 0.0 for 90+ days ago.
        """
        if last_interaction is None:
            return 0.0

        now = datetime.now(timezone.utc)
        # Ensure tz-aware comparison
        if last_interaction.tzinfo is None:
            last_interaction = last_interaction.replace(tzinfo=timezone.utc)

        days_ago = (now - last_interaction).days
        if days_ago <= 0:
            return 1.0
        if days_ago >= 90:
            return 0.0
        return round(1.0 - (days_ago / 90.0), 2)

    def _compute_frequency_score(
        self,
        interaction_count: int,
    ) -> float:
        """Compute frequency score based on interaction count.

        Returns:
            0.0-1.0 based on interaction frequency.
        """
        if interaction_count == 0:
            return 0.0

        if interaction_count >= 10:
            return 1.0
        elif interaction_count >= 5:
            return 0.7
        elif interaction_count >= 3:
            return 0.5
        elif interaction_count >= 1:
            return 0.3
        return 0.0

    def _compute_depth_score(
        self,
        interaction_types: list[str],
    ) -> float:
        """Compute depth score. Comments > likes, conversations > one-way.

        Returns:
            0.0-1.0 based on interaction depth.
        """
        if not interaction_types:
            return 0.0

        # Weight by interaction type
        weights = {
            "conversation": 1.0,
            "comment": 0.7,
            "share": 0.5,
            "like": 0.3,
        }

        total = 0.0
        for itype in interaction_types:
            total += weights.get(itype.lower(), 0.3)

        avg = total / len(interaction_types)
        return min(1.0, avg)

    def _classify_temperature(self, numeric_score: float) -> str:
        """Classify numeric score into temperature label.

        0-0.25: cold, 0.25-0.5: warming, 0.5-0.75: warm, 0.75-1.0: hot.
        """
        if numeric_score >= 0.75:
            return "hot"
        elif numeric_score >= 0.5:
            return "warm"
        elif numeric_score >= 0.25:
            return "warming"
        return "cold"
