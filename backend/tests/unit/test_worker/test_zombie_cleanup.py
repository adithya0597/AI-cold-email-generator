"""
Tests for Story 0.6: Zombie task cleanup.

Validates:
  AC#6 - Zombie task detection and revocation
  AC#6 - Cleanup registered in beat_schedule at 5-minute interval
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.worker.celery_app import celery_app


# ============================================================
# AC#6 - Zombie Task Detection & Revocation
# ============================================================


class TestCleanupZombieTasks:
    """AC#6: Stale tasks are detected and revoked."""

    def test_cleanup_revokes_stale_tasks(self):
        """Tasks running longer than hard timeout are revoked."""
        now = datetime.now(timezone.utc).timestamp()
        stale_start = now - 400  # 400s ago, exceeds 300s hard timeout

        mock_inspector = MagicMock()
        mock_inspector.active.return_value = {
            "worker1@host": [
                {
                    "id": "stale-task-1",
                    "name": "app.worker.tasks.agent_job_scout",
                    "time_start": stale_start,
                },
            ],
        }

        mock_control = MagicMock()
        mock_control.inspect.return_value = mock_inspector

        with patch.object(celery_app, "control", mock_control):
            from app.worker.tasks import cleanup_zombie_tasks

            result = cleanup_zombie_tasks()

        assert result["revoked_count"] == 1
        assert result["details"][0]["task_id"] == "stale-task-1"
        mock_control.revoke.assert_called_once_with("stale-task-1", terminate=True)

    def test_cleanup_ignores_healthy_tasks(self):
        """Tasks within the timeout are not revoked."""
        now = datetime.now(timezone.utc).timestamp()
        recent_start = now - 10  # 10s ago, well within 300s limit

        mock_inspector = MagicMock()
        mock_inspector.active.return_value = {
            "worker1@host": [
                {
                    "id": "healthy-task-1",
                    "name": "app.worker.tasks.example_task",
                    "time_start": recent_start,
                },
            ],
        }

        mock_control = MagicMock()
        mock_control.inspect.return_value = mock_inspector

        with patch.object(celery_app, "control", mock_control):
            from app.worker.tasks import cleanup_zombie_tasks

            result = cleanup_zombie_tasks()

        assert result["revoked_count"] == 0
        assert result["details"] == []
        mock_control.revoke.assert_not_called()

    def test_cleanup_handles_no_workers(self):
        """Gracefully handles inspect returning None (no workers online)."""
        mock_inspector = MagicMock()
        mock_inspector.active.return_value = None

        mock_control = MagicMock()
        mock_control.inspect.return_value = mock_inspector

        with patch.object(celery_app, "control", mock_control):
            from app.worker.tasks import cleanup_zombie_tasks

            result = cleanup_zombie_tasks()

        assert result["revoked_count"] == 0
        assert result["note"] == "no workers online"


# ============================================================
# AC#6 - Beat Schedule Registration
# ============================================================


class TestZombieCleanupSchedule:
    """AC#6: Zombie cleanup is in beat_schedule at 300s interval."""

    def test_cleanup_in_beat_schedule(self):
        """beat_schedule contains cleanup-zombie-tasks entry."""
        # Import tasks to ensure beat_schedule is populated
        import app.worker.tasks  # noqa: F401

        schedule = celery_app.conf.beat_schedule
        assert "cleanup-zombie-tasks" in schedule

    def test_cleanup_schedule_interval(self):
        """Zombie cleanup runs every 300 seconds (5 minutes)."""
        import app.worker.tasks  # noqa: F401

        entry = celery_app.conf.beat_schedule["cleanup-zombie-tasks"]
        assert entry["schedule"] == 300

    def test_cleanup_schedule_task_name(self):
        """Zombie cleanup points to correct task name."""
        import app.worker.tasks  # noqa: F401

        entry = celery_app.conf.beat_schedule["cleanup-zombie-tasks"]
        assert entry["task"] == "app.worker.tasks.cleanup_zombie_tasks"
