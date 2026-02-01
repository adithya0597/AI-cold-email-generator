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
