"""Tests for the Applications API endpoints (Stories 5-8, 6-5).

Covers: approval queue, history, detail, status update, and error cases.
"""

from datetime import datetime, timezone
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


def _sample_queue_row(item_id="item-uuid-1", status="pending"):
    """Create a sample approval queue row."""
    return {
        "id": item_id,
        "agent_type": "apply",
        "action_name": "submit_application",
        "payload": {
            "job_id": "job-uuid-123",
            "job_title": "Backend Engineer",
            "company": "BigTech Inc",
            "submission_method": "api",
            "resume_document_id": "resume-uuid",
            "cover_letter_document_id": "cl-uuid",
        },
        "rationale": "High match score",
        "confidence": 0.9,
        "status": status,
        "created_at": datetime(2026, 2, 1, 10, 0, tzinfo=timezone.utc),
        "expires_at": datetime(2026, 2, 3, 10, 0, tzinfo=timezone.utc),
    }


# ---------------------------------------------------------------------------
# Test: List queue (AC1)
# ---------------------------------------------------------------------------


class TestListApprovalQueue:
    """Tests for GET /applications/queue."""

    @pytest.mark.asyncio
    async def test_list_returns_pending_items(self):
        """Returns pending approval items with job details from payload."""
        mock_cm, mock_sess = _mock_session_cm()

        # Count query
        mock_count = MagicMock()
        mock_count.scalar.return_value = 1

        # Items query
        mock_items = MagicMock()
        mock_items.mappings.return_value.all.return_value = [_sample_queue_row()]

        mock_sess.execute = AsyncMock(side_effect=[mock_count, mock_items])

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.applications import list_approval_queue

            result = await list_approval_queue(user_id="user123")

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].job_title == "Backend Engineer"
        assert result.items[0].company == "BigTech Inc"
        assert result.items[0].submission_method == "api"

    @pytest.mark.asyncio
    async def test_list_empty_queue(self):
        """Returns empty list when no pending items."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_count = MagicMock()
        mock_count.scalar.return_value = 0

        mock_items = MagicMock()
        mock_items.mappings.return_value.all.return_value = []

        mock_sess.execute = AsyncMock(side_effect=[mock_count, mock_items])

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.applications import list_approval_queue

            result = await list_approval_queue(user_id="user123")

        assert result.total == 0
        assert result.items == []


# ---------------------------------------------------------------------------
# Test: Queue count (AC5)
# ---------------------------------------------------------------------------


class TestQueueCount:
    """Tests for GET /applications/queue/count."""

    @pytest.mark.asyncio
    async def test_count_returns_pending_count(self):
        """Returns correct count of pending items."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_sess.execute = AsyncMock(return_value=mock_result)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.applications import get_queue_count

            result = await get_queue_count(user_id="user123")

        assert result.count == 3


# ---------------------------------------------------------------------------
# Test: Approve (AC2)
# ---------------------------------------------------------------------------


class TestApproveItem:
    """Tests for POST /applications/queue/{id}/approve."""

    @pytest.mark.asyncio
    async def test_approve_updates_status_and_dispatches(self):
        """Approving item updates status to 'approved' and dispatches task."""
        mock_cm, mock_sess = _mock_session_cm()

        # Select query returns pending item
        mock_select = MagicMock()
        mock_select.mappings.return_value.first.return_value = _sample_queue_row()

        # Update query
        mock_update = MagicMock()

        mock_sess.execute = AsyncMock(side_effect=[mock_select, mock_update])
        mock_sess.commit = AsyncMock()

        with (
            patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm),
            patch(
                "app.agents.orchestrator.dispatch_task",
                new_callable=AsyncMock,
            ) as mock_dispatch,
        ):
            from app.api.v1.applications import approve_item

            result = await approve_item(item_id="item-uuid-1", user_id="user123")

        assert result["status"] == "approved"
        assert result["item_id"] == "item-uuid-1"

        # Verify dispatch was called with payload
        mock_dispatch.assert_called_once()
        call_args = mock_dispatch.call_args
        assert call_args[0][0] == "apply"
        assert call_args[0][1] == "user123"

    @pytest.mark.asyncio
    async def test_approve_not_found_returns_404(self):
        """Returns 404 when item doesn't exist or doesn't belong to user."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_select = MagicMock()
        mock_select.mappings.return_value.first.return_value = None
        mock_sess.execute = AsyncMock(return_value=mock_select)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.applications import approve_item

            with pytest.raises(Exception) as exc_info:
                await approve_item(item_id="nonexistent", user_id="user123")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_approve_already_approved_returns_409(self):
        """Returns 409 when item is already approved."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_select = MagicMock()
        mock_select.mappings.return_value.first.return_value = _sample_queue_row(
            status="approved"
        )
        mock_sess.execute = AsyncMock(return_value=mock_select)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.applications import approve_item

            with pytest.raises(Exception) as exc_info:
                await approve_item(item_id="item-uuid-1", user_id="user123")

        assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# Test: Reject (AC3)
