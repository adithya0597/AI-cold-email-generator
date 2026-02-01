"""
Applications API endpoints for JobPilot.

Provides:
    - GET  /applications/queue          -- list pending approval items
    - GET  /applications/queue/count    -- count pending items (for badges)
    - POST /applications/queue/{id}/approve  -- approve and dispatch
    - POST /applications/queue/{id}/reject   -- reject application
    - POST /applications/queue/batch-approve -- approve multiple items
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth.clerk import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["applications"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ApprovalItem(BaseModel):
    """A single approval queue item for display."""

    id: str
    agent_type: str
    action_name: str
    job_id: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    submission_method: Optional[str] = None
    resume_document_id: Optional[str] = None
    cover_letter_document_id: Optional[str] = None
    rationale: Optional[str] = None
    confidence: Optional[float] = None
    created_at: str
    expires_at: str


class QueueListResponse(BaseModel):
    """Response for GET /queue."""

    items: List[ApprovalItem]
    total: int


class QueueCountResponse(BaseModel):
    """Response for GET /queue/count."""

    count: int


class RejectRequest(BaseModel):
    """Request body for POST /queue/{id}/reject."""

    reason: Optional[str] = None


class BatchApproveRequest(BaseModel):
    """Request body for POST /queue/batch-approve."""

    item_ids: List[str]


class BatchApproveResponse(BaseModel):
    """Response for POST /queue/batch-approve."""

    approved: int
    failed: int
    details: List[Dict[str, Any]] = []


class ApplicationItem(BaseModel):
    """A single application record."""

    id: str
    job_id: str
    job_title: Optional[str] = None
    company: Optional[str] = None
    status: str
    applied_at: str
    resume_version_id: Optional[str] = None


class ApplicationListResponse(BaseModel):
    """Response for GET /applications."""

    applications: List[ApplicationItem]
    total: int
    has_more: bool


class ApplicationDetailResponse(BaseModel):
    """Response for GET /applications/{id}."""

    id: str
    job_id: str
    job_title: Optional[str] = None
    company: Optional[str] = None
    job_url: Optional[str] = None
    status: str
    applied_at: str
    resume_version_id: Optional[str] = None
    cover_letter_document_id: Optional[str] = None


class UpdateStatusRequest(BaseModel):
    """Request body for PATCH /applications/{id}/status."""

    status: str


class UpdateStatusResponse(BaseModel):
    """Response for PATCH /applications/{id}/status."""

    id: str
    old_status: str
    new_status: str


# ---------------------------------------------------------------------------
# History endpoints (must be before /queue to avoid route conflicts)
# ---------------------------------------------------------------------------


@router.get("/history", response_model=ApplicationListResponse)
async def list_applications(
    user_id: str = Depends(get_current_user_id),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List user's applications sorted by date descending."""
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        # Build query with optional status filter.
        # SAFETY: base_where is built ONLY from hardcoded strings and
        # parameterised placeholders (:status). Never interpolate user input.
        base_where = (
            "WHERE a.user_id = (SELECT id FROM users WHERE clerk_id = :uid)"
        )
        params: dict = {"uid": user_id, "lim": limit, "off": offset}

        if status_filter:
            base_where += " AND a.status = :status"
            params["status"] = status_filter

        # Count total
        count_result = await session.execute(
            text(f"SELECT COUNT(*) FROM applications a {base_where}"),
            params,
        )
        total = count_result.scalar() or 0

        # Fetch with job join
        result = await session.execute(
            text(
                f"SELECT a.id, a.job_id, j.title AS job_title, j.company, "
                f"a.status, a.applied_at, a.resume_version_id "
                f"FROM applications a "
                f"LEFT JOIN jobs j ON a.job_id = j.id "
                f"{base_where} "
                f"ORDER BY a.applied_at DESC "
                f"LIMIT :lim OFFSET :off"
            ),
            params,
        )
        rows = result.mappings().all()

    items = [
        ApplicationItem(
            id=str(row["id"]),
            job_id=str(row["job_id"]),
            job_title=row["job_title"],
            company=row["company"],
            status=str(row["status"]).rsplit(".", 1)[-1].lower(),
            applied_at=row["applied_at"].isoformat() if row["applied_at"] else "",
            resume_version_id=str(row["resume_version_id"]) if row["resume_version_id"] else None,
        )
        for row in rows
    ]

    return ApplicationListResponse(
        applications=items,
        total=total,
        has_more=(offset + limit) < total,
    )


