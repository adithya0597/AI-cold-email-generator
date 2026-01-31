"""
Tests for the emergency brake module.

Verifies Phase 3 Success Criterion #1:
    "The emergency brake button is visible on every page, and pressing it
     pauses all agent activity for that user within 30 seconds."

These tests verify the backend brake state machine:
    RUNNING -> PAUSING -> PAUSED -> RESUMING -> RUNNING
                     \\-> PARTIAL (some tasks stuck)

All Redis and Celery interactions are mocked -- no real connections needed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.brake import (
    BrakeState,
    activate_brake,
    check_brake,
    check_brake_or_raise,
    get_brake_state,
    resume_agents,
    verify_brake_completion,
)

_USER_ID = "test-user-brake-00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# activate_brake tests
# ---------------------------------------------------------------------------


class TestActivateBrake:
    """Tests for activate_brake() -- sets flag, transitions to PAUSING, publishes event."""

    @pytest.mark.asyncio
    async def test_activate_brake_sets_redis_flag(self, mock_redis):
        """activate_brake creates the ``paused:{user_id}`` key in Redis."""
        with patch("app.agents.brake._get_redis", return_value=mock_redis):
            with patch("app.agents.brake.celery_app", create=True):
                with patch(
                    "app.worker.celery_app.celery_app",
                    new_callable=MagicMock,
                ) as mock_celery:
                    mock_celery.send_task = MagicMock()
                    with patch(
                        "app.agents.brake.celery_app",
                        mock_celery,
                        create=True,
                    ):
                        result = await activate_brake(_USER_ID)

        # Verify Redis SET was called with the brake flag key
        mock_redis.set.assert_awaited_once_with(f"paused:{_USER_ID}", "1")
        assert result["state"] == "pausing"
        assert "activated_at" in result

    @pytest.mark.asyncio
    async def test_activate_brake_transitions_to_pausing(self, mock_redis):
        """After activation, brake_state hash shows 'pausing'."""
        with patch("app.agents.brake._get_redis", return_value=mock_redis):
            with patch(
                "app.worker.celery_app.celery_app",
                new_callable=MagicMock,
            ) as mock_celery:
                mock_celery.send_task = MagicMock()
                result = await activate_brake(_USER_ID)

        # Verify hset was called to set state to PAUSING
        hset_calls = mock_redis.hset.await_args_list
        assert len(hset_calls) >= 1
        first_call = hset_calls[0]
        # The first hset call sets the state machine
        assert first_call.args[0] == f"brake_state:{_USER_ID}"
        mapping = first_call.kwargs.get("mapping", {})
        assert mapping["state"] == BrakeState.PAUSING.value

    @pytest.mark.asyncio
    async def test_activate_brake_publishes_websocket_event(self, mock_redis):
        """activate_brake publishes a system.brake.activated event via Redis pub/sub."""
        with patch("app.agents.brake._get_redis", return_value=mock_redis):
            with patch(
                "app.worker.celery_app.celery_app",
                new_callable=MagicMock,
            ) as mock_celery:
                mock_celery.send_task = MagicMock()
                await activate_brake(_USER_ID)

        # Verify publish was called
        mock_redis.publish.assert_awaited_once()
        publish_args = mock_redis.publish.await_args
        channel = publish_args.args[0]
        payload = json.loads(publish_args.args[1])

        assert channel == f"agent:status:{_USER_ID}"
        assert payload["type"] == "system.brake.activated"
        assert payload["state"] == "pausing"
        assert payload["user_id"] == _USER_ID


# ---------------------------------------------------------------------------
# check_brake tests
# ---------------------------------------------------------------------------


class TestCheckBrake:
    """Tests for check_brake() and check_brake_or_raise()."""

    @pytest.mark.asyncio
    async def test_check_brake_returns_true_when_active(self, mock_redis):
        """check_brake returns True when the paused:{user_id} key exists."""
        mock_redis.exists = AsyncMock(return_value=1)

        with patch("app.agents.brake._get_redis", return_value=mock_redis):
            result = await check_brake(_USER_ID)

        assert result is True
        mock_redis.exists.assert_awaited_once_with(f"paused:{_USER_ID}")

    @pytest.mark.asyncio
    async def test_check_brake_returns_false_when_inactive(self, mock_redis):
        """check_brake returns False when the key does not exist."""
        mock_redis.exists = AsyncMock(return_value=0)

        with patch("app.agents.brake._get_redis", return_value=mock_redis):
            result = await check_brake(_USER_ID)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_brake_or_raise_raises_when_active(self, mock_redis):
        """check_brake_or_raise raises BrakeActive when brake is on."""
        from app.agents.base import BrakeActive

        mock_redis.exists = AsyncMock(return_value=1)

        with patch("app.agents.brake._get_redis", return_value=mock_redis):
            with pytest.raises(BrakeActive):
                await check_brake_or_raise(_USER_ID)

    @pytest.mark.asyncio
    async def test_check_brake_or_raise_passes_when_inactive(self, mock_redis):
        """check_brake_or_raise returns None when brake is off."""
        mock_redis.exists = AsyncMock(return_value=0)

        with patch("app.agents.brake._get_redis", return_value=mock_redis):
            result = await check_brake_or_raise(_USER_ID)

        assert result is None


# ---------------------------------------------------------------------------
# resume_agents tests
# ---------------------------------------------------------------------------


class TestResumeAgents:
    """Tests for resume_agents() -- clears flag, transitions to RUNNING."""

    @pytest.mark.asyncio
    async def test_resume_clears_brake_flag(self, mock_redis):
        """resume_agents deletes the paused:{user_id} key and sets state to RUNNING."""
        with patch("app.agents.brake._get_redis", return_value=mock_redis):
            result = await resume_agents(_USER_ID)

        mock_redis.delete.assert_awaited_once_with(f"paused:{_USER_ID}")
        assert result["state"] == "running"

    @pytest.mark.asyncio
    async def test_resume_publishes_event(self, mock_redis):
        """resume_agents publishes a system.brake.resumed event."""
        with patch("app.agents.brake._get_redis", return_value=mock_redis):
            await resume_agents(_USER_ID)

        mock_redis.publish.assert_awaited_once()
        payload = json.loads(mock_redis.publish.await_args.args[1])
        assert payload["type"] == "system.brake.resumed"
        assert payload["state"] == "running"

    @pytest.mark.asyncio
    async def test_resume_transitions_through_resuming(self, mock_redis):
        """resume_agents transitions through RESUMING before reaching RUNNING."""
        with patch("app.agents.brake._get_redis", return_value=mock_redis):
            await resume_agents(_USER_ID)

        hset_calls = mock_redis.hset.await_args_list
        # First hset: state=resuming, second hset: state=running
        assert len(hset_calls) == 2
        assert hset_calls[0].args[2] == BrakeState.RESUMING.value
        assert hset_calls[1].args[2] == BrakeState.RUNNING.value


# ---------------------------------------------------------------------------
# get_brake_state tests
# ---------------------------------------------------------------------------


class TestGetBrakeState:
    """Tests for get_brake_state()."""

    @pytest.mark.asyncio
    async def test_get_state_default_running(self, mock_redis):
        """When no brake state exists, defaults to RUNNING."""
        mock_redis.hgetall = AsyncMock(return_value={})

        with patch("app.agents.brake._get_redis", return_value=mock_redis):
            state = await get_brake_state(_USER_ID)

        assert state["state"] == "running"
        assert state["activated_at"] is None
        assert state["paused_tasks_count"] == 0

    @pytest.mark.asyncio
    async def test_get_state_returns_stored_state(self, mock_redis):
        """Returns the state stored in the Redis hash."""
        mock_redis.hgetall = AsyncMock(
            return_value={
                "state": "paused",
                "activated_at": "2026-01-31T12:00:00+00:00",
                "paused_tasks_count": "3",
            }
        )

        with patch("app.agents.brake._get_redis", return_value=mock_redis):
            state = await get_brake_state(_USER_ID)

        assert state["state"] == "paused"
        assert state["paused_tasks_count"] == 3


# ---------------------------------------------------------------------------
# verify_brake_completion tests
# ---------------------------------------------------------------------------


class TestVerifyBrakeCompletion:
    """Tests for verify_brake_completion() -- PAUSING -> PAUSED or PARTIAL."""

    @pytest.mark.asyncio
    async def test_verify_completion_transitions_to_paused(self, mock_redis):
        """When no Celery tasks are running, state transitions to PAUSED."""
        mock_redis.exists = AsyncMock(return_value=1)  # brake still active

        mock_inspector = MagicMock()
        mock_inspector.active = MagicMock(return_value={})  # no active tasks

        mock_celery = MagicMock()
        mock_celery.control.inspect = MagicMock(return_value=mock_inspector)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.agents.brake._get_redis", return_value=mock_redis):
            with patch(
                "app.worker.celery_app.celery_app", mock_celery
            ):
                with patch(
                    "app.agents.brake.AsyncSessionLocal",
                    return_value=mock_session,
                    create=True,
                ):
                    with patch("app.db.engine.AsyncSessionLocal", return_value=mock_session):
                        result = await verify_brake_completion(_USER_ID)

        assert result["state"] == "paused"

    @pytest.mark.asyncio
    async def test_verify_completion_transitions_to_partial(self, mock_redis):
        """When some Celery tasks are stuck, state transitions to PARTIAL."""
        mock_redis.exists = AsyncMock(return_value=1)

        # Simulate a stuck task for our user
        mock_inspector = MagicMock()
        mock_inspector.active = MagicMock(
            return_value={
                "worker1": [
                    {
                        "id": "stuck-task-001",
                        "args": [_USER_ID, {}],
                    }
                ]
            }
        )

        mock_celery = MagicMock()
        mock_celery.control.inspect = MagicMock(return_value=mock_inspector)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.agents.brake._get_redis", return_value=mock_redis):
            with patch(
                "app.worker.celery_app.celery_app", mock_celery
            ):
                with patch("app.db.engine.AsyncSessionLocal", return_value=mock_session):
                    result = await verify_brake_completion(_USER_ID)

        assert result["state"] == "partial"

    @pytest.mark.asyncio
    async def test_verify_skips_if_brake_already_cleared(self, mock_redis):
        """If user resumed before verification runs, returns RUNNING."""
        mock_redis.exists = AsyncMock(return_value=0)  # brake already cleared

        with patch("app.agents.brake._get_redis", return_value=mock_redis):
            result = await verify_brake_completion(_USER_ID)

        assert result["state"] == "running"

    @pytest.mark.asyncio
    async def test_approval_items_paused_on_brake(self, mock_redis):
        """verify_brake_completion marks pending approvals as 'paused'."""
        mock_redis.exists = AsyncMock(return_value=1)

        mock_inspector = MagicMock()
        mock_inspector.active = MagicMock(return_value={})

        mock_celery = MagicMock()
        mock_celery.control.inspect = MagicMock(return_value=mock_inspector)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.agents.brake._get_redis", return_value=mock_redis):
            with patch(
                "app.worker.celery_app.celery_app", mock_celery
            ):
                with patch("app.db.engine.AsyncSessionLocal", return_value=mock_session):
                    await verify_brake_completion(_USER_ID)

        # The session.execute should have been called with an UPDATE statement
        # to set status="paused" on pending approval items
        mock_session.execute.assert_awaited()
        mock_session.commit.assert_awaited()
