"""Tests for Network Approval Service (Story 9-6).

Covers: queue_outreach(), get_pending_outreach(), process_approval(),
hard constraint enforcement, approval context.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import pytest

VALID_UUID = str(uuid.uuid4())

from app.services.network.approval import NetworkApprovalService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    return NetworkApprovalService()


@pytest.fixture
def draft():
    return {
        "recipient_name": "Alice Smith",
        "connection_name": "Bob Jones",
        "target_company": "Acme Corp",
        "message": "Hi Alice! I'd love to connect about Acme.",
        "tone": "professional",
        "word_count": 9,
        "data_quality": "complete",
    }


@pytest.fixture
def context():
    return {
        "path_type": "1st_degree",
        "strength": "strong",
        "mutual_connections": ["Carol"],
    }


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _mock_session():
    """Create a mock AsyncSession context manager."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


def _mock_session_cm(session):
    """Wrap session in async context manager."""
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ---------------------------------------------------------------------------
# AC1: Approval queue integration
# ---------------------------------------------------------------------------


class TestQueueOutreach:
    @pytest.mark.asyncio
    async def test_creates_approval_item(self, service, draft, context):
        """queue_outreach() creates ApprovalQueueItem with correct fields."""
        session = _mock_session()
        session_cm = _mock_session_cm(session)

        with patch(
            "app.db.engine.AsyncSessionLocal",
            return_value=session_cm,
        ), patch(
            "app.cache.redis_client.get_redis_client",
            new_callable=AsyncMock,
        ) as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client

            item_id = await service.queue_outreach("user-1", draft, context)

        assert item_id is not None
        assert len(item_id) > 0
        # Verify session.add was called
        session.add.assert_called_once()
        # Verify the item has correct fields
        added_item = session.add.call_args[0][0]
        assert added_item.agent_type == "network"
        assert added_item.action_name == "outreach_request"
        assert added_item.status == "pending"
        assert added_item.payload["draft"] == draft
        assert added_item.payload["context"] == context

    @pytest.mark.asyncio
    async def test_publishes_redis_event(self, service, draft, context):
        """queue_outreach() publishes approval.new via Redis."""
        session = _mock_session()
        session_cm = _mock_session_cm(session)

        with patch(
            "app.db.engine.AsyncSessionLocal",
            return_value=session_cm,
        ), patch(
            "app.cache.redis_client.get_redis_client",
            new_callable=AsyncMock,
        ) as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client

            await service.queue_outreach("user-1", draft, context)

        mock_client.publish.assert_called_once()
        channel = mock_client.publish.call_args[0][0]
        assert channel == "agent:status:user-1"


# ---------------------------------------------------------------------------
# AC2: Approval actions
# ---------------------------------------------------------------------------


