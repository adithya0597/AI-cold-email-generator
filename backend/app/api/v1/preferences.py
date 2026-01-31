"""
Preferences CRUD API endpoints.

Provides full and per-section preference management with upsert semantics,
plus a structured deal-breakers endpoint for agent consumption.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk import get_current_user_id
from app.db.models import User, UserPreference
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/preferences", tags=["preferences"])


# ============================================================
# ensure_user_exists dependency
# ============================================================
# Plan 03 (onboarding) will also use this. When Plan 03 is built,
# this can be extracted to a shared module. For now, defined here.


async def ensure_user_exists(
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get or create User record for the authenticated Clerk user."""
    result = await db.execute(select(User).where(User.clerk_id == clerk_user_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            clerk_id=clerk_user_id,
            email=f"pending-{clerk_user_id}@setup.jobpilot.com",
            onboarding_status="not_started",
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
    return user


# ============================================================
# Pydantic schemas
# ============================================================


class JobTypePreferences(BaseModel):
    categories: List[str] = Field(default_factory=list)
    target_titles: List[str] = Field(default_factory=list)
    seniority_levels: List[str] = Field(default_factory=list)


class LocationPreferences(BaseModel):
    work_arrangement: Optional[str] = None
    target_locations: List[str] = Field(default_factory=list)
    excluded_locations: List[str] = Field(default_factory=list)
    willing_to_relocate: bool = False


class SalaryPreferences(BaseModel):
    minimum: Optional[int] = None
    target: Optional[int] = None
    flexibility: Optional[str] = None
    comp_preference: Optional[str] = None


class DealBreakers(BaseModel):
    min_company_size: Optional[int] = None
    excluded_companies: List[str] = Field(default_factory=list)
    excluded_industries: List[str] = Field(default_factory=list)
    must_have_benefits: List[str] = Field(default_factory=list)
    max_travel_percent: Optional[int] = None
    no_oncall: bool = False


class H1BPreferences(BaseModel):
    requires_h1b: bool = False
    requires_greencard: bool = False
    current_visa_type: Optional[str] = None
    visa_expiration: Optional[str] = None


class AutonomyPreference(BaseModel):
    level: str = "l0"


class FullPreferences(BaseModel):
    job_type: JobTypePreferences = Field(default_factory=JobTypePreferences)
    location: LocationPreferences = Field(default_factory=LocationPreferences)
    salary: SalaryPreferences = Field(default_factory=SalaryPreferences)
    deal_breakers: DealBreakers = Field(default_factory=DealBreakers)
    h1b: H1BPreferences = Field(default_factory=H1BPreferences)
    autonomy: AutonomyPreference = Field(default_factory=AutonomyPreference)
    extra_preferences: Dict[str, Any] = Field(default_factory=dict)


class PreferenceSummaryResponse(BaseModel):
    job_type: JobTypePreferences
    location: LocationPreferences
    salary: SalaryPreferences
    deal_breakers: DealBreakers
    h1b: H1BPreferences
    autonomy: AutonomyPreference
    extra_preferences: Dict[str, Any]
    is_complete: bool
    missing_sections: List[str]


class DealBreakerResponse(BaseModel):
    must_haves: Dict[str, Any]
    never_haves: Dict[str, Any]


# ============================================================
# Helpers
# ============================================================


def _pref_to_full(pref: UserPreference) -> FullPreferences:
    """Convert a UserPreference ORM instance to the FullPreferences schema."""
    return FullPreferences(
        job_type=JobTypePreferences(
            categories=pref.job_categories or [],
            target_titles=pref.target_titles or [],
            seniority_levels=pref.seniority_levels or [],
        ),
        location=LocationPreferences(
            work_arrangement=pref.work_arrangement,
            target_locations=pref.target_locations or [],
            excluded_locations=pref.excluded_locations or [],
            willing_to_relocate=pref.willing_to_relocate or False,
        ),
        salary=SalaryPreferences(
            minimum=pref.salary_minimum,
            target=pref.salary_target,
            flexibility=pref.salary_flexibility,
            comp_preference=pref.comp_preference,
        ),
        deal_breakers=DealBreakers(
            min_company_size=pref.min_company_size,
            excluded_companies=pref.excluded_companies or [],
            excluded_industries=pref.excluded_industries or [],
            must_have_benefits=pref.must_have_benefits or [],
            max_travel_percent=pref.max_travel_percent,
            no_oncall=pref.no_oncall or False,
        ),
        h1b=H1BPreferences(
            requires_h1b=pref.requires_h1b_sponsorship or False,
            requires_greencard=pref.requires_greencard_sponsorship or False,
            current_visa_type=pref.current_visa_type,
            visa_expiration=(
                pref.visa_expiration.isoformat() if pref.visa_expiration else None
            ),
        ),
        autonomy=AutonomyPreference(level=pref.autonomy_level or "l0"),
        extra_preferences=pref.extra_preferences or {},
    )


def _apply_full_to_pref(pref: UserPreference, data: FullPreferences) -> None:
    """Apply FullPreferences data to a UserPreference ORM instance."""
    # Job type
    pref.job_categories = data.job_type.categories
    pref.target_titles = data.job_type.target_titles
    pref.seniority_levels = data.job_type.seniority_levels

    # Location
    pref.work_arrangement = data.location.work_arrangement
    pref.target_locations = data.location.target_locations
    pref.excluded_locations = data.location.excluded_locations
    pref.willing_to_relocate = data.location.willing_to_relocate

    # Salary
    pref.salary_minimum = data.salary.minimum
    pref.salary_target = data.salary.target
    pref.salary_flexibility = data.salary.flexibility
    pref.comp_preference = data.salary.comp_preference

    # Deal breakers
    pref.min_company_size = data.deal_breakers.min_company_size
    pref.excluded_companies = data.deal_breakers.excluded_companies
    pref.excluded_industries = data.deal_breakers.excluded_industries
    pref.must_have_benefits = data.deal_breakers.must_have_benefits
    pref.max_travel_percent = data.deal_breakers.max_travel_percent
    pref.no_oncall = data.deal_breakers.no_oncall

    # H1B
    pref.requires_h1b_sponsorship = data.h1b.requires_h1b
    pref.requires_greencard_sponsorship = data.h1b.requires_greencard
    pref.current_visa_type = data.h1b.current_visa_type
    # visa_expiration stored as string in schema, convert if needed
    pref.visa_expiration = None  # Simplified: parse ISO date if provided
    if data.h1b.visa_expiration:
        from datetime import datetime

        try:
            pref.visa_expiration = datetime.fromisoformat(
                data.h1b.visa_expiration
            )
        except (ValueError, TypeError):
            pass

    # Autonomy
    pref.autonomy_level = data.autonomy.level

    # Extra
    pref.extra_preferences = data.extra_preferences


def _get_missing_sections(pref: UserPreference) -> List[str]:
    """Return list of section names that have no meaningful data."""
    missing = []
    if not (pref.job_categories or pref.target_titles or pref.seniority_levels):
        missing.append("job_type")
    if not (pref.work_arrangement or pref.target_locations):
        missing.append("location")
    if pref.salary_minimum is None and pref.salary_target is None:
        missing.append("salary")
    if not (
        pref.min_company_size
        or pref.excluded_companies
        or pref.excluded_industries
        or pref.must_have_benefits
        or pref.max_travel_percent is not None
        or pref.no_oncall
    ):
        missing.append("deal_breakers")
    if not (pref.requires_h1b_sponsorship or pref.requires_greencard_sponsorship):
        missing.append("h1b")
    # autonomy always has a default, so only missing if still default
    if pref.autonomy_level == "l0":
        missing.append("autonomy")
    return missing


async def _get_or_create_pref(
    user: User, db: AsyncSession
) -> UserPreference:
    """Get or create the UserPreference record for a user."""
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user.id)
    )
    pref = result.scalar_one_or_none()
    if not pref:
        pref = UserPreference(user_id=user.id)
        db.add(pref)
        await db.flush()
        await db.refresh(pref)
    return pref


