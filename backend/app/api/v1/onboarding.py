"""
Onboarding API endpoints for resume upload, profile extraction, and confirmation.

Handles the onboarding flow:
1. Upload resume -> extract profile via LLM (or LinkedIn URL extraction)
2. User reviews and confirms extracted profile
3. Profile is saved to DB, onboarding status updated

All endpoints require Clerk authentication.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk import get_current_user_id
from app.db.models import Profile, User
from app.db.session import get_db
from app.api.v1.preferences import ensure_user_exists
from app.services.analytics_service import track_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# ============================================================
# Pydantic request/response schemas
# ============================================================


class ProfileConfirmRequest(BaseModel):
    """Request body for confirming/saving an extracted profile."""

    name: str
    headline: Optional[str] = None
    phone: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    extraction_source: str = "resume"  # 'resume' | 'linkedin' | 'manual'


class OnboardingStatusResponse(BaseModel):
    """Response for the onboarding status endpoint."""

    onboarding_status: str
    display_name: Optional[str] = None


class LinkedInExtractRequest(BaseModel):
    """Request body for LinkedIn profile extraction."""

    url: str


# ============================================================
# Constants
# ============================================================

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


# ============================================================
# Endpoints
# ============================================================


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    user: User = Depends(ensure_user_exists),
):
    """Return the current onboarding status for the authenticated user."""
    return OnboardingStatusResponse(
        onboarding_status=user.onboarding_status or "not_started",
        display_name=user.display_name,
    )


@router.post("/resume/upload")
async def upload_resume(
    file: UploadFile,
    user: User = Depends(ensure_user_exists),
    db: AsyncSession = Depends(get_db),
    clerk_user_id: str = Depends(get_current_user_id),
):
    """
    Upload a resume file (PDF/DOCX), extract profile via LLM.

    Stores the file in Supabase Storage, extracts text, and uses
    OpenAI structured outputs to parse profile data. Returns the
    extracted profile for user review (NOT saved to DB yet).

    Updates onboarding_status to 'profile_pending'.
    """
    # Validate file type
    filename = file.filename or "unknown"
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Please upload a PDF or DOCX file.",
        )

    # Read and validate file size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
        )

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Store in Supabase Storage
    try:
        from app.services.storage_service import upload_file

        storage_path = await upload_file(
            user_id=str(user.id),
            file_bytes=file_bytes,
            filename=filename,
            content_type=file.content_type,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception:
        logger.error("Failed to upload resume to storage for user %s", user.id, exc_info=True)
        storage_path = f"{user.id}/{filename}"  # Continue even if storage fails

    # Extract profile via LLM
    try:
        from app.services.resume_parser import extract_profile_from_resume

        extracted = await extract_profile_from_resume(file_bytes, filename)
    except ValueError as exc:
        # Known errors (image-based PDF, unsupported type, etc.)
        track_event(
            str(user.id),
            "profile_extraction_failed",
            {"source": "resume", "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Profile extraction failed for user %s: %s", user.id, exc, exc_info=True)
        track_event(
            str(user.id),
            "profile_extraction_failed",
            {"source": "resume", "error": "internal_error"},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract profile from resume. Please try again.",
        )

    # Update onboarding status
    user.onboarding_status = "profile_pending"
    await db.flush()

    # Track success
    track_event(
        str(user.id),
        "profile_extraction_completed",
        {
            "source": "resume",
            "fields_extracted": len(
                [v for v in extracted.model_dump().values() if v]
            ),
            "storage_path": storage_path,
        },
    )

    return {
        "profile": extracted.model_dump(),
        "storage_path": storage_path,
    }


@router.post("/linkedin/extract")
async def extract_linkedin_profile(
    body: LinkedInExtractRequest,
    user: User = Depends(ensure_user_exists),
    clerk_user_id: str = Depends(get_current_user_id),
):
    """
    Extract profile data from a LinkedIn profile URL.

    This is a secondary path -- LinkedIn aggressively blocks scraping.
    Returns 422 with a helpful fallback message if extraction fails.
    """
    from app.services.linkedin_extractor import extract_from_linkedin_url

    track_event(
        str(user.id),
        "profile_extraction_method_chosen",
        {"method": "linkedin"},
    )

    extracted = await extract_from_linkedin_url(body.url)

    if extracted is None:
        track_event(
            str(user.id),
            "profile_extraction_failed",
            {"source": "linkedin"},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract profile from LinkedIn. Try uploading your resume instead.",
        )

    track_event(
        str(user.id),
        "profile_extraction_completed",
        {"source": "linkedin"},
    )

    return {"profile": extracted.model_dump()}


@router.put("/profile/confirm")
async def confirm_profile(
    body: ProfileConfirmRequest,
    user: User = Depends(ensure_user_exists),
    db: AsyncSession = Depends(get_db),
    clerk_user_id: str = Depends(get_current_user_id),
):
    """
    Confirm and save the extracted (and possibly edited) profile.

    Upserts the Profile record with skills, experience, education,
    headline, phone, and extraction_source. Updates User.display_name
    and transitions onboarding_status to 'profile_complete'.
    """
    # Upsert profile
    result = await db.execute(
        select(Profile).where(Profile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        profile = Profile(user_id=user.id)
        db.add(profile)

    profile.skills = body.skills
    profile.experience = [dict(e) for e in body.experience]
    profile.education = [dict(e) for e in body.education]
    profile.headline = body.headline
    profile.phone = body.phone
    profile.extraction_source = body.extraction_source

    # Update user
    user.display_name = body.name
    user.onboarding_status = "profile_complete"

    await db.flush()
    await db.refresh(profile)

    track_event(
        str(user.id),
        "profile_confirmed",
        {
            "extraction_source": body.extraction_source,
            "skills_count": len(body.skills),
            "experience_count": len(body.experience),
            "education_count": len(body.education),
        },
    )

    return {
        "profile": {
            "name": body.name,
            "headline": profile.headline,
            "phone": profile.phone,
            "skills": profile.skills or [],
            "experience": profile.experience or [],
            "education": profile.education or [],
            "extraction_source": profile.extraction_source,
        },
        "onboarding_status": user.onboarding_status,
    }


@router.get("/profile")
async def get_profile(
    user: User = Depends(ensure_user_exists),
    db: AsyncSession = Depends(get_db),
):
    """Return the current profile data for the user (for profile review editing)."""
    result = await db.execute(
        select(Profile).where(Profile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        return {
            "profile": None,
            "display_name": user.display_name,
            "onboarding_status": user.onboarding_status,
        }

    return {
        "profile": {
            "name": user.display_name,
            "headline": profile.headline,
            "phone": profile.phone,
            "skills": profile.skills or [],
            "experience": profile.experience or [],
            "education": profile.education or [],
            "extraction_source": profile.extraction_source,
            "resume_storage_path": profile.resume_storage_path,
        },
        "display_name": user.display_name,
        "onboarding_status": user.onboarding_status,
    }
