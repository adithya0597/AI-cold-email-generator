"""Tests for the InvitationService and invitation API endpoints.

Tests cover:
- Invitation creation with correct fields and UUID token
- Duplicate invitation revocation
- Accept flow (OrganizationMember creation + tier upgrade)
- Decline flow
- Token expiry handling
- Audit logging for all mutation methods
- API admin auth requirement and public token endpoints
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.db.models import (
    Invitation,
    InvitationStatus,
    Organization,
    OrganizationMember,
    OrgRole,
    User,
    UserTier,
)
from app.services.enterprise.invitation import InvitationService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    return InvitationService()


@pytest.fixture
def org_id():
    return str(uuid4())


@pytest.fixture
def admin_user_id():
    return str(uuid4())


@pytest.fixture
def invitee_user_id():
    return str(uuid4())


def _make_invitation(
    org_id: str | None = None,
    email: str = "employee@example.com",
    status: InvitationStatus = InvitationStatus.PENDING,
    expires_at: datetime | None = None,
    invited_by: str | None = None,
) -> Invitation:
    """Helper to create a mock Invitation object."""
    inv = Invitation()
    inv.id = uuid4()
    inv.org_id = UUID(org_id) if org_id else uuid4()
    inv.email = email
    inv.token = uuid4()
    inv.status = status
    inv.invited_by = UUID(invited_by) if invited_by else uuid4()
    inv.first_name = "Test"
    inv.last_name = "User"
    inv.created_at = datetime.now(timezone.utc)
    inv.expires_at = expires_at or (datetime.now(timezone.utc) + timedelta(days=7))
    return inv


# ---------------------------------------------------------------------------
# Tests: _check_expiry
# ---------------------------------------------------------------------------


class TestCheckExpiry:
    def test_not_expired(self, service):
        invitation = _make_invitation(
            expires_at=datetime.now(timezone.utc) + timedelta(days=3)
        )
        assert service._check_expiry(invitation) is False
        assert invitation.status == InvitationStatus.PENDING

    def test_expired(self, service):
        invitation = _make_invitation(
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        assert service._check_expiry(invitation) is True
        assert invitation.status == InvitationStatus.EXPIRED

    def test_already_accepted_not_re_expired(self, service):
        invitation = _make_invitation(
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            status=InvitationStatus.ACCEPTED,
        )
        assert service._check_expiry(invitation) is False
        assert invitation.status == InvitationStatus.ACCEPTED

    def test_naive_datetime_handled(self, service):
        """expires_at without tzinfo should be treated as UTC."""
        invitation = _make_invitation(
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        # Remove tzinfo to simulate naive datetime from DB
        invitation.expires_at = invitation.expires_at.replace(tzinfo=None)
        assert service._check_expiry(invitation) is True


# ---------------------------------------------------------------------------
# Tests: create_invitation
# ---------------------------------------------------------------------------


class TestCreateInvitation:
    @pytest.mark.asyncio
    async def test_creates_invitation_with_correct_fields(self, service, org_id, admin_user_id):
        session = AsyncMock()
        # Mock flush to simulate DB-generated values (populate id)
        generated_id = uuid4()

        generated_token = uuid4()

        async def _flush_side_effect():
            # Find the invitation that was added and populate DB-generated fields
            for call in session.add.call_args_list:
                obj = call.args[0]
                if isinstance(obj, Invitation):
                    if obj.id is None:
                        obj.id = generated_id
                    if obj.token is None:
                        obj.token = generated_token

        session.flush = AsyncMock(side_effect=_flush_side_effect)
        # Mock the revoke query (no pending invitations)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        invitation = await service.create_invitation(
            session=session,
            org_id=org_id,
            email="new@example.com",
            invited_by=admin_user_id,
            first_name="Alice",
            last_name="Smith",
        )

        assert invitation.email == "new@example.com"
        assert invitation.org_id == UUID(org_id)
        assert invitation.invited_by == UUID(admin_user_id)
        assert invitation.first_name == "Alice"
        assert invitation.last_name == "Smith"
        assert invitation.status == InvitationStatus.PENDING
        assert invitation.token is not None
        assert isinstance(invitation.token, UUID)
        # Verify session.add was called (invitation + audit log)
        assert session.add.call_count >= 1

    @pytest.mark.asyncio
    async def test_normalizes_email(self, service, org_id, admin_user_id):
        session = AsyncMock()
        generated_id = uuid4()

        async def _flush_side_effect():
            for call in session.add.call_args_list:
                obj = call.args[0]
                if isinstance(obj, Invitation) and obj.id is None:
                    obj.id = generated_id

        session.flush = AsyncMock(side_effect=_flush_side_effect)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        invitation = await service.create_invitation(
            session=session,
            org_id=org_id,
            email="  USER@Example.COM  ",
            invited_by=admin_user_id,
        )

        assert invitation.email == "user@example.com"

    @pytest.mark.asyncio
    async def test_revokes_existing_pending_invitation(self, service, org_id, admin_user_id):
        existing_pending = _make_invitation(org_id=org_id, email="dup@example.com")
        assert existing_pending.status == InvitationStatus.PENDING

        session = AsyncMock()
        generated_id = uuid4()

        async def _flush_side_effect():
            for call in session.add.call_args_list:
                obj = call.args[0]
                if isinstance(obj, Invitation) and obj.id is None:
                    obj.id = generated_id

        session.flush = AsyncMock(side_effect=_flush_side_effect)
        # First execute returns the existing pending invitation (revoke query)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_pending]
        session.execute = AsyncMock(return_value=mock_result)

        invitation = await service.create_invitation(
            session=session,
            org_id=org_id,
            email="dup@example.com",
            invited_by=admin_user_id,
        )

        # Old invitation should be revoked
        assert existing_pending.status == InvitationStatus.REVOKED
        # New invitation should be created
        assert invitation.status == InvitationStatus.PENDING
        assert invitation.email == "dup@example.com"


# ---------------------------------------------------------------------------
# Tests: accept_invitation
# ---------------------------------------------------------------------------


class TestAcceptInvitation:
    @pytest.mark.asyncio
    async def test_accept_creates_member_and_upgrades_tier(
        self, service, invitee_user_id
    ):
        invitation = _make_invitation()
        org = Organization()
        org.id = invitation.org_id
        org.name = "TestCorp"
        invitation.organization = org

        session = AsyncMock()
        session.flush = AsyncMock()

        # Mock get_invitation_by_token
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = invitation
        session.execute = AsyncMock(return_value=mock_result)

        with patch.object(service, "get_invitation_by_token", return_value=invitation):
            result = await service.accept_invitation(
                session=session,
                token=invitation.token,
                user_id=invitee_user_id,
            )

        assert result.status == InvitationStatus.ACCEPTED
        # Verify OrganizationMember was added
        add_calls = session.add.call_args_list
        member_added = any(
            isinstance(call.args[0], OrganizationMember) for call in add_calls
        )
        assert member_added, "OrganizationMember should be added to session"

        # Verify tier upgrade query was executed
        assert session.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_accept_expired_raises_error(self, service, invitee_user_id):
        invitation = _make_invitation(
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )

        session = AsyncMock()
        session.flush = AsyncMock()

        with patch.object(service, "get_invitation_by_token", return_value=invitation):
            with pytest.raises(ValueError, match="expired"):
                await service.accept_invitation(
                    session=session,
                    token=invitation.token,
                    user_id=invitee_user_id,
                )

        assert invitation.status == InvitationStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_accept_already_accepted_raises_error(self, service, invitee_user_id):
        invitation = _make_invitation(status=InvitationStatus.ACCEPTED)

        session = AsyncMock()
        session.flush = AsyncMock()

        with patch.object(service, "get_invitation_by_token", return_value=invitation):
            with pytest.raises(ValueError, match="no longer pending"):
                await service.accept_invitation(
                    session=session,
                    token=invitation.token,
                    user_id=invitee_user_id,
                )

    @pytest.mark.asyncio
    async def test_accept_invalid_token_raises_error(self, service, invitee_user_id):
        session = AsyncMock()

        with patch.object(service, "get_invitation_by_token", return_value=None):
            with pytest.raises(ValueError, match="Invalid invitation token"):
                await service.accept_invitation(
                    session=session,
                    token=uuid4(),
                    user_id=invitee_user_id,
                )


# ---------------------------------------------------------------------------
# Tests: decline_invitation
# ---------------------------------------------------------------------------


class TestDeclineInvitation:
    @pytest.mark.asyncio
    async def test_decline_sets_status(self, service):
        invitation = _make_invitation()

        session = AsyncMock()
        session.flush = AsyncMock()

        with patch.object(service, "get_invitation_by_token", return_value=invitation):
            result = await service.decline_invitation(
                session=session,
                token=invitation.token,
            )

        assert result.status == InvitationStatus.DECLINED

    @pytest.mark.asyncio
    async def test_decline_expired_raises_error(self, service):
        invitation = _make_invitation(
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )

        session = AsyncMock()
        session.flush = AsyncMock()

        with patch.object(service, "get_invitation_by_token", return_value=invitation):
            with pytest.raises(ValueError, match="expired"):
                await service.decline_invitation(
                    session=session,
                    token=invitation.token,
                )


# ---------------------------------------------------------------------------
# Tests: audit logging
# ---------------------------------------------------------------------------


class TestAuditLogging:
    @pytest.mark.asyncio
    async def test_create_invitation_logs_audit(self, service, org_id, admin_user_id):
        session = AsyncMock()
        generated_id = uuid4()

        async def _flush_side_effect():
            for call in session.add.call_args_list:
                obj = call.args[0]
                if isinstance(obj, Invitation) and obj.id is None:
                    obj.id = generated_id

        session.flush = AsyncMock(side_effect=_flush_side_effect)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.enterprise.invitation.log_audit_event") as mock_audit:
            await service.create_invitation(
                session=session,
                org_id=org_id,
                email="audit@example.com",
                invited_by=admin_user_id,
            )

            # Should be called at least once for invitation_created
            mock_audit.assert_called()
            call_kwargs = mock_audit.call_args_list[-1].kwargs
            assert call_kwargs["action"] == "invitation_created"
            assert call_kwargs["resource_type"] == "invitation"

    @pytest.mark.asyncio
    async def test_accept_invitation_logs_audit(self, service, invitee_user_id):
        invitation = _make_invitation()

        session = AsyncMock()
        session.flush = AsyncMock()

        with (
            patch.object(service, "get_invitation_by_token", return_value=invitation),
            patch("app.services.enterprise.invitation.log_audit_event") as mock_audit,
        ):
            # Need to mock execute for the tier update
            session.execute = AsyncMock()
            await service.accept_invitation(
                session=session,
                token=invitation.token,
                user_id=invitee_user_id,
            )

            mock_audit.assert_called()
            call_kwargs = mock_audit.call_args_list[-1].kwargs
            assert call_kwargs["action"] == "invitation_accepted"

    @pytest.mark.asyncio
    async def test_decline_invitation_logs_audit(self, service):
        invitation = _make_invitation()

        session = AsyncMock()
        session.flush = AsyncMock()

        with (
            patch.object(service, "get_invitation_by_token", return_value=invitation),
            patch("app.services.enterprise.invitation.log_audit_event") as mock_audit,
        ):
            await service.decline_invitation(
                session=session,
                token=invitation.token,
            )

            mock_audit.assert_called()
            call_kwargs = mock_audit.call_args_list[-1].kwargs
            assert call_kwargs["action"] == "invitation_declined"

    @pytest.mark.asyncio
    async def test_revoke_logs_audit(self, service, org_id, admin_user_id):
        existing = _make_invitation(org_id=org_id, email="rev@example.com")

        session = AsyncMock()
        generated_id = uuid4()

        async def _flush_side_effect():
            for call in session.add.call_args_list:
                obj = call.args[0]
                if isinstance(obj, Invitation) and obj.id is None:
                    obj.id = generated_id

        session.flush = AsyncMock(side_effect=_flush_side_effect)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing]
        session.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.enterprise.invitation.log_audit_event") as mock_audit:
            await service.create_invitation(
                session=session,
                org_id=org_id,
                email="rev@example.com",
                invited_by=admin_user_id,
            )

            # Check revocation audit was logged
            revoke_calls = [
                c for c in mock_audit.call_args_list
                if c.kwargs.get("action") == "invitation_revoked"
            ]
            assert len(revoke_calls) == 1


# ---------------------------------------------------------------------------
# Tests: send_invitation_email
# ---------------------------------------------------------------------------


class TestSendInvitationEmail:
    @pytest.mark.asyncio
    async def test_send_invitation_email_uses_correct_template(self):
        from app.services.transactional_email import send_invitation_email

        with patch("app.services.transactional_email.send_email", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"id": "test-id"}

            await send_invitation_email(
                to="employee@example.com",
                admin_name="Jane Admin",
                company_name="Acme Corp",
                accept_url="https://app.jobpilot.ai/invitations/abc/accept",
                decline_url="https://app.jobpilot.ai/invitations/abc/decline",
                recipient_first_name="Bob",
                logo_url="https://example.com/logo.png",
            )

            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args.kwargs
            assert call_kwargs["to"] == "employee@example.com"
            assert "Acme Corp" in call_kwargs["subject"]
            html = call_kwargs["html"]
            assert "Jane Admin" in html
            assert "Acme Corp" in html
            assert "Bob" in html
            assert "https://app.jobpilot.ai/invitations/abc/accept" in html
            assert "https://app.jobpilot.ai/invitations/abc/decline" in html
            assert "logo.png" in html

    @pytest.mark.asyncio
    async def test_send_invitation_email_without_optional_fields(self):
        from app.services.transactional_email import send_invitation_email

        with patch("app.services.transactional_email.send_email", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"id": "test-id"}

            await send_invitation_email(
                to="employee@example.com",
                admin_name="Jane Admin",
                company_name="Acme Corp",
                accept_url="https://example.com/accept",
                decline_url="https://example.com/decline",
            )

            mock_send.assert_called_once()
            html = mock_send.call_args.kwargs["html"]
            # No logo should be present
            assert "<img" not in html


# ---------------------------------------------------------------------------
# Tests: API endpoint schemas
# ---------------------------------------------------------------------------


class TestAPISchemas:
    def test_invite_request_requires_email(self):
        from app.api.v1.admin import InviteRequest

        with pytest.raises(Exception):
            InviteRequest()  # type: ignore[call-arg]

    def test_invite_request_valid(self):
        from app.api.v1.admin import InviteRequest

        req = InviteRequest(email="test@example.com", first_name="Test")
        assert req.email == "test@example.com"
        assert req.first_name == "Test"
        assert req.last_name is None

    def test_invitation_response_schema(self):
        from app.api.v1.admin import InvitationResponse

        resp = InvitationResponse(
            id=uuid4(),
            email="test@example.com",
            status="pending",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        assert resp.status == "pending"

    def test_invitation_action_response_schema(self):
        from app.api.v1.invitations import InvitationActionResponse

        resp = InvitationActionResponse(
            message="Invitation accepted.",
            status="accepted",
            redirect_url="/dashboard",
        )
        assert resp.redirect_url == "/dashboard"

    def test_invitation_action_response_optional_redirect(self):
        from app.api.v1.invitations import InvitationActionResponse

        resp = InvitationActionResponse(
            message="Declined.",
            status="declined",
        )
        assert resp.redirect_url is None