# ============================================================
# Endpoints
# ============================================================


@router.get("", response_model=FullPreferences)
async def get_preferences(
    user: User = Depends(ensure_user_exists),
    db: AsyncSession = Depends(get_db),
):
    """Return full preferences for the current user (defaults if none exist)."""
    pref = await _get_or_create_pref(user, db)
    return _pref_to_full(pref)


@router.put("", response_model=FullPreferences)
async def update_preferences(
    data: FullPreferences,
    user: User = Depends(ensure_user_exists),
    db: AsyncSession = Depends(get_db),
):
    """
    Full upsert of all preference sections.

    If the user's onboarding_status is 'preferences_pending', transitions
    it to 'complete'.
    """
    pref = await _get_or_create_pref(user, db)
    _apply_full_to_pref(pref, data)
    await db.flush()

    # Transition onboarding status if appropriate
    if user.onboarding_status == "preferences_pending":
        user.onboarding_status = "complete"
        from datetime import datetime, timezone

        user.onboarding_completed_at = datetime.now(timezone.utc)
        await db.flush()

    await db.refresh(pref)
    return _pref_to_full(pref)


# Section name -> (schema class, field mapping)
SECTION_MAP: Dict[str, type[BaseModel]] = {
    "job_type": JobTypePreferences,
    "location": LocationPreferences,
    "salary": SalaryPreferences,
    "deal_breakers": DealBreakers,
    "h1b": H1BPreferences,
    "autonomy": AutonomyPreference,
}