# ---------------------------------------------------------------------------


class TestRejectItem:
    """Tests for POST /applications/queue/{id}/reject."""

    @pytest.mark.asyncio
    async def test_reject_updates_status(self):
        """Rejecting item updates status to 'rejected'."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_select = MagicMock()
        mock_select.mappings.return_value.first.return_value = _sample_queue_row()

        mock_update = MagicMock()
        mock_sess.execute = AsyncMock(side_effect=[mock_select, mock_update])
        mock_sess.commit = AsyncMock()

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.applications import RejectRequest, reject_item

            result = await reject_item(
                item_id="item-uuid-1",
                body=RejectRequest(reason="Not a good fit"),
                user_id="user123",
            )

        assert result["status"] == "rejected"

        # Verify update SQL includes reason
        update_call = mock_sess.execute.call_args_list[1]
        sql_params = update_call[0][1]
        assert sql_params["reason"] == "Not a good fit"

    @pytest.mark.asyncio
    async def test_reject_not_found_returns_404(self):
        """Returns 404 when item doesn't exist."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_select = MagicMock()
        mock_select.mappings.return_value.first.return_value = None
        mock_sess.execute = AsyncMock(return_value=mock_select)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.applications import reject_item

            with pytest.raises(Exception) as exc_info:
                await reject_item(
                    item_id="nonexistent", body=None, user_id="user123"
                )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Test: Batch approve (AC4)
# ---------------------------------------------------------------------------


class TestBatchApprove:
    """Tests for POST /applications/queue/batch-approve."""

    @pytest.mark.asyncio
    async def test_batch_approve_multiple_items(self):
        """Batch approves multiple items successfully."""
        # Each approve call needs its own session
        sessions = []
        for _ in range(2):
            cm, sess = _mock_session_cm()
            mock_select = MagicMock()
            mock_select.mappings.return_value.first.return_value = _sample_queue_row()
            mock_update = MagicMock()
            sess.execute = AsyncMock(side_effect=[mock_select, mock_update])
            sess.commit = AsyncMock()
            sessions.append(cm)

        with (
            patch("app.db.engine.AsyncSessionLocal", side_effect=sessions),
            patch(
                "app.agents.orchestrator.dispatch_task",
                new_callable=AsyncMock,
            ),
        ):
            from app.api.v1.applications import BatchApproveRequest, batch_approve

            result = await batch_approve(
                body=BatchApproveRequest(item_ids=["item-1", "item-2"]),
                user_id="user123",
            )

        assert result.approved == 2
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_batch_approve_empty_list_returns_400(self):
        """Returns 400 when item_ids list is empty."""
        from app.api.v1.applications import BatchApproveRequest, batch_approve

        with pytest.raises(Exception) as exc_info:
            await batch_approve(
                body=BatchApproveRequest(item_ids=[]),
                user_id="user123",
            )

        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Helpers for history tests (Story 5-13)
# ---------------------------------------------------------------------------


def _sample_application_row(
    app_id="app-uuid-1",
    job_id="job-uuid-1",
    app_status="applied",
):
    """Create a sample application row with job join fields."""
    return {
        "id": app_id,
        "job_id": job_id,
        "job_title": "Backend Engineer",
        "company": "BigTech Inc",
        "status": app_status,
        "applied_at": datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc),
        "resume_version_id": "resume-uuid-1",
    }


def _sample_detail_row(app_id="app-uuid-1", job_id="job-uuid-1"):
    """Create a sample application detail row with job URL."""
    return {
        "id": app_id,
        "job_id": job_id,
        "job_title": "Backend Engineer",
        "company": "BigTech Inc",
        "job_url": "https://example.com/job/1",
        "status": "applied",
        "applied_at": datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc),
        "resume_version_id": "resume-uuid-1",
    }


# ---------------------------------------------------------------------------
# Test: List applications (AC1, AC3)
# ---------------------------------------------------------------------------