@router.get("/detail/{application_id}", response_model=ApplicationDetailResponse)
async def get_application_detail(
    application_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get single application with job and material details."""
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "SELECT a.id, a.job_id, j.title AS job_title, j.company, j.url AS job_url, "
                "a.status, a.applied_at, a.resume_version_id "
                "FROM applications a "
                "LEFT JOIN jobs j ON a.job_id = j.id "
                "WHERE a.id = :aid "
                "AND a.user_id = (SELECT id FROM users WHERE clerk_id = :uid)"
            ),
            {"aid": application_id, "uid": user_id},
        )
        row = result.mappings().first()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )

        # Also look up the cover letter for this job
        cl_result = await session.execute(
            text(
                "SELECT id FROM documents "
                "WHERE user_id = (SELECT id FROM users WHERE clerk_id = :uid) "
                "AND job_id = :jid "
                "AND type = 'cover_letter' "
                "AND deleted_at IS NULL "
                "ORDER BY version DESC LIMIT 1"
            ),
            {"uid": user_id, "jid": str(row["job_id"])},
        )
        cl_id = cl_result.scalar()

    return ApplicationDetailResponse(
        id=str(row["id"]),
        job_id=str(row["job_id"]),
        job_title=row["job_title"],
        company=row["company"],
        job_url=row["job_url"],
        status=str(row["status"]).rsplit(".", 1)[-1].lower(),
        applied_at=row["applied_at"].isoformat() if row["applied_at"] else "",
        resume_version_id=str(row["resume_version_id"]) if row["resume_version_id"] else None,
        cover_letter_document_id=str(cl_id) if cl_id else None,
    )


VALID_STATUSES = {"applied", "screening", "interview", "offer", "closed", "rejected"}


@router.patch("/{application_id}/status", response_model=UpdateStatusResponse)
async def update_application_status(
    application_id: str,
    body: UpdateStatusRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Update application status (manual drag & drop from Kanban)."""
    import uuid

    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    new_status = body.status.lower()
    if new_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{body.status}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
        )

    async with AsyncSessionLocal() as session:
        # Load current application
        result = await session.execute(
            text(
                "SELECT a.id, a.status "
                "FROM applications a "
                "WHERE a.id = :aid "
                "AND a.user_id = (SELECT id FROM users WHERE clerk_id = :uid) "
                "AND a.deleted_at IS NULL"
            ),
            {"aid": application_id, "uid": user_id},
        )
        row = result.mappings().first()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )

        old_status = str(row["status"]).rsplit(".", 1)[-1].lower()

        if old_status == new_status:
            return UpdateStatusResponse(
                id=application_id, old_status=old_status, new_status=new_status
            )

        # Update status
        await session.execute(
            text("UPDATE applications SET status = :status WHERE id = :aid"),
            {"status": new_status, "aid": application_id},
        )

        # Insert audit trail
        change_id = str(uuid.uuid4())
        await session.execute(
            text(
                "INSERT INTO application_status_changes "
                "(id, application_id, old_status, new_status, "
                "detection_method, confidence) "
                "VALUES (:id, :aid, :old, :new, 'manual', 1.0)"
            ),
            {
                "id": change_id,
                "aid": application_id,
                "old": old_status,
                "new": new_status,
            },
        )

        await session.commit()

    return UpdateStatusResponse(
        id=application_id, old_status=old_status, new_status=new_status
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/queue", response_model=QueueListResponse)
async def list_approval_queue(
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List pending approval items for the authenticated user."""
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        # Count total pending
        count_result = await session.execute(
            text(
                "SELECT COUNT(*) FROM approval_queue "
                "WHERE user_id = (SELECT id FROM users WHERE clerk_id = :uid) "
                "AND status = 'pending'"
            ),
            {"uid": user_id},
        )
        total = count_result.scalar() or 0

        # Fetch items with job info from payload
        result = await session.execute(
            text(
                "SELECT aq.id, aq.agent_type, aq.action_name, aq.payload, "
                "aq.rationale, aq.confidence, aq.created_at, aq.expires_at "
                "FROM approval_queue aq "
                "WHERE aq.user_id = (SELECT id FROM users WHERE clerk_id = :uid) "
                "AND aq.status = 'pending' "
                "ORDER BY aq.created_at DESC "
                "LIMIT :lim OFFSET :off"
            ),
            {"uid": user_id, "lim": limit, "off": offset},
        )
        rows = result.mappings().all()

    items = []
    for row in rows:
        payload = row["payload"] or {}
        items.append(
            ApprovalItem(
                id=str(row["id"]),
                agent_type=row["agent_type"],
                action_name=row["action_name"],
                job_id=payload.get("job_id"),
                job_title=payload.get("job_title"),
                company=payload.get("company"),
                submission_method=payload.get("submission_method"),
                resume_document_id=payload.get("resume_document_id"),
                cover_letter_document_id=payload.get("cover_letter_document_id"),
                rationale=row["rationale"],
                confidence=float(row["confidence"]) if row["confidence"] else None,
                created_at=row["created_at"].isoformat() if row["created_at"] else "",
                expires_at=row["expires_at"].isoformat() if row["expires_at"] else "",
            )
        )

    return QueueListResponse(items=items, total=total)


@router.get("/queue/count", response_model=QueueCountResponse)
async def get_queue_count(
    user_id: str = Depends(get_current_user_id),
):
    """Return count of pending approval items (for navigation badges)."""
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "SELECT COUNT(*) FROM approval_queue "
                "WHERE user_id = (SELECT id FROM users WHERE clerk_id = :uid) "
                "AND status = 'pending'"
            ),
            {"uid": user_id},
        )
        count = result.scalar() or 0

    return QueueCountResponse(count=count)


@router.post("/queue/{item_id}/approve")
async def approve_item(
    item_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Approve a pending application and dispatch the ApplyAgent."""
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        # Verify item exists and belongs to user
        result = await session.execute(
            text(
                "SELECT id, payload, status FROM approval_queue "
                "WHERE id = :iid "
                "AND user_id = (SELECT id FROM users WHERE clerk_id = :uid)"
            ),
            {"iid": item_id, "uid": user_id},
        )
        row = result.mappings().first()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval item not found",
            )

        if row["status"] != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Item is already '{row['status']}', cannot approve",
            )

        # Update status to approved
        await session.execute(
            text(
                "UPDATE approval_queue "
                "SET status = 'approved', decided_at = :now "
                "WHERE id = :iid"
            ),
            {"iid": item_id, "now": datetime.now(timezone.utc)},
        )
        await session.commit()

        payload = row["payload"] or {}

    # Dispatch the apply agent
    try:
        from app.agents.orchestrator import dispatch_task

        await dispatch_task("apply", user_id, payload)
    except Exception as exc:
        logger.warning("Failed to dispatch apply task after approval: %s", exc)

    return {"status": "approved", "item_id": item_id}


