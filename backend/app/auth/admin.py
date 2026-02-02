"""
Enterprise admin authentication dependency.

Provides require_admin FastAPI dependency that verifies the authenticated
user has an admin role in an organization. Returns AdminContext with
user and org information.

Usage as a FastAPI dependency::

    from app.auth.admin import require_admin, AdminContext

    @router.get("/admin-only")
    async def admin_endpoint(admin_ctx: AdminContext = Depends(require_admin)):
        ...
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException
from sqlalchemy import select

from app.auth.clerk import get_current_user_id
from app.db.engine import AsyncSessionLocal
from app.db.models import Organization, OrganizationMember, OrgRole


@dataclass
class AdminContext:
    """Context object returned by require_admin dependency."""

    user_id: str
    org_id: str
    org_name: str


async def require_admin(
    user_id: str = Depends(get_current_user_id),
) -> AdminContext:
    """FastAPI dependency that requires the user to be an org admin.

    Queries OrganizationMember for the user with admin role.
    Returns AdminContext on success, raises 403 on failure.

    The dependency does NOT set RLS context -- route handlers set
    context as needed using set_rls_context / set_org_rls_context.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(OrganizationMember, Organization)
            .join(Organization, OrganizationMember.org_id == Organization.id)
            .where(
                OrganizationMember.user_id == user_id,
                OrganizationMember.role == OrgRole.ADMIN,
            )
        )
        row = result.first()

        if row is None:
            raise HTTPException(
                status_code=403,
                detail="Admin access required. You must be an organization admin to access this resource.",
            )

        member, org = row
        return AdminContext(
            user_id=str(member.user_id),
            org_id=str(member.org_id),
            org_name=org.name,
        )
