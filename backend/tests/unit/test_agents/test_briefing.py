"""
Tests for the briefing pipeline and fallback mechanism.

Verifies Phase 3 Success Criteria:
    #2: "A daily briefing is generated at the user's configured time
         and delivered both in-app and via email within 15 minutes."
    #5: "If the briefing pipeline fails, a 'lite briefing' from cache
         is shown instead of an error."

All database, Redis, and external API calls are mocked.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_USER_ID = "test-user-briefing-00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Helper: mock gather results for the generator
# ---------------------------------------------------------------------------


def _mock_gather_data(
    matches=None, updates=None, approvals=0, warnings=None
):
    """Return a tuple mimicking asyncio.gather results for the 4 data queries."""
    return (
        matches or [],
        updates or [],
        approvals,
        warnings or [],
    )


# ---------------------------------------------------------------------------
# Full briefing generation tests
# ---------------------------------------------------------------------------


class TestGenerateFullBriefing:
    """Tests for generate_full_briefing()."""

    @pytest.mark.asyncio
    async def test_successful_briefing_cached(self):
        """After successful generation, the briefing is cached in Redis with 48h TTL."""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.aclose = AsyncMock()

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_briefing = MagicMock()
        mock_briefing.id = "briefing-id-001"
        mock_session.refresh = AsyncMock(
            side_effect=lambda obj: setattr(obj, "id", "briefing-id-001")
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.agents.briefing.generator._get_recent_matches",
            new_callable=AsyncMock,
            return_value=[{"id": "m1", "output": {"action": "job_match"}, "created_at": "2026-01-31T10:00:00"}],
        ):
            with patch(
                "app.agents.briefing.generator._get_application_updates",
                new_callable=AsyncMock,
                return_value=[],
            ):
                with patch(
                    "app.agents.briefing.generator._get_pending_approval_count",
                    new_callable=AsyncMock,
                    return_value=2,
                ):
                    with patch(
                        "app.agents.briefing.generator._get_agent_warnings",
                        new_callable=AsyncMock,
                        return_value=[],
                    ):
                        with patch(
                            "app.agents.briefing.generator._llm_summarise",
                            new_callable=AsyncMock,
                            return_value={
                                "summary": "You have 1 new match and 2 pending approvals.",
                                "actions_needed": ["Review 2 pending approvals"],
                                "new_matches": [{"title": "ML Engineer", "company": "Acme", "reason": "Skills match"}],
                                "activity_log": [],
                                "metrics": {"total_matches": 1, "pending_approvals": 2, "applications_sent": 0},
                            },
                        ):
                            with patch(
                                "app.db.engine.AsyncSessionLocal",
                                return_value=mock_session,
                            ):
                                with patch(
                                    "redis.asyncio.from_url",
                                    return_value=mock_redis,
                                ):
                                    from app.agents.briefing.generator import (
                                        generate_full_briefing,
                                    )

                                    briefing = await generate_full_briefing(_USER_ID)

        # Verify briefing content
        assert briefing["briefing_type"] == "full"
        assert "summary" in briefing
        assert briefing["metrics"]["pending_approvals"] == 2

        # Verify Redis cache was set with 48h TTL
        mock_redis.set.assert_awaited_once()
        cache_call = mock_redis.set.await_args
        assert cache_call.args[0] == f"briefing_cache:{_USER_ID}"
        assert cache_call.kwargs.get("ex") == 86400 * 2  # 48h

    @pytest.mark.asyncio
    async def test_briefing_empty_state_for_new_user(self):
        """First briefing with zero data returns the encouraging empty-state message."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock(
            side_effect=lambda obj: setattr(obj, "id", "briefing-empty-001")
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.aclose = AsyncMock()

        # All data queries return empty results
        with patch(
            "app.agents.briefing.generator._get_recent_matches",
            new_callable=AsyncMock,
            return_value=[],
        ):
            with patch(
                "app.agents.briefing.generator._get_application_updates",
                new_callable=AsyncMock,
                return_value=[],
            ):
                with patch(
                    "app.agents.briefing.generator._get_pending_approval_count",
                    new_callable=AsyncMock,
                    return_value=0,
                ):
                    with patch(
                        "app.agents.briefing.generator._get_agent_warnings",
                        new_callable=AsyncMock,
                        return_value=[],
                    ):
                        with patch(
                            "app.db.engine.AsyncSessionLocal",
                            return_value=mock_session,
                        ):
                            with patch(
                                "redis.asyncio.from_url",
                                return_value=mock_redis,
                            ):
                                from app.agents.briefing.generator import (
                                    generate_full_briefing,
                                )

                                briefing = await generate_full_briefing(_USER_ID)

        # Verify empty state content
        assert "still learning your preferences" in briefing["summary"]
        assert briefing["metrics"]["total_matches"] == 0
        assert "tips" in briefing
        assert len(briefing["tips"]) > 0


# ---------------------------------------------------------------------------
# Fallback / lite briefing tests
# ---------------------------------------------------------------------------


