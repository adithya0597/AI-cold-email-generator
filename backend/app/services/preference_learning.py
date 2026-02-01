"""
Preference learning service.

Analyzes swipe events to detect user preference patterns and provides
score adjustment for learned preferences.

Architecture: Standalone module with pure functions that take a db session
parameter, following the same pattern as job_scoring.py.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    LearnedPreference,
    LearnedPreferenceStatus,
    SwipeEvent,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_OCCURRENCES = 3
MIN_DISMISS_RATE = 0.60
MAX_CONFIDENCE = 0.95

# Score adjustments
NEGATIVE_PENALTY = -15  # Per high-confidence dismissed pattern
POSITIVE_BOOST = 10     # Per high-confidence saved pattern


# ---------------------------------------------------------------------------
# Pattern detection
# ---------------------------------------------------------------------------


async def detect_patterns(user_id: UUID, db: AsyncSession) -> list[LearnedPreference]:
    """Analyze swipe events and detect preference patterns.

    Scans all swipe events for the given user, groups by attribute
    (company, location, remote, employment_type), and creates
    LearnedPreference records for patterns above threshold.

    Returns newly created LearnedPreference records.
    """
    # 1. Query all swipe events for user
    result = await db.execute(
        select(SwipeEvent).where(SwipeEvent.user_id == user_id)
    )
    events = result.scalars().all()

    if not events:
        return []

    # 2. Query existing learned preferences (to avoid duplicates)
    existing_result = await db.execute(
        select(LearnedPreference).where(
            LearnedPreference.user_id == user_id,
            LearnedPreference.deleted_at.is_(None),
        )
    )
    existing_prefs = existing_result.scalars().all()
    existing_keys = {
        (p.pattern_type, p.pattern_value) for p in existing_prefs
    }

    # 3. Group events by attribute
    attribute_counts: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"total": 0, "dismissed": 0})
    )

    for event in events:
        action = event.action

        # Company pattern
        if event.job_company:
            counts = attribute_counts["company"][event.job_company]
            counts["total"] += 1
            if action == "dismissed":
                counts["dismissed"] += 1

        # Location pattern
        if event.job_location:
            counts = attribute_counts["location"][event.job_location]
            counts["total"] += 1
            if action == "dismissed":
                counts["dismissed"] += 1

        # Remote pattern
        if event.job_remote is not None:
            remote_val = str(event.job_remote).lower()
            counts = attribute_counts["remote"][remote_val]
            counts["total"] += 1
            if action == "dismissed":
                counts["dismissed"] += 1

        # Employment type pattern
        if event.job_employment_type:
            counts = attribute_counts["employment_type"][event.job_employment_type]
            counts["total"] += 1
            if action == "dismissed":
                counts["dismissed"] += 1

    # 4. Create LearnedPreference for patterns above threshold
    new_preferences: list[LearnedPreference] = []

    for pattern_type, values in attribute_counts.items():
        for pattern_value, counts in values.items():
            total = counts["total"]
            dismissed = counts["dismissed"]

            if dismissed < MIN_OCCURRENCES:
                continue

            dismiss_rate = dismissed / total
            if dismiss_rate < MIN_DISMISS_RATE:
                continue

            # Skip if already exists
            if (pattern_type, pattern_value) in existing_keys:
                continue

            confidence = min(dismiss_rate, MAX_CONFIDENCE)

            pref = LearnedPreference(
                user_id=user_id,
                pattern_type=pattern_type,
                pattern_value=pattern_value,
                confidence=confidence,
                occurrences=total,
                status=LearnedPreferenceStatus.PENDING,
            )
            db.add(pref)
            new_preferences.append(pref)

            logger.info(
                "Detected preference pattern: %s=%s (confidence=%.2f, occurrences=%d)",
                pattern_type,
                pattern_value,
                confidence,
                total,
            )

    if new_preferences:
        await db.flush()

    return new_preferences


# ---------------------------------------------------------------------------
# Score adjustment
# ---------------------------------------------------------------------------


async def apply_learned_preferences(
    user_id: UUID,
    base_score: int,
    job: Any,
    db: AsyncSession,
) -> int:
    """Adjust a job's match score based on learned preferences.

    Applies negative penalties for dismissed patterns and positive boosts
    for saved patterns (patterns where dismiss rate is low, i.e., the
    user tends to save jobs with that attribute).

    Args:
        user_id: The user's UUID.
        base_score: The original heuristic/LLM score (0-100).
        job: A job object with company, location, remote, employment_type attributes.
        db: Async database session.

    Returns:
        Adjusted score clamped to 0-100.
    """
    result = await db.execute(
        select(LearnedPreference).where(
            LearnedPreference.user_id == user_id,
            LearnedPreference.status.in_([
                LearnedPreferenceStatus.PENDING,
                LearnedPreferenceStatus.ACKNOWLEDGED,
            ]),
            LearnedPreference.deleted_at.is_(None),
        )
    )
    preferences = result.scalars().all()

    if not preferences:
        return base_score

    adjustment = 0

    for pref in preferences:
        job_value = _get_job_attribute(job, pref.pattern_type)
        if job_value is None:
            continue

        if str(job_value).lower() == pref.pattern_value.lower():
            # High dismiss rate = negative pattern
            confidence = float(pref.confidence)
            if confidence >= MIN_DISMISS_RATE:
                adjustment += int(NEGATIVE_PENALTY * confidence)
            else:
                adjustment += int(POSITIVE_BOOST * (1 - confidence))

    return max(0, min(100, base_score + adjustment))


def _get_job_attribute(job: Any, pattern_type: str) -> str | None:
    """Extract the relevant attribute from a job object based on pattern type."""
    mapping = {
        "company": "company",
        "location": "location",
        "remote": "remote",
        "employment_type": "employment_type",
    }
    attr_name = mapping.get(pattern_type)
    if attr_name is None:
        return None
    value = getattr(job, attr_name, None)
    if value is None:
        return None
    return str(value).lower()
