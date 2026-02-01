"""Tests for GDPR data portability endpoints.

Covers data export, account deletion scheduling, deletion cancellation,
and permanent deletion Celery task.

Note: TestClient cannot be used due to a pre-existing ColdEmailRequest
model issue in create_app(). These tests mock at the function level instead.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Data Export Tests (GET /api/v1/users/me/export)
# ---------------------------------------------------------------------------


class TestDataExport:
    """Tests for GDPR data export function."""

    @pytest.mark.asyncio
    async def test_export_returns_all_sections(self):
        """Export returns profile, applications, documents, agent_actions."""
        mock_sess = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = {
            "clerk_id": "user_test_123",
            "email": "test@example.com",
        }
        mock_result.mappings.return_value.all.return_value = []
        mock_sess.execute = AsyncMock(return_value=mock_result)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.users import export_user_data

            data = await export_user_data(user_id="user_test_123")

        assert "export_metadata" in data
        assert "profile" in data
        assert "applications" in data
        assert "documents" in data
        assert "agent_actions" in data
        assert data["export_metadata"]["user_id"] == "user_test_123"
        assert data["export_metadata"]["format_version"] == "1.0"

    @pytest.mark.asyncio
    async def test_export_handles_db_errors_gracefully(self):
        """Export returns partial data when database is unreachable."""
        with patch(
            "app.db.engine.AsyncSessionLocal",
            side_effect=Exception("DB unavailable"),
        ):
            from app.api.v1.users import export_user_data

            data = await export_user_data(user_id="user_test_123")

        assert "export_metadata" in data
        assert "error" in data["export_metadata"]


# ---------------------------------------------------------------------------
# Account Deletion Tests (DELETE /api/v1/users/me)
# ---------------------------------------------------------------------------


class TestAccountDeletion:
    """Tests for GDPR account deletion function."""

    @pytest.mark.asyncio
    async def test_delete_sets_deleted_at_and_sends_email(self):
        """Delete handler sets deleted_at, sends email, schedules task."""
        mock_sess = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_sess.execute = AsyncMock()
        mock_sess.commit = AsyncMock()

        mock_email = AsyncMock()
        mock_task = MagicMock()

        with (
            patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm),
            patch(
                "app.services.transactional_email.send_account_deletion_notice", mock_email
            ),
            patch("app.worker.tasks.gdpr_permanent_delete", mock_task),
        ):
            from app.api.v1.users import delete_user_account

            response = await delete_user_account(user_id="user_test_123")

        data = response.body.decode()
        import json

        body = json.loads(data)

        assert body["message"] == "Account scheduled for deletion"
        assert body["grace_period_days"] == 30
        assert body["cancellation_window_days"] == 14

        # Email was sent
        mock_email.assert_called_once()

        # Celery task was scheduled with eta
        mock_task.apply_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_handles_db_error_gracefully(self):
        """Delete still returns 200 even if DB is unreachable."""
        mock_email = AsyncMock()
        mock_task = MagicMock()

        with (
            patch(
                "app.db.engine.AsyncSessionLocal",
                side_effect=Exception("DB error"),
            ),
            patch(
                "app.services.transactional_email.send_account_deletion_notice", mock_email
            ),
            patch("app.worker.tasks.gdpr_permanent_delete", mock_task),
        ):
            from app.api.v1.users import delete_user_account

            response = await delete_user_account(user_id="user_test_123")

        import json

        body = json.loads(response.body.decode())
        assert body["message"] == "Account scheduled for deletion"


# ---------------------------------------------------------------------------
# Deletion Cancellation Tests (POST /api/v1/users/me/cancel-deletion)
# ---------------------------------------------------------------------------


class TestDeletionCancellation:
    """Tests for deletion cancellation function."""

    @pytest.mark.asyncio
    async def test_cancel_deletion_clears_deleted_at(self):
        """Cancel-deletion clears deleted_at and returns success."""
        mock_sess = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "user_test_123"
        mock_sess.execute = AsyncMock(return_value=mock_result)
        mock_sess.commit = AsyncMock()

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.users import cancel_deletion

            result = await cancel_deletion(user_id="user_test_123")

        assert result["message"] == "Account deletion cancelled"

    @pytest.mark.asyncio
    async def test_cancel_deletion_no_pending_returns_404(self):
        """Cancel-deletion returns 404 when no pending deletion exists."""
        mock_sess = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_sess.execute = AsyncMock(return_value=mock_result)
        mock_sess.commit = AsyncMock()

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.users import cancel_deletion

            result = await cancel_deletion(user_id="user_test_123")

        import json

        body = json.loads(result.body.decode())
        assert body["message"] == "No pending deletion found for this account"


# ---------------------------------------------------------------------------
# Permanent Deletion Celery Task Tests
# ---------------------------------------------------------------------------


class TestPermanentDeletionTask:
    """Tests for gdpr_permanent_delete Celery task."""

    def test_permanent_delete_removes_user(self):
        """Task hard-deletes user when deleted_at is still set."""
        mock_sess = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        # First query: check deleted_at — return a row with a timestamp
        mock_result = MagicMock()
        mock_result.first.return_value = (datetime(2026, 1, 1, tzinfo=timezone.utc),)
        mock_sess.execute = AsyncMock(return_value=mock_result)
        mock_sess.commit = AsyncMock()

        with (
            patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm),
            patch(
                "app.services.storage_service.delete_file",
                new_callable=AsyncMock,
            ),
        ):
            from app.worker.tasks import gdpr_permanent_delete

            result = gdpr_permanent_delete("user_test_123")

        assert result["status"] == "deleted"
        assert result["user_id"] == "user_test_123"

    def test_permanent_delete_skips_when_cancelled(self):
        """Task skips deletion when deleted_at has been cleared."""
        mock_sess = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        mock_result = MagicMock()
        mock_result.first.return_value = (None,)
        mock_sess.execute = AsyncMock(return_value=mock_result)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.worker.tasks import gdpr_permanent_delete

            result = gdpr_permanent_delete("user_test_123")

        assert result["status"] == "skipped"
        assert result["reason"] == "deletion_cancelled"

    def test_permanent_delete_skips_when_user_not_found(self):
        """Task skips when user record doesn't exist."""
        mock_sess = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_sess.execute = AsyncMock(return_value=mock_result)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.worker.tasks import gdpr_permanent_delete

            result = gdpr_permanent_delete("nonexistent_user")

        assert result["status"] == "skipped"
        assert result["reason"] == "user_not_found"
