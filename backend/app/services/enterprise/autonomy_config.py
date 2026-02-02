"""
Per-employee autonomy configuration service.

Manages organization-wide default autonomy levels, max autonomy ceilings,
per-employee overrides, and organization restrictions (blocked companies,
blocked industries, require-approval industries).

All configuration is stored in the Organization.settings JSONB field --
no new columns required.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel, field_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Organization, OrganizationMember, UserPreference

logger = logging.getLogger(__name__)

# Valid autonomy level values (lowercase, matching tier_enforcer TIER_ORDER)
VALID_LEVELS = ("l0", "l1", "l2", "l3")
LEVEL_ORDER = {"l0": 0, "l1": 1, "l2": 2, "l3": 3}

# Admin-configurable levels (L0 is always available, not settable as default/max)
ADMIN_LEVELS = ("l1", "l2", "l3")


# ---------------------------------------------------------------------------
# Pydantic models (Task 1.2, 1.3 + Task 5)
# ---------------------------------------------------------------------------


class OrgRestrictions(BaseModel):
    """Organization-level restrictions on job/company matching."""

    blocked_companies: List[str] = []
    blocked_industries: List[str] = []
    require_approval_industries: List[str] = []


class OrgAutonomySettings(BaseModel):
    """Organization autonomy configuration stored in settings JSONB."""

    default_autonomy: str = "l1"
    max_autonomy: str = "l3"
    restrictions: OrgRestrictions = OrgRestrictions()

    @field_validator("default_autonomy", "max_autonomy")
    @classmethod
    def validate_level(cls, v: str) -> str:
        v = v.lower()
        if v not in ADMIN_LEVELS:
            raise ValueError(f"Autonomy level must be one of {ADMIN_LEVELS}, got '{v}'")
        return v


class OrgAutonomyConfigResponse(BaseModel):
    """API response for autonomy config GET."""

    default_autonomy: str
    max_autonomy: str
    restrictions: OrgRestrictions


class EmployeeAutonomyRequest(BaseModel):
    """API request for setting per-employee autonomy override."""

    level: str

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        v = v.lower()
        if v not in VALID_LEVELS:
            raise ValueError(f"Autonomy level must be one of {VALID_LEVELS}, got '{v}'")
        return v


@dataclass
class RestrictionResult:
    """Result of checking organization restrictions against a company/industry."""

    blocked: bool
    requires_approval: bool
    reason: str


# ---------------------------------------------------------------------------
# Service class (Task 2)
# ---------------------------------------------------------------------------


class AutonomyConfigService:
    """Manages organization autonomy configuration and per-employee overrides."""

    # -- Read config --

    async def get_org_autonomy_config(
        self, session: AsyncSession, org_id: str
    ) -> OrgAutonomySettings:
        """Read autonomy config from Organization.settings JSONB.

        Returns defaults if no config has been set yet.
        """
        result = await session.execute(
            select(Organization.settings).where(Organization.id == org_id)
        )
        settings = result.scalar_one_or_none()
        if not settings:
            return OrgAutonomySettings()

        autonomy_data = settings.get("autonomy", {})
        return OrgAutonomySettings(**autonomy_data) if autonomy_data else OrgAutonomySettings()

    # -- Update config --

    async def update_org_autonomy_config(
        self, session: AsyncSession, org_id: str, config: OrgAutonomySettings
    ) -> OrgAutonomySettings:
        """Validate and persist autonomy config to Organization.settings JSONB.

        Raises ValueError if default_autonomy exceeds max_autonomy.
        """
        if LEVEL_ORDER[config.default_autonomy] > LEVEL_ORDER[config.max_autonomy]:
            raise ValueError(
                f"default_autonomy ({config.default_autonomy}) cannot exceed "
                f"max_autonomy ({config.max_autonomy})"
            )

        result = await session.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = result.scalar_one()

        current_settings = dict(org.settings or {})
        current_settings["autonomy"] = config.model_dump()
        org.settings = current_settings

        return config

    # -- Employee autonomy validation --

    async def validate_employee_autonomy(
        self, session: AsyncSession, org_id: str, requested_level: str
    ) -> bool:
        """Check if requested autonomy level does not exceed org max_autonomy."""
        config = await self.get_org_autonomy_config(session, org_id)
        return LEVEL_ORDER.get(requested_level.lower(), 0) <= LEVEL_ORDER[config.max_autonomy]

    # -- Per-employee override --

    async def set_employee_autonomy(
        self, session: AsyncSession, org_id: str, user_id: str, level: str
    ) -> str:
        """Set autonomy level for a specific employee, capped at max_autonomy.

        Stores the override in the user's UserPreference.autonomy_level.
        Returns the effective (possibly capped) level.
        """
        level = level.lower()
        config = await self.get_org_autonomy_config(session, org_id)

        # Cap at max_autonomy
        if LEVEL_ORDER.get(level, 0) > LEVEL_ORDER[config.max_autonomy]:
            level = config.max_autonomy

        result = await session.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        pref = result.scalar_one_or_none()

        if pref:
            pref.autonomy_level = level
        else:
            pref = UserPreference(user_id=user_id, autonomy_level=level)
            session.add(pref)

        return level

    # -- Effective autonomy resolution --

    async def get_effective_autonomy(
        self, session: AsyncSession, user_id: str
    ) -> str:
        """Resolve effective autonomy: user preference capped at org max.

        Resolution:
        1. Read user's autonomy_level from UserPreference
        2. If user belongs to an org, cap at org max_autonomy
        3. If no user preference, use org default_autonomy
        4. If no org, return user preference or "l0"
        """
        # Get user preference
        result = await session.execute(
            select(UserPreference.autonomy_level).where(
                UserPreference.user_id == user_id
            )
        )
        user_level = result.scalar_one_or_none()

        # Check org membership
        result = await session.execute(
            select(OrganizationMember.org_id).where(
                OrganizationMember.user_id == user_id
            )
        )
        org_id = result.scalar_one_or_none()

        if org_id is None:
            # No org -- return user pref or default
            return user_level or "l0"

        config = await self.get_org_autonomy_config(session, str(org_id))

        if user_level is None or user_level == "l0":
            # No preference set -- use org default
            return config.default_autonomy

        # Cap user preference at org max
        if LEVEL_ORDER.get(user_level, 0) > LEVEL_ORDER[config.max_autonomy]:
            return config.max_autonomy

        return user_level

    # -- Restrictions --

    async def update_restrictions(
        self, session: AsyncSession, org_id: str, restrictions: OrgRestrictions
    ) -> OrgRestrictions:
        """Persist restrictions to Organization.settings JSONB."""
        config = await self.get_org_autonomy_config(session, org_id)
        config.restrictions = restrictions
        await self.update_org_autonomy_config(session, org_id, config)
        return restrictions

    async def check_restrictions(
        self,
        session: AsyncSession,
        org_id: str,
        company: Optional[str] = None,
        industry: Optional[str] = None,
    ) -> RestrictionResult:
        """Check company/industry against org restrictions.

        Returns RestrictionResult indicating if blocked or requires approval.
        """
        config = await self.get_org_autonomy_config(session, org_id)
        restrictions = config.restrictions

        # Check blocked companies (case-insensitive)
        if company and restrictions.blocked_companies:
            company_lower = company.lower()
            for blocked in restrictions.blocked_companies:
                if blocked.lower() in company_lower or company_lower in blocked.lower():
                    return RestrictionResult(
                        blocked=True,
                        requires_approval=False,
                        reason=f"Company '{company}' is blocked by organization policy",
                    )

        # Check blocked industries (case-insensitive)
        if industry and restrictions.blocked_industries:
            industry_lower = industry.lower()
            for blocked in restrictions.blocked_industries:
                if blocked.lower() == industry_lower:
                    return RestrictionResult(
                        blocked=True,
                        requires_approval=False,
                        reason=f"Industry '{industry}' is blocked by organization policy",
                    )

        # Check require-approval industries (case-insensitive)
        if industry and restrictions.require_approval_industries:
            industry_lower = industry.lower()
            for req_approval in restrictions.require_approval_industries:
                if req_approval.lower() == industry_lower:
                    return RestrictionResult(
                        blocked=False,
                        requires_approval=True,
                        reason=f"Industry '{industry}' requires approval per organization policy",
                    )

        return RestrictionResult(blocked=False, requires_approval=False, reason="")