@router.patch("/{section}")
async def patch_preference_section(
    section: str = Path(..., description="Section name: job_type, location, salary, deal_breakers, h1b, autonomy"),
    user: User = Depends(ensure_user_exists),
    db: AsyncSession = Depends(get_db),
    body: Dict[str, Any] = {},
):
    """
    Partial update for a single preference section.

    Enables per-step wizard saves. The request body should match the
    corresponding section schema.
    """
    if section not in SECTION_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown section '{section}'. Valid sections: {list(SECTION_MAP.keys())}",
        )

    schema_cls = SECTION_MAP[section]
    try:
        section_data = schema_cls(**body)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid data for section '{section}': {exc}",
        )

    pref = await _get_or_create_pref(user, db)

    # Apply section-specific fields
    if section == "job_type":
        pref.job_categories = section_data.categories
        pref.target_titles = section_data.target_titles
        pref.seniority_levels = section_data.seniority_levels
    elif section == "location":
        pref.work_arrangement = section_data.work_arrangement
        pref.target_locations = section_data.target_locations
        pref.excluded_locations = section_data.excluded_locations
        pref.willing_to_relocate = section_data.willing_to_relocate
    elif section == "salary":
        pref.salary_minimum = section_data.minimum
        pref.salary_target = section_data.target
        pref.salary_flexibility = section_data.flexibility
        pref.comp_preference = section_data.comp_preference
    elif section == "deal_breakers":
        pref.min_company_size = section_data.min_company_size
        pref.excluded_companies = section_data.excluded_companies
        pref.excluded_industries = section_data.excluded_industries
        pref.must_have_benefits = section_data.must_have_benefits
        pref.max_travel_percent = section_data.max_travel_percent
        pref.no_oncall = section_data.no_oncall
    elif section == "h1b":
        pref.requires_h1b_sponsorship = section_data.requires_h1b
        pref.requires_greencard_sponsorship = section_data.requires_greencard
        pref.current_visa_type = section_data.current_visa_type
        if section_data.visa_expiration:
            from datetime import datetime

            try:
                pref.visa_expiration = datetime.fromisoformat(
                    section_data.visa_expiration
                )
            except (ValueError, TypeError):
                pass
        else:
            pref.visa_expiration = None
    elif section == "autonomy":
        pref.autonomy_level = section_data.level

    await db.flush()
    await db.refresh(pref)

    return {"status": "updated", "section": section}


@router.get("/summary", response_model=PreferenceSummaryResponse)
async def get_preference_summary(
    user: User = Depends(ensure_user_exists),
    db: AsyncSession = Depends(get_db),
):
    """Return preferences with completion status and missing sections."""
    pref = await _get_or_create_pref(user, db)
    full = _pref_to_full(pref)
    missing = _get_missing_sections(pref)

    return PreferenceSummaryResponse(
        **full.model_dump(),
        is_complete=len(missing) == 0,
        missing_sections=missing,
    )


@router.get("/deal-breakers", response_model=DealBreakerResponse)
async def get_deal_breakers(
    user: User = Depends(ensure_user_exists),
    db: AsyncSession = Depends(get_db),
):
    """
    Return ONLY deal-breakers in structured format for agent consumption.

    Returns must_haves (things the user requires) and never_haves (things
    the user wants to avoid) in a format agents can query programmatically.
    """
    pref = await _get_or_create_pref(user, db)

    must_haves: Dict[str, Any] = {}
    never_haves: Dict[str, Any] = {}

    # Must-haves
    if pref.min_company_size:
        must_haves["min_company_size"] = pref.min_company_size
    if pref.must_have_benefits:
        must_haves["benefits"] = pref.must_have_benefits
    if pref.requires_h1b_sponsorship:
        must_haves["h1b_sponsorship"] = True
    if pref.requires_greencard_sponsorship:
        must_haves["greencard_sponsorship"] = True
    if pref.salary_minimum:
        must_haves["salary_minimum"] = pref.salary_minimum

    # Never-haves
    if pref.excluded_companies:
        never_haves["companies"] = pref.excluded_companies
    if pref.excluded_industries:
        never_haves["industries"] = pref.excluded_industries
    if pref.max_travel_percent is not None:
        never_haves["max_travel_percent"] = pref.max_travel_percent
    if pref.no_oncall:
        never_haves["on_call"] = True
    if pref.excluded_locations:
        never_haves["locations"] = pref.excluded_locations

    return DealBreakerResponse(must_haves=must_haves, never_haves=never_haves)
