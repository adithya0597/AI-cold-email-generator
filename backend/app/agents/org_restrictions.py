"""
Organization restriction checker for the agent framework.

Standalone utility that agents call before processing a job or company
to check if the user's organization has restrictions that block or
require approval for the target company/industry.

Follows the same pre-flight check pattern as ``check_brake()`` in
``app.agents.brake`` -- a quick check before agent execution.

Usage in agents::

    from app.agents.org_restrictions import check_org_restrictions

    result = await check_org_restrictions(user_id, company="Acme Corp", industry="Defense")
    if result.blocked:
        # Skip this job
        ...
    elif result.requires_approval:
        # Route to approval queue regardless of autonomy level
        ...
"""

from __future__ import annotations

import logging
from typing import Optional

from app.services.enterprise.autonomy_config import RestrictionResult

logger = logging.getLogger(__name__)


async def check_org_restrictions(
    user_id: str,
    company: Optional[str] = None,
    industry: Optional[str] = None,
) -> RestrictionResult:
    """Check organization restrictions for a user's company/industry target.

    If the user belongs to an organization, fetches the org's restrictions
    and evaluates the company/industry against them. If the user has no
    organization, returns a no-restriction result.

    Args:
        user_id: The user performing the agent action.
        company: Target company name or domain to check.
        industry: Target industry to check.

    Returns:
        RestrictionResult with blocked/requires_approval flags and reason.
    """
    from sqlalchemy import select

    from app.db.engine import AsyncSessionLocal
    from app.db.models import OrganizationMember
    from app.services.enterprise.autonomy_config import AutonomyConfigService

    async with AsyncSessionLocal() as session:
        # Look up user's org membership
        result = await session.execute(
            select(OrganizationMember.org_id).where(
                OrganizationMember.user_id == user_id
            )
        )
        org_id = result.scalar_one_or_none()

        if org_id is None:
            return RestrictionResult(
                blocked=False, requires_approval=False, reason=""
            )

        service = AutonomyConfigService()
        return await service.check_restrictions(
            session, str(org_id), company=company, industry=industry
        )