@router.post("/queue/{item_id}/reject")
async def reject_item(
    item_id: str,
    body: RejectRequest = None,
    user_id: str = Depends(get_current_user_id),
):
    """Reject a pending application."""
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    reason = body.reason if body else None

    async with AsyncSessionLocal() as session:
        # Verify item exists and belongs to user
        result = await session.execute(
            text(
                "SELECT id, status FROM approval_queue "
                "WHERE id = :iid "
                "AND user_id = (SELECT id FROM users WHERE clerk_id = :uid)"
            ),
            {"iid": item_id, "uid": user_id},
        )
        row = result.mappings().first()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval item not found",
            )

        if row["status"] != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Item is already '{row['status']}', cannot reject",
            )

        await session.execute(
            text(
                "UPDATE approval_queue "
                "SET status = 'rejected', decided_at = :now, "
                "user_decision_reason = :reason "
                "WHERE id = :iid"
            ),
            {
                "iid": item_id,
                "now": datetime.now(timezone.utc),
                "reason": reason,
            },
        )
        await session.commit()

    return {"status": "rejected", "item_id": item_id}


@router.post("/queue/batch-approve", response_model=BatchApproveResponse)
async def batch_approve(
    body: BatchApproveRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Approve multiple pending applications at once."""
    if not body.item_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="item_ids list cannot be empty",
        )

    approved = 0
    failed = 0
    details = []

    for item_id in body.item_ids:
        try:
            await approve_item(item_id=item_id, user_id=user_id)
            approved += 1
            details.append({"item_id": item_id, "status": "approved"})
        except HTTPException as exc:
            failed += 1
            details.append({
                "item_id": item_id,
                "status": "failed",
                "error": exc.detail,
            })

    return BatchApproveResponse(
        approved=approved,
        failed=failed,
        details=details,
    )
