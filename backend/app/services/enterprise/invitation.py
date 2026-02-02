"""Enterprise invitation service for employee onboarding.

Handles the full invitation lifecycle: create, accept, decline, expiry.
Each mutation logs an audit event via log_audit_event().
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import (
    Invitation,
    InvitationStatus,
    Organization,
    OrganizationMember,
    OrgRole,
    User,
    UserTier,
)
from app.services.enterprise.audit import log_audit_event

logger = logging.getLogger(__name__)

INVITATION_EXPIRY_DAYS = 7


class InvitationService:
    """Service for managing employee invitations."""

    async def create_invitation(
        self,
        session: AsyncSession,
        org_id: str,
        email: str,
        invited_by: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> Invitation:
        """Create a new invitation, revoking any existing pending ones for the same email+org.

        Args:
            session: Active async database session (caller manages transaction).
            org_id: Organization UUID string.
            email: Invitee email address.
            invited_by: Admin user UUID string who is sending the invite.
            first_name: Optional first name of invitee.
            last_name: Optional last name of invitee.

        Returns:
            The newly created Invitation record.
        """
        org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id
        inviter_uuid = UUID(invited_by) if isinstance(invited_by, str) else invited_by

        # Revoke existing pending invitations for same email + org
        await self._revoke_pending(session, org_uuid, email, inviter_uuid)

        invitation = Invitation(
            org_id=org_uuid,
            email=email.lower().strip(),
            invited_by=inviter_uuid,
            status=InvitationStatus.PENDING,
            first_name=first_name,
            last_name=last_name,
            expires_at=datetime.now(timezone.utc) + timedelta(days=INVITATION_EXPIRY_DAYS),
        )
        session.add(invitation)
        await session.flush()  # Populate id and token

        await log_audit_event(
            session=session,
            org_id=org_id,
            actor_id=invited_by,
            action="invitation_created",
            resource_type="invitation",
            resource_id=str(invitation.id),
            changes={"email": invitation.email, "first_name": first_name, "last_name": last_name},
        )

        logger.info("Invitation created: id=%s email=%s org=%s", invitation.id, email, org_id)
        return invitation

    async def accept_invitation(
        self,
        session: AsyncSession,
        token: UUID,
        user_id: str,
    ) -> Invitation:
        """Accept an invitation by token.

        Creates an OrganizationMember record and upgrades the user tier to ENTERPRISE.

        Args:
            session: Active async database session.
            token: Invitation token UUID.
            user_id: The accepting user's UUID string.

        Returns:
            The updated Invitation record.

        Raises:
            ValueError: If token is invalid, expired, or already used.
        """
        invitation = await self.get_invitation_by_token(session, token)
        if invitation is None:
            raise ValueError("Invalid invitation token")

        if self._check_expiry(invitation):
            await session.flush()
            await log_audit_event(
                session=session,
                org_id=str(invitation.org_id),
                actor_id=user_id,
                action="invitation_expired",
                resource_type="invitation",
                resource_id=str(invitation.id),
            )
            raise ValueError("Invitation has expired")

        if invitation.status != InvitationStatus.PENDING:
            raise ValueError(f"Invitation is no longer pending (status: {invitation.status.value})")

        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id

        # Create OrganizationMember record
        member = OrganizationMember(
            org_id=invitation.org_id,
            user_id=user_uuid,
            role=OrgRole.MEMBER,
        )
        session.add(member)

        # Upgrade user tier to ENTERPRISE
        await session.execute(
            update(User)
            .where(User.id == user_uuid)
            .values(tier=UserTier.ENTERPRISE, org_id=invitation.org_id)
        )

        # Update invitation status
        invitation.status = InvitationStatus.ACCEPTED

        await log_audit_event(
            session=session,
            org_id=str(invitation.org_id),
            actor_id=user_id,
            action="invitation_accepted",
            resource_type="invitation",
            resource_id=str(invitation.id),
            changes={"user_id": user_id},
        )

        logger.info("Invitation accepted: id=%s user=%s", invitation.id, user_id)
        return invitation

    async def decline_invitation(
        self,
        session: AsyncSession,
        token: UUID,
    ) -> Invitation:
        """Decline an invitation by token.

        Args:
            session: Active async database session.
            token: Invitation token UUID.

        Returns:
            The updated Invitation record.

        Raises:
            ValueError: If token is invalid, expired, or already used.
        """
        invitation = await self.get_invitation_by_token(session, token)
        if invitation is None:
            raise ValueError("Invalid invitation token")

        if self._check_expiry(invitation):
            await session.flush()
            raise ValueError("Invitation has expired")

        if invitation.status != InvitationStatus.PENDING:
            raise ValueError(f"Invitation is no longer pending (status: {invitation.status.value})")

        invitation.status = InvitationStatus.DECLINED

        await log_audit_event(
            session=session,
            org_id=str(invitation.org_id),
            actor_id=str(invitation.invited_by),
            action="invitation_declined",
            resource_type="invitation",
            resource_id=str(invitation.id),
            changes={"email": invitation.email},
        )

        logger.info("Invitation declined: id=%s email=%s", invitation.id, invitation.email)
        return invitation

    async def get_invitation_by_token(
        self,
        session: AsyncSession,
        token: UUID,
    ) -> Invitation | None:
        """Fetch an invitation by its token, eagerly loading the organization.

        Args:
            session: Active async database session.
            token: Invitation token UUID.

        Returns:
            Invitation with organization loaded, or None if not found.
        """
        result = await session.execute(
            select(Invitation)
            .options(joinedload(Invitation.organization))
            .where(Invitation.token == token)
        )
        return result.scalars().first()

    def _check_expiry(self, invitation: Invitation) -> bool:
        """Check if an invitation has expired and auto-update status.

        Args:
            invitation: The invitation to check.

        Returns:
            True if expired (status updated to EXPIRED), False otherwise.
        """
        now = datetime.now(timezone.utc)
        expires_at = invitation.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if now > expires_at and invitation.status == InvitationStatus.PENDING:
            invitation.status = InvitationStatus.EXPIRED
            return True
        return False

    async def _revoke_pending(
        self,
        session: AsyncSession,
        org_id: UUID,
        email: str,
        actor_id: UUID,
    ) -> int:
        """Revoke all pending invitations for the given email in the org.

        Returns the number of revoked invitations.
        """
        result = await session.execute(
            select(Invitation).where(
                Invitation.org_id == org_id,
                Invitation.email == email.lower().strip(),
                Invitation.status == InvitationStatus.PENDING,
            )
        )
        pending = result.scalars().all()

        for inv in pending:
            inv.status = InvitationStatus.REVOKED
            await log_audit_event(
                session=session,
                org_id=str(org_id),
                actor_id=str(actor_id),
                action="invitation_revoked",
                resource_type="invitation",
                resource_id=str(inv.id),
                changes={"email": inv.email, "reason": "replaced_by_new_invitation"},
            )

        if pending:
            logger.info("Revoked %d pending invitation(s) for %s in org %s", len(pending), email, org_id)

        return len(pending)