class TestProcessApproval:
    @pytest.mark.asyncio
    async def test_approve_action(self, service):
        """process_approval() with approve sets status to approved."""
        mock_item = MagicMock()
        mock_item.id = VALID_UUID
        mock_item.status = "pending"
        mock_item.payload = {"draft": {"message": "Hi!"}, "context": {}}

        session = _mock_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_item
        session.execute = AsyncMock(return_value=result_mock)
        session_cm = _mock_session_cm(session)

        with patch(
            "app.db.engine.AsyncSessionLocal",
            return_value=session_cm,
        ):
            result = await service.process_approval(VALID_UUID, "approve")

        assert result["status"] == "success"
        assert result["action"] == "approve"
        assert mock_item.status == "approved"

    @pytest.mark.asyncio
    async def test_edit_approve_updates_message(self, service):
        """process_approval() with edit_approve updates the message."""
        mock_item = MagicMock()
        mock_item.id = VALID_UUID
        mock_item.status = "pending"
        mock_item.payload = {"draft": {"message": "Old message"}, "context": {}}

        session = _mock_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_item
        session.execute = AsyncMock(return_value=result_mock)
        session_cm = _mock_session_cm(session)

        with patch(
            "app.db.engine.AsyncSessionLocal",
            return_value=session_cm,
        ):
            result = await service.process_approval(
                VALID_UUID, "edit_approve", edited_message="New message"
            )

        assert result["status"] == "success"
        assert mock_item.status == "approved"
        assert mock_item.payload["draft"]["message"] == "New message"

    @pytest.mark.asyncio
    async def test_reject_action(self, service):
        """process_approval() with reject sets status to rejected."""
        mock_item = MagicMock()
        mock_item.id = VALID_UUID
        mock_item.status = "pending"
        mock_item.payload = {"draft": {"message": "Hi!"}, "context": {}}

        session = _mock_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_item
        session.execute = AsyncMock(return_value=result_mock)
        session_cm = _mock_session_cm(session)

        with patch(
            "app.db.engine.AsyncSessionLocal",
            return_value=session_cm,
        ):
            result = await service.process_approval(VALID_UUID, "reject")

        assert result["status"] == "success"
        assert mock_item.status == "rejected"

    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_error(self, service):
        """process_approval() returns error for invalid UUID."""
        result = await service.process_approval("bad-id", "approve")
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_item_not_found(self, service):
        """process_approval() returns error for missing item."""
        session = _mock_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)
        session_cm = _mock_session_cm(session)

        with patch(
            "app.db.engine.AsyncSessionLocal",
            return_value=session_cm,
        ):
            result = await service.process_approval(
                str(uuid.uuid4()), "approve"
            )

        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# AC3: Hard constraint
# ---------------------------------------------------------------------------


class TestHardConstraint:
    @pytest.mark.asyncio
    async def test_requires_approval_always_true(self):
        """Agent always sets requires_approval=True when drafts exist."""
        from app.agents.core.network_agent import NetworkAgent
        from app.services.network.warm_path import WarmPath
        from app.services.network.intro_drafts import IntroDraft
        from app.services.network.engagement_tracking import EngagementOpportunity

        agent = NetworkAgent()

        mock_paths = [WarmPath(contact_name="Alice", company="Acme")]
        mock_drafts = [IntroDraft(recipient_name="Alice", message="Hi!")]
        mock_opps = [EngagementOpportunity(contact_name="Alice")]

        with patch(
            "app.services.network.warm_path.WarmPathService"
        ) as MockWP, patch(
            "app.services.network.intro_drafts.IntroDraftService"
        ) as MockID, patch(
            "app.services.network.engagement_tracking.EngagementTrackingService"
        ) as MockET, patch(
            "app.services.network.approval.NetworkApprovalService"
        ) as MockApproval:
            MockWP.return_value.analyze = AsyncMock(return_value=mock_paths)
            MockID.return_value.generate = AsyncMock(return_value=mock_drafts)
            MockET.return_value.find_opportunities = AsyncMock(return_value=mock_opps)
            MockApproval.return_value.queue_outreach = AsyncMock(return_value="item-1")

            output = await agent.execute("user-1", {
                "target_companies": ["Acme"],
            })

        assert output.requires_approval is True


# ---------------------------------------------------------------------------
# AC4: Approval context
# ---------------------------------------------------------------------------


class TestApprovalContext:
    @pytest.mark.asyncio
    async def test_payload_includes_context(self, service, draft, context):
        """Approval item payload includes relationship context."""
        session = _mock_session()
        session_cm = _mock_session_cm(session)

        with patch(
            "app.db.engine.AsyncSessionLocal",
            return_value=session_cm,
        ), patch(
            "app.cache.redis_client.get_redis_client",
            new_callable=AsyncMock,
        ) as mock_redis:
            mock_redis.return_value = AsyncMock()

            await service.queue_outreach("user-1", draft, context)

        added = session.add.call_args[0][0]
        payload = added.payload
        assert "draft" in payload
        assert "context" in payload
        assert payload["draft"]["recipient_name"] == "Alice Smith"
        assert payload["context"]["path_type"] == "1st_degree"
