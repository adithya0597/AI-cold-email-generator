"""Public invitation endpoints (token-based, no Clerk JWT required).

These endpoints are used by invitation recipients to accept or decline
invitations via the unique token in their email link.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.engine import AsyncSessionLocal
from app.services.enterprise.invitation import InvitationService

router = APIRouter(prefix="/invitations", tags=["invitations"])


# ---------- Response schemas ----------


class InvitationActionResponse(BaseModel):
    message: str
    status: str
    redirect_url: Optional[str] = None


# ---------- Endpoints ----------


@router.post("/{token}/accept", response_model=InvitationActionResponse)
async def accept_invitation(token: UUID):
    """Accept an invitation using its token.

    Validates the token, checks expiry, creates an OrganizationMember
    record, and upgrades the user tier to ENTERPRISE.

    For users without an account, returns a redirect URL to signup
    with org context pre-filled.
    """
    service = InvitationService()

    async with AsyncSessionLocal() as session:
        # First look up the invitation to check if user exists
        invitation = await service.get_invitation_by_token(session, token)
        if invitation is None:
            raise HTTPException(status_code=404, detail="Invalid invitation token")

        # Check if a user with this email already exists
        from sqlalchemy import select
        from app.db.models import User

        result = await session.execute(
            select(User).where(User.email == invitation.email)
        )
        user = result.scalars().first()

        if user is None:
            # No account -- redirect to signup with org context
            return InvitationActionResponse(
                message="Please create an account to join the organization",
                status="redirect_to_signup",
                redirect_url=f"/signup?invitation={token}&email={invitation.email}",
            )

        async with session.begin():
            try:
                updated = await service.accept_invitation(
                    session=session,
                    token=token,
                    user_id=str(user.id),
                )
            except ValueError as exc:
                detail = str(exc)
                if "expired" in detail.lower():
                    raise HTTPException(status_code=410, detail="Invitation has expired")
                raise HTTPException(status_code=400, detail=detail)

    return InvitationActionResponse(
        message="Invitation accepted. You are now a member of the organization.",
        status="accepted",
        redirect_url="/dashboard",
    )


@router.post("/{token}/decline", response_model=InvitationActionResponse)
async def decline_invitation(token: UUID):
    """Decline an invitation using its token.

    Updates the invitation status to declined. No authentication required.
    """
    service = InvitationService()

    async with AsyncSessionLocal() as session:
        async with session.begin():
            try:
                updated = await service.decline_invitation(
                    session=session,
                    token=token,
                )
            except ValueError as exc:
                detail = str(exc)
                if "expired" in detail.lower():
                    raise HTTPException(status_code=410, detail="Invitation has expired")
                if "invalid" in detail.lower():
                    raise HTTPException(status_code=404, detail="Invalid invitation token")
                raise HTTPException(status_code=400, detail=detail)

    return InvitationActionResponse(
        message="Invitation declined.",
        status="declined",
    )
