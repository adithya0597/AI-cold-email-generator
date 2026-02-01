"""
Matches API endpoints.

Provides endpoints for listing and updating job matches:
  - GET /matches — paginated list filtered by status, with joined Job data
  - PATCH /matches/{match_id} — update match status (new -> saved/dismissed)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.clerk import get_current_user_id
from app.db.models import Job, Match, MatchStatus, User
from app.db.session import get_db
from app.services.job_scoring import parse_rationale

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/matches", tags=["matches"])


# ============================================================
# ensure_user_exists dependency
# ============================================================


async def ensure_user_exists(
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get User record for the authenticated Clerk user."""
    result = await db.execute(select(User).where(User.clerk_id == clerk_user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ============================================================
# Pydantic schemas
# ============================================================


class JobSummary(BaseModel):
    id: str
    title: str
    company: str
    location: Optional[str] = None
    remote: bool = False
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    url: Optional[str] = None
    description: Optional[str] = None


class RationaleResponse(BaseModel):
    summary: str = ""
    top_reasons: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    confidence: str = "Medium"


class MatchResponse(BaseModel):
    id: str
    score: int
    status: str
    rationale: RationaleResponse
    job: JobSummary
    created_at: str


class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int


class MatchListMeta(BaseModel):
    pagination: PaginationMeta


class MatchListResponse(BaseModel):
    data: List[MatchResponse]
    meta: MatchListMeta


class MatchStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("saved", "dismissed"):
            raise ValueError("Status must be 'saved' or 'dismissed'")
        return v


# ============================================================
# Helpers
# ============================================================


def _match_to_response(match: Match) -> MatchResponse:
    """Convert an ORM Match (with loaded job) to a MatchResponse."""
    job = match.job
    rationale_dict = parse_rationale(match.rationale)

    return MatchResponse(
        id=str(match.id),
        score=int(match.score) if match.score is not None else 0,
        status=match.status.value if hasattr(match.status, "value") else str(match.status),
        rationale=RationaleResponse(**rationale_dict),
        job=JobSummary(
            id=str(job.id),
            title=job.title,
            company=job.company,
            location=job.location,
            remote=bool(job.remote) if job.remote is not None else False,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            url=job.url,
            description=job.description,
        ),
        created_at=match.created_at.isoformat() if isinstance(match.created_at, datetime) else str(match.created_at),
    )


# ============================================================
# Endpoints
# ============================================================


@router.get("", response_model=MatchListResponse)
async def get_matches(
    user: User = Depends(ensure_user_exists),
    db: AsyncSession = Depends(get_db),
    status: str = Query(default="new", description="Filter by match status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page"),
):
    """Return paginated matches for the current user, filtered by status."""
    # Validate status
    try:
        match_status = MatchStatus(status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{status}'. Valid values: {[s.value for s in MatchStatus]}",
        )

    # Count total
    count_q = (
        select(func.count())
        .select_from(Match)
        .where(Match.user_id == user.id, Match.status == match_status)
    )
    total_result = await db.execute(count_q)
    total = total_result.scalar_one()

    # Fetch page
    offset = (page - 1) * per_page
    q = (
        select(Match)
        .options(selectinload(Match.job))
        .where(Match.user_id == user.id, Match.status == match_status)
        .order_by(Match.score.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(q)
    matches = result.scalars().all()

    total_pages = max(1, (total + per_page - 1) // per_page)

    return MatchListResponse(
        data=[_match_to_response(m) for m in matches],
        meta=MatchListMeta(
            pagination=PaginationMeta(
                page=page,
                per_page=per_page,
                total=total,
                total_pages=total_pages,
            )
        ),
    )


@router.get("/top-pick", response_model=MatchResponse, responses={204: {"description": "No new matches"}})
async def get_top_pick(
    user: User = Depends(ensure_user_exists),
    db: AsyncSession = Depends(get_db),
):
    """Return the single highest-scoring 'new' match for the current user."""
    q = (
        select(Match)
        .options(selectinload(Match.job))
        .where(Match.user_id == user.id, Match.status == MatchStatus.NEW)
        .order_by(Match.score.desc())
        .limit(1)
    )
    result = await db.execute(q)
    match = result.scalar_one_or_none()

    if not match:
        return Response(status_code=204)

    return _match_to_response(match)


@router.patch("/{match_id}")
async def update_match_status(
    match_id: str,
    body: MatchStatusUpdate,
    user: User = Depends(ensure_user_exists),
    db: AsyncSession = Depends(get_db),
):
    """Update a match's status. Only new -> saved/dismissed transitions are allowed."""
    result = await db.execute(
        select(Match)
        .options(selectinload(Match.job))
        .where(Match.id == match_id, Match.user_id == user.id)
    )
    match = result.scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    current_status = match.status.value if hasattr(match.status, "value") else str(match.status)
    if current_status != "new":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update match with status '{current_status}'. Only 'new' matches can be updated.",
        )

    match.status = MatchStatus(body.status)
    await db.flush()
    await db.refresh(match)

    return _match_to_response(match)
