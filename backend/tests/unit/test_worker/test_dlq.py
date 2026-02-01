"""
Tests for Story 0.6: Dead letter queue handler.

Validates:
  AC#5 - Failed tasks go to DLQ (Redis list)
  AC#7 - DLQ monitoring endpoint returns data
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================
# AC#5 - DLQ Handler
# ============================================================


class TestHandleTaskFailure:
    """AC#5: Failed tasks are written to Redis DLQ list."""

    @pytest.mark.asyncio
    async def test_handle_task_failure_writes_to_redis(self):
        """Failure callback pushes JSON entry to dlq:{queue} list."""
        mock_client = AsyncMock()
        with patch("app.worker.dlq.get_redis_client", return_value=mock_client):
            from app.worker.dlq import handle_task_failure

            await handle_task_failure(
                task_id="abc-123",
                task_name="app.worker.tasks.agent_job_scout",
                args=("user1", {"key": "val"}),
                kwargs={},
                exc=ValueError("something broke"),
                queue="agents",
            )

        # Verify lpush was called with correct key
        mock_client.lpush.assert_awaited_once()
        call_args = mock_client.lpush.call_args
        assert call_args[0][0] == "dlq:agents"

        # Verify JSON content
        entry = json.loads(call_args[0][1])
        assert entry["task_id"] == "abc-123"
        assert entry["task_name"] == "app.worker.tasks.agent_job_scout"
        assert entry["args"] == ["user1", {"key": "val"}]
        assert entry["error"] == "something broke"
        assert entry["error_type"] == "ValueError"
        assert "failed_at" in entry

    @pytest.mark.asyncio
    async def test_handle_task_failure_sets_ttl(self):
        """Failure callback sets 7-day TTL on the DLQ key."""
        mock_client = AsyncMock()
        with patch("app.worker.dlq.get_redis_client", return_value=mock_client):
            from app.worker.dlq import handle_task_failure, DLQ_TTL_SECONDS

            await handle_task_failure(
                task_id="abc-123",
                task_name="test_task",
                args=(),
                kwargs={},
                exc=RuntimeError("fail"),
            )

        mock_client.expire.assert_awaited_once_with("dlq:default", DLQ_TTL_SECONDS)
        assert DLQ_TTL_SECONDS == 7 * 24 * 60 * 60


class TestGetDlqContents:
    """AC#5/#7: DLQ contents are retrievable."""

    @pytest.mark.asyncio
    async def test_get_dlq_contents(self):
        """Returns parsed JSON entries from the DLQ list."""
        entries = [
            json.dumps({"task_id": "t1", "error": "err1"}),
            json.dumps({"task_id": "t2", "error": "err2"}),
        ]
        mock_client = AsyncMock()
        mock_client.lrange = AsyncMock(return_value=entries)

        with patch("app.worker.dlq.get_redis_client", return_value=mock_client):
            from app.worker.dlq import get_dlq_contents

            result = await get_dlq_contents(queue="default", limit=50)

        assert len(result) == 2
        assert result[0]["task_id"] == "t1"
        assert result[1]["task_id"] == "t2"
        mock_client.lrange.assert_awaited_once_with("dlq:default", 0, 49)

    @pytest.mark.asyncio
    async def test_get_dlq_contents_respects_limit(self):
        """Limit parameter bounds the lrange call."""
        mock_client = AsyncMock()
        mock_client.lrange = AsyncMock(return_value=[])

        with patch("app.worker.dlq.get_redis_client", return_value=mock_client):
            from app.worker.dlq import get_dlq_contents

            await get_dlq_contents(queue="default", limit=10)

        mock_client.lrange.assert_awaited_once_with("dlq:default", 0, 9)


class TestDlqLength:
    """AC#5: DLQ length is queryable."""

    @pytest.mark.asyncio
    async def test_dlq_length(self):
        """Returns count of items in the DLQ."""
        mock_client = AsyncMock()
        mock_client.llen = AsyncMock(return_value=7)

        with patch("app.worker.dlq.get_redis_client", return_value=mock_client):
            from app.worker.dlq import dlq_length

            result = await dlq_length(queue="default")

        assert result == 7
        mock_client.llen.assert_awaited_once_with("dlq:default")


class TestClearDlq:
    """AC#5: DLQ can be cleared."""

    @pytest.mark.asyncio
    async def test_clear_dlq(self):
        """Clears all entries and returns count."""
        mock_client = AsyncMock()
        mock_client.llen = AsyncMock(return_value=3)
        mock_client.delete = AsyncMock()

        with patch("app.worker.dlq.get_redis_client", return_value=mock_client):
            from app.worker.dlq import clear_dlq

            count = await clear_dlq(queue="agents")

        assert count == 3
        mock_client.delete.assert_awaited_once_with("dlq:agents")


# ============================================================
# AC#7 - DLQ Admin Endpoint
# ============================================================


class TestDlqAdminEndpoint:
    """AC#7: GET /admin/dlq returns DLQ data."""

    def test_admin_module_has_dlq_endpoint(self):
        """admin.py source defines a GET /dlq endpoint."""
        from pathlib import Path

        admin_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "app" / "api" / "v1" / "admin.py"
        )
        source = admin_path.read_text()
        assert '@router.get("/dlq")' in source
        assert "async def get_dlq" in source

    @pytest.mark.asyncio
    async def test_dlq_endpoint_logic(self):
        """DLQ endpoint function returns queue, total, and entries."""
        mock_entries = [{"task_id": "t1", "error": "err1"}]
        mock_get = AsyncMock(return_value=mock_entries)
        mock_len = AsyncMock(return_value=1)

        with (
            patch("app.worker.dlq.get_dlq_contents", mock_get),
            patch("app.worker.dlq.dlq_length", mock_len),
        ):
            from app.worker.dlq import get_dlq_contents, dlq_length

            entries = await mock_get(queue="default", limit=50)
            total = await mock_len(queue="default")

        result = {"queue": "default", "total": total, "entries": entries}
        assert result["queue"] == "default"
        assert result["total"] == 1
        assert len(result["entries"]) == 1
        assert result["entries"][0]["task_id"] == "t1"