class TestBriefingFallback:
    """Tests for generate_briefing_with_fallback() and generate_lite_briefing()."""

    @pytest.mark.asyncio
    async def test_lite_briefing_returned_on_failure(self):
        """When generate_full_briefing raises, a lite briefing from cache is returned."""
        cached_data = json.dumps({
            "summary": "Yesterday's briefing",
            "actions_needed": ["Review applications"],
            "new_matches": [{"title": "SWE", "company": "BigCo", "reason": "Match"}],
            "activity_log": [{"event": "apply", "detail": "Applied to BigCo"}],
            "metrics": {"total_matches": 5, "pending_approvals": 1, "applications_sent": 2},
            "generated_at": "2026-01-30T08:00:00+00:00",
        })

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=cached_data)
        mock_redis.aclose = AsyncMock()

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock(
            side_effect=lambda obj: setattr(obj, "id", "lite-briefing-001")
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.agents.briefing.generator.generate_full_briefing",
            new_callable=AsyncMock,
            side_effect=RuntimeError("LLM API timeout"),
        ):
            with patch(
                "redis.asyncio.from_url",
                return_value=mock_redis,
            ):
                with patch(
                    "app.db.engine.AsyncSessionLocal",
                    return_value=mock_session,
                ):
                    with patch(
                        "app.worker.celery_app.celery_app",
                        new_callable=MagicMock,
                    ) as mock_celery:
                        mock_celery.send_task = MagicMock()

                        from app.agents.briefing.fallback import (
                            generate_briefing_with_fallback,
                        )

                        briefing = await generate_briefing_with_fallback(_USER_ID)

        # Verify lite briefing was returned
        assert briefing["briefing_type"] == "lite"
        assert "trouble" in briefing["summary"].lower()
        # Verify cached data was used
        assert len(briefing["new_matches"]) > 0

    @pytest.mark.asyncio
    async def test_lite_briefing_no_cache(self):
        """When no cache exists, a minimal 'check back soon' briefing is returned."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # no cache
        mock_redis.aclose = AsyncMock()

        with patch(
            "redis.asyncio.from_url",
            return_value=mock_redis,
        ):
            from app.agents.briefing.fallback import generate_lite_briefing

            briefing = await generate_lite_briefing(_USER_ID)

        assert briefing["briefing_type"] == "lite"
        assert "check back soon" in briefing["summary"].lower()
        assert briefing["new_matches"] == []
        assert briefing["metrics"]["total_matches"] == 0

    @pytest.mark.asyncio
    async def test_lite_briefing_from_cache(self):
        """When cache exists, lite briefing includes data from last successful briefing."""
        cached = {
            "summary": "Great day! 3 new matches.",
            "actions_needed": ["Approve application to TechCorp"],
            "new_matches": [
                {"title": "Backend Dev", "company": "TechCorp", "reason": "Python match"},
                {"title": "ML Eng", "company": "DataCo", "reason": "ML skills"},
            ],
            "activity_log": [{"event": "search", "detail": "Searched 50 listings"}],
            "metrics": {"total_matches": 3, "pending_approvals": 1, "applications_sent": 0},
            "generated_at": "2026-01-30T08:00:00+00:00",
        }

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(cached))
        mock_redis.aclose = AsyncMock()

        with patch(
            "redis.asyncio.from_url",
            return_value=mock_redis,
        ):
            from app.agents.briefing.fallback import generate_lite_briefing

            briefing = await generate_lite_briefing(_USER_ID)

        assert briefing["briefing_type"] == "lite"
        assert "trouble" in briefing["summary"].lower()
        # Cached data should be present
        assert len(briefing["new_matches"]) == 2
        assert briefing["metrics"]["total_matches"] == 3
        assert briefing["cached_from"] == "2026-01-30T08:00:00+00:00"

    @pytest.mark.asyncio
    async def test_briefing_retry_scheduled_on_failure(self):
        """When full briefing fails, a retry is scheduled in 1 hour via Celery."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.aclose = AsyncMock()

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock(
            side_effect=lambda obj: setattr(obj, "id", "lite-retry-001")
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_celery = MagicMock()
        mock_celery.send_task = MagicMock()

        with patch(
            "app.agents.briefing.generator.generate_full_briefing",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Database unreachable"),
        ):
            with patch(
                "redis.asyncio.from_url",
                return_value=mock_redis,
            ):
                with patch(
                    "app.db.engine.AsyncSessionLocal",
                    return_value=mock_session,
                ):
                    with patch(
                        "app.worker.celery_app.celery_app",
                        mock_celery,
                    ):
                        from app.agents.briefing.fallback import (
                            generate_briefing_with_fallback,
                        )

                        await generate_briefing_with_fallback(_USER_ID)

        # Verify retry was scheduled with 1h countdown
        mock_celery.send_task.assert_called_once_with(
            "app.worker.tasks.briefing_generate",
            args=[_USER_ID],
            countdown=3600,
            queue="briefings",
        )