class TestListApplications:
    """Tests for GET /applications/history."""

    @pytest.mark.asyncio
    async def test_list_returns_applications(self):
        """Returns applications with job details."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_count = MagicMock()
        mock_count.scalar.return_value = 1

        mock_items = MagicMock()
        mock_items.mappings.return_value.all.return_value = [_sample_application_row()]

        mock_sess.execute = AsyncMock(side_effect=[mock_count, mock_items])

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.applications import list_applications

            result = await list_applications(
                user_id="user123", status_filter=None, limit=20, offset=0,
            )

        assert result.total == 1
        assert len(result.applications) == 1
        assert result.applications[0].job_title == "Backend Engineer"
        assert result.applications[0].company == "BigTech Inc"
        assert result.applications[0].status == "applied"
        assert result.has_more is False

    @pytest.mark.asyncio
    async def test_list_with_status_filter(self):
        """Filters applications by status when provided."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_count = MagicMock()
        mock_count.scalar.return_value = 1

        mock_items = MagicMock()
        mock_items.mappings.return_value.all.return_value = [
            _sample_application_row(app_status="applied")
        ]

        mock_sess.execute = AsyncMock(side_effect=[mock_count, mock_items])

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.applications import list_applications

            result = await list_applications(
                user_id="user123", status_filter="applied", limit=20, offset=0,
            )

        assert result.total == 1
        # Verify the SQL included the status filter
        count_call = mock_sess.execute.call_args_list[0]
        sql_params = count_call[0][1]
        assert sql_params["status"] == "applied"

    @pytest.mark.asyncio
    async def test_list_has_more_pagination(self):
        """Returns has_more=True when more results exist beyond limit+offset."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_count = MagicMock()
        mock_count.scalar.return_value = 25  # More than default limit

        mock_items = MagicMock()
        mock_items.mappings.return_value.all.return_value = [_sample_application_row()]

        mock_sess.execute = AsyncMock(side_effect=[mock_count, mock_items])

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.applications import list_applications

            result = await list_applications(
                user_id="user123", status_filter=None, limit=20, offset=0,
            )

        assert result.has_more is True


# ---------------------------------------------------------------------------
# Test: Application detail (AC2)
# ---------------------------------------------------------------------------


class TestApplicationDetail:
    """Tests for GET /applications/detail/{id}."""

    @pytest.mark.asyncio
    async def test_detail_returns_application(self):
        """Returns application with job and cover letter details."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_app = MagicMock()
        mock_app.mappings.return_value.first.return_value = _sample_detail_row()

        mock_cl = MagicMock()
        mock_cl.scalar.return_value = "cl-uuid-1"

        mock_sess.execute = AsyncMock(side_effect=[mock_app, mock_cl])

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.applications import get_application_detail

            result = await get_application_detail(
                application_id="app-uuid-1", user_id="user123"
            )

        assert result.id == "app-uuid-1"
        assert result.job_title == "Backend Engineer"
        assert result.job_url == "https://example.com/job/1"
        assert result.cover_letter_document_id == "cl-uuid-1"

    @pytest.mark.asyncio
    async def test_detail_not_found_returns_404(self):
        """Returns 404 when application doesn't exist."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_app = MagicMock()
        mock_app.mappings.return_value.first.return_value = None

        mock_sess.execute = AsyncMock(return_value=mock_app)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.applications import get_application_detail

            with pytest.raises(Exception) as exc_info:
                await get_application_detail(
                    application_id="nonexistent", user_id="user123"
                )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Test: Update application status (Story 6-5)
# ---------------------------------------------------------------------------


class TestUpdateApplicationStatus:
    """Tests for PATCH /applications/{id}/status."""

    @pytest.mark.asyncio
    async def test_update_status_success(self):
        """Updates application status and creates audit trail."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_select = MagicMock()
        mock_select.mappings.return_value.first.return_value = {
            "id": "app-uuid-1",
            "status": "applied",
        }

        mock_update = MagicMock()
        mock_insert = MagicMock()

        mock_sess.execute = AsyncMock(side_effect=[mock_select, mock_update, mock_insert])
        mock_sess.commit = AsyncMock()

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.applications import UpdateStatusRequest, update_application_status

            result = await update_application_status(
                application_id="app-uuid-1",
                body=UpdateStatusRequest(status="interview"),
                user_id="user123",
            )

        assert result.old_status == "applied"
        assert result.new_status == "interview"

    @pytest.mark.asyncio
    async def test_update_invalid_status_returns_400(self):
        """Returns 400 for invalid status value."""
        from app.api.v1.applications import UpdateStatusRequest, update_application_status

        with pytest.raises(Exception) as exc_info:
            await update_application_status(
                application_id="app-uuid-1",
                body=UpdateStatusRequest(status="invalid_status"),
                user_id="user123",
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_update_not_found_returns_404(self):
        """Returns 404 when application doesn't exist."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_select = MagicMock()
        mock_select.mappings.return_value.first.return_value = None
        mock_sess.execute = AsyncMock(return_value=mock_select)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.applications import UpdateStatusRequest, update_application_status

            with pytest.raises(Exception) as exc_info:
                await update_application_status(
                    application_id="nonexistent",
                    body=UpdateStatusRequest(status="interview"),
                    user_id="user123",
                )

        assert exc_info.value.status_code == 404
