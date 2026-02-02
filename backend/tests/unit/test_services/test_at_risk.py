"""Tests for AtRiskDetectionService and at-risk enterprise endpoints.

Covers:
- Detection criteria (login, applications, pipeline)
- Privacy enforcement (only user_id, name, email, engagement_status)
- Status filtering
- Nudge email sending (mocked)
- Nudge audit logging
- RBAC enforcement (403 for non-admin)
- Celery task structure
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

# ---------------------------------------------------------------------------
# Helpers: lightweight fakes for SQLAlchemy result sets
# ---------------------------------------------------------------------------


class FakeScalarResult:
    """Mimics a SQLAlchemy result that returns rows via .all() or .scalar()."""

    def __init__(self, rows: List[Any]):
        self._rows = rows

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return self._rows[0] if self._rows else None


class FakeSession:
    """Minimal async session fake that routes queries to pre-configured results."""

    def __init__(self, execute_results: List[FakeScalarResult] | None = None):
        self._execute_results = execute_results or []
        self._call_idx = 0
        self._added: list = []

    async def execute(self, stmt, *args, **kwargs):
        if self._call_idx < len(self._execute_results):
            result = self._execute_results[self._call_idx]
            self._call_idx += 1
            return result
        return FakeScalarResult([])

    def add(self, obj):
        self._added.append(obj)

    async def begin(self):
        return FakeTransactionCtx()

    async def commit(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class FakeTransactionCtx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ORG_ID = str(uuid4())
USER_1_ID = uuid4()
USER_2_ID = uuid4()
USER_3_ID = uuid4()

NOW = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Test: Detection — user not logged in 14+ days is flagged at-risk
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_at_risk_login_inactive():
    """User with updated_at > 14 days ago should be flagged at-risk."""
    from app.services.enterprise.at_risk import AtRiskDetectionService

    service = AtRiskDetectionService()

    # Mock session: members query returns USER_1; login check returns USER_1 (inactive);
    # active applicants returns empty; active pipeline returns empty; users with apps returns empty
    session = FakeSession([
        FakeScalarResult([(USER_1_ID,)]),           # members
        FakeScalarResult([(USER_1_ID,)]),           # inactive login (updated_at < threshold)
        FakeScalarResult([]),                        # active applicants (none)
        FakeScalarResult([]),                        # active pipeline (none)
        FakeScalarResult([]),                        # users with apps (none)
    ])

    result = await service.detect_at_risk(session, ORG_ID)
    assert str(USER_1_ID) in result


# ---------------------------------------------------------------------------
# Test: Detection — user with no applications in 30+ days flagged at-risk
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_at_risk_no_recent_applications():
    """User with no applications in 30+ days should be flagged at-risk."""
    from app.services.enterprise.at_risk import AtRiskDetectionService

    service = AtRiskDetectionService()

    session = FakeSession([
        FakeScalarResult([(USER_1_ID,)]),           # members
        FakeScalarResult([]),                        # inactive login (none - user is active)
        FakeScalarResult([]),                        # active applicants (none - no recent apps)
        FakeScalarResult([]),                        # active pipeline (none)
        FakeScalarResult([]),                        # users with apps (none)
    ])

    result = await service.detect_at_risk(session, ORG_ID)
    assert str(USER_1_ID) in result


# ---------------------------------------------------------------------------
# Test: Detection — user with stalled pipeline (21+ days) flagged at-risk
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_at_risk_stalled_pipeline():
    """User with applications but no status changes in 21+ days should be flagged."""
    from app.services.enterprise.at_risk import AtRiskDetectionService

    service = AtRiskDetectionService()

    session = FakeSession([
        FakeScalarResult([(USER_1_ID,)]),           # members
        FakeScalarResult([]),                        # inactive login (none)
        FakeScalarResult([(USER_1_ID,)]),           # active applicants (has recent apps)
        FakeScalarResult([]),                        # active pipeline (no recent updates)
        FakeScalarResult([(USER_1_ID,)]),           # users with apps (has apps)
    ])

    result = await service.detect_at_risk(session, ORG_ID)
    assert str(USER_1_ID) in result


# ---------------------------------------------------------------------------
# Test: Detection — active user is NOT flagged at-risk
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_active_user_not_flagged():
    """User with recent login, applications, and pipeline activity should NOT be flagged."""
    from app.services.enterprise.at_risk import AtRiskDetectionService

    service = AtRiskDetectionService()

    session = FakeSession([
        FakeScalarResult([(USER_1_ID,)]),           # members
        FakeScalarResult([]),                        # inactive login (none - user is active)
        FakeScalarResult([(USER_1_ID,)]),           # active applicants (has recent apps)
        FakeScalarResult([(USER_1_ID,)]),           # active pipeline (has recent updates)
        FakeScalarResult([(USER_1_ID,)]),           # users with apps
    ])

    result = await service.detect_at_risk(session, ORG_ID)
    assert str(USER_1_ID) not in result


# ---------------------------------------------------------------------------
# Test: Privacy enforcement — response contains ONLY allowed fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_privacy_enforcement_only_allowed_fields():
    """get_employee_summaries must return ONLY user_id, name, email, engagement_status."""
    from app.services.enterprise.at_risk import AtRiskDetectionService

    service = AtRiskDetectionService()

    # Mock get_employee_summaries: members query + detect_at_risk queries
    session = FakeSession([
        # get_employee_summaries: members with user info
        FakeScalarResult([(USER_1_ID, "Alice", "alice@example.com")]),
        # detect_at_risk: members
        FakeScalarResult([(USER_1_ID,)]),
        # detect_at_risk: inactive login
        FakeScalarResult([]),
        # detect_at_risk: active applicants
        FakeScalarResult([(USER_1_ID,)]),
        # detect_at_risk: active pipeline
        FakeScalarResult([(USER_1_ID,)]),
        # detect_at_risk: users with apps
        FakeScalarResult([(USER_1_ID,)]),
    ])

    summaries = await service.get_employee_summaries(session, ORG_ID)
    assert len(summaries) == 1

    allowed_keys = {"user_id", "name", "email", "engagement_status"}
    for summary in summaries:
        assert set(summary.keys()) == allowed_keys
        # Must NOT contain any of these privacy-violating keys
        for forbidden in ["application_title", "pipeline", "job_match", "activity"]:
            assert forbidden not in summary


# ---------------------------------------------------------------------------
# Test: Status filtering returns only matching employees
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_filtering():
    """Status filter should return only employees matching the specified status."""
    from app.services.enterprise.at_risk import AtRiskDetectionService

    service = AtRiskDetectionService()

    # Two users: USER_1 is active, USER_2 is at-risk
    session = FakeSession([
        # get_employee_summaries: members with user info
        FakeScalarResult([
            (USER_1_ID, "Alice", "alice@example.com"),
            (USER_2_ID, "Bob", "bob@example.com"),
        ]),
        # detect_at_risk: members
        FakeScalarResult([(USER_1_ID,), (USER_2_ID,)]),
        # detect_at_risk: inactive login - USER_2 is inactive
        FakeScalarResult([(USER_2_ID,)]),
        # detect_at_risk: active applicants - USER_1 has recent apps
        FakeScalarResult([(USER_1_ID,)]),
        # detect_at_risk: active pipeline - USER_1 has recent updates
        FakeScalarResult([(USER_1_ID,)]),
        # detect_at_risk: users with apps - both
        FakeScalarResult([(USER_1_ID,), (USER_2_ID,)]),
    ])

    # Filter for at_risk only
    summaries = await service.get_employee_summaries(session, ORG_ID, status_filter="at_risk")

    # Only Bob should appear (at-risk)
    assert len(summaries) >= 1
    statuses = {s["engagement_status"] for s in summaries}
    assert statuses == {"at_risk"}


# ---------------------------------------------------------------------------
# Test: Nudge sends generic email via Resend (mocked)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nudge_sends_generic_email():
    """send_nudge_email should send a generic email with no personalized data."""
    from app.services.transactional_email import send_nudge_email

    with patch("app.services.transactional_email.send_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"id": "test-email-id"}

        result = await send_nudge_email(
            to="alice@example.com",
            user_name="Alice",
        )

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args
        html_content = call_kwargs.kwargs.get("html") or call_kwargs[1].get("html", "")

        # Email must be generic - no application/pipeline/job-specific content
        assert "career transition tools are ready" in html_content.lower() or "career tools" in html_content.lower()
        assert result["id"] == "test-email-id"


# ---------------------------------------------------------------------------
# Test: Nudge creates AuditLog entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nudge_creates_audit_log():
    """Sending a nudge must create an AuditLog entry with action 'nudge_sent'."""
    from app.services.enterprise.audit import log_audit_event

    session = FakeSession()
    await log_audit_event(
        session=session,
        org_id=ORG_ID,
        actor_id=str(uuid4()),
        action="nudge_sent",
        resource_type="employee",
        resource_id=str(USER_1_ID),
        changes={"target_user_id": str(USER_1_ID)},
    )

    # Verify an AuditLog was added to the session
    assert len(session._added) == 1
    entry = session._added[0]
    assert entry.action == "nudge_sent"
    assert entry.resource_type == "employee"


# ---------------------------------------------------------------------------
# Test: Non-admin user receives 403 Forbidden
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_admin_receives_403():
    """require_admin should raise 403 when user is not an org admin."""
    from fastapi import HTTPException

    from app.auth.admin import require_admin

    # Mock the DB session to return no admin membership
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("app.auth.admin.AsyncSessionLocal") as mock_session_cls:
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user_id=str(uuid4()))

        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Test: Celery task follows standard pattern
# ---------------------------------------------------------------------------


def test_celery_task_registered():
    """detect_at_risk_employees task should exist in tasks module with correct attributes."""
    from app.worker.tasks import detect_at_risk_employees

    assert detect_at_risk_employees.name == "app.worker.tasks.detect_at_risk_employees"
    assert detect_at_risk_employees.queue == "default"


def test_celery_beat_schedule_includes_at_risk():
    """Beat schedule should include daily at-risk detection task."""
    from app.worker.celery_app import celery_app

    # Reload tasks to ensure beat_schedule is populated
    import app.worker.tasks  # noqa: F401

    schedule = celery_app.conf.beat_schedule
    assert "detect-at-risk-employees" in schedule
    entry = schedule["detect-at-risk-employees"]
    assert entry["task"] == "app.worker.tasks.detect_at_risk_employees"
    assert entry["schedule"] == 24 * 60 * 60  # Daily
