"""Tests for Prep Briefing Delivery Service (Story 8-6).

Covers: multi-channel delivery, 24h scheduling, 2h reminder,
graceful degradation on channel failure, pipeline card access.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.research.prep_delivery import (
    DeliveryResult,
    PrepBriefingDeliveryService,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    return PrepBriefingDeliveryService()


@pytest.fixture
def sample_briefing():
    return {
        "application_id": "app-123",
        "company_name": "Acme Corp",
        "role_title": "Backend Engineer",
        "summary": {
            "total_questions": 12,
            "interviewers_researched": 2,
        },
    }


@pytest.fixture
def future_interview():
    return datetime.now(timezone.utc) + timedelta(days=1)


# ---------------------------------------------------------------------------
# AC1: 24h delivery
# ---------------------------------------------------------------------------


class TestDelivery:
    @pytest.mark.asyncio
    async def test_delivers_to_all_channels(self, service, sample_briefing):
        """deliver() sends to in_app, email, push channels."""
        with patch.object(
            service, "_deliver_in_app", new_callable=AsyncMock
        ), patch.object(
            service, "_deliver_email", new_callable=AsyncMock
        ), patch.object(
            service, "_deliver_push", new_callable=AsyncMock
        ):
            result = await service.deliver(
                "user-1", sample_briefing, "app-123"
            )

        assert isinstance(result, DeliveryResult)
        assert "in_app" in result.channels_sent
        assert "email" in result.channels_sent
        assert "push" in result.channels_sent
        assert result.channels_failed == []

    @pytest.mark.asyncio
    async def test_delivers_to_specific_channels(self, service, sample_briefing):
        """deliver() only sends to specified channels."""
        with patch.object(
            service, "_deliver_in_app", new_callable=AsyncMock
        ), patch.object(
            service, "_deliver_email", new_callable=AsyncMock
        ):
            result = await service.deliver(
                "user-1", sample_briefing, "app-123",
                channels=["in_app", "email"],
            )

        assert result.channels_sent == ["in_app", "email"]

    @pytest.mark.asyncio
    async def test_result_has_briefing_id(self, service, sample_briefing):
        """Result includes briefing_id based on application_id."""
        with patch.object(
            service, "_deliver_in_app", new_callable=AsyncMock
        ), patch.object(
            service, "_deliver_email", new_callable=AsyncMock
        ), patch.object(
            service, "_deliver_push", new_callable=AsyncMock
        ):
            result = await service.deliver(
                "user-1", sample_briefing, "app-123"
            )

        assert result.briefing_id == "briefing-app-123"

    @pytest.mark.asyncio
    async def test_result_to_dict(self, service, sample_briefing):
        """to_dict() serializes correctly."""
        with patch.object(
            service, "_deliver_in_app", new_callable=AsyncMock
        ), patch.object(
            service, "_deliver_email", new_callable=AsyncMock
        ), patch.object(
            service, "_deliver_push", new_callable=AsyncMock
        ):
            result = await service.deliver(
                "user-1", sample_briefing, "app-123"
            )

        d = result.to_dict()
        assert "channels_sent" in d
        assert "channels_failed" in d
        assert "reminder_scheduled" in d
        assert "delivery_time" in d
        assert "briefing_id" in d


# ---------------------------------------------------------------------------
# AC2: Channel failure graceful degradation
# ---------------------------------------------------------------------------


class TestChannelFailure:
    @pytest.mark.asyncio
    async def test_channel_failure_recorded(self, service, sample_briefing):
        """Failed channels are recorded without blocking others."""
        with patch.object(
            service, "_deliver_in_app", new_callable=AsyncMock
        ), patch.object(
            service, "_deliver_email", new_callable=AsyncMock,
            side_effect=Exception("SMTP down"),
        ), patch.object(
            service, "_deliver_push", new_callable=AsyncMock
        ):
            result = await service.deliver(
                "user-1", sample_briefing, "app-123"
            )

        assert "in_app" in result.channels_sent
        assert "push" in result.channels_sent
        assert "email" in result.channels_failed


# ---------------------------------------------------------------------------
# AC4: 2h reminder scheduling
# ---------------------------------------------------------------------------


class TestReminderScheduling:
    @pytest.mark.asyncio
    async def test_reminder_scheduled(self, service, sample_briefing, future_interview):
        """Reminder scheduled 2h before interview."""
        mock_task = MagicMock()
        mock_task.id = "celery-reminder-1"

        with patch.object(
            service, "_deliver_in_app", new_callable=AsyncMock
        ), patch.object(
            service, "_deliver_email", new_callable=AsyncMock
        ), patch.object(
            service, "_deliver_push", new_callable=AsyncMock
        ), patch(
            "app.worker.celery_app.celery_app"
        ) as mock_celery:
            mock_celery.send_task.return_value = mock_task

            result = await service.deliver(
                "user-1", sample_briefing, "app-123",
                interview_datetime=future_interview,
            )

        assert result.reminder_scheduled is True
        assert result.reminder_time is not None

    @pytest.mark.asyncio
    async def test_no_reminder_when_too_late(self, service, sample_briefing):
        """No reminder when interview is less than 2h away."""
        soon = datetime.now(timezone.utc) + timedelta(hours=1)

        with patch.object(
            service, "_deliver_in_app", new_callable=AsyncMock
        ), patch.object(
            service, "_deliver_email", new_callable=AsyncMock
        ), patch.object(
            service, "_deliver_push", new_callable=AsyncMock
        ):
            result = await service.deliver(
                "user-1", sample_briefing, "app-123",
                interview_datetime=soon,
            )

        assert result.reminder_scheduled is False

    @pytest.mark.asyncio
    async def test_no_reminder_without_datetime(self, service, sample_briefing):
        """No reminder when no interview_datetime provided."""
        with patch.object(
            service, "_deliver_in_app", new_callable=AsyncMock
        ), patch.object(
            service, "_deliver_email", new_callable=AsyncMock
        ), patch.object(
            service, "_deliver_push", new_callable=AsyncMock
        ):
            result = await service.deliver(
                "user-1", sample_briefing, "app-123"
            )

        assert result.reminder_scheduled is False
