"""
Enterprise admin API endpoints.

Separated from admin.py to keep enterprise-specific routes organized.
All endpoints require admin RBAC via require_admin dependency.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth.admin import AdminContext, require_admin

router = APIRouter(prefix="/admin", tags=["admin-enterprise"])


# ---------- Request/Response schemas ----------


class EmployeeSummarySchema(BaseModel):
    user_id: str
    name: str
    email: str
    engagement_status: str


class AtRiskListResponse(BaseModel):
    employees: List[EmployeeSummarySchema]
    total: int


class NudgeResponse(BaseModel):
    status: str
    message: str


# ---------- Endpoints ----------


@router.get("/employees/at-risk", response_model=AtRiskListResponse)
async def get_at_risk_employees(
    admin_ctx: AdminContext = Depends(require_admin),
    status: Optional[str] = Query(
        None,
        description="Filter by engagement status: at_risk, active, placed, opted_out",
    ),
):
    """Return privacy-safe list of employees with engagement status.

    Each record contains ONLY user_id, name, email, engagement_status.
    NEVER includes application titles, pipeline details, job matches,
    or any individual activity data.

    Accepts an optional ``status`` query parameter to filter results.
    """
    from app.db.engine import AsyncSessionLocal
    from app.services.enterprise.at_risk import AtRiskDetectionService

    # Validate status filter
    valid_statuses = {"at_risk", "active", "placed", "opted_out"}
    if status and status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status filter. Must be one of: {', '.join(sorted(valid_statuses))}",
        )

    service = AtRiskDetectionService()

    async with AsyncSessionLocal() as session:
        summaries = await service.get_employee_summaries(
            session=session,
            org_id=admin_ctx.org_id,
            status_filter=status,
        )

    employees = [EmployeeSummarySchema(**s) for s in summaries]
    return AtRiskListResponse(employees=employees, total=len(employees))


@router.post("/employees/{user_id}/nudge", response_model=NudgeResponse)
async def send_nudge(
    user_id: str,
    admin_ctx: AdminContext = Depends(require_admin),
):
    """Send a generic re-engagement nudge email to an employee.

    The email content is NOT personalized with any pipeline or application
    data. Creates an AuditLog entry recording the nudge action.
    """
    from sqlalchemy import select

    from app.db.engine import AsyncSessionLocal
    from app.db.models import OrganizationMember, User
    from app.services.enterprise.audit import log_audit_event
    from app.services.transactional_email import send_nudge_email

    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Verify user is a member of the admin's org
            result = await session.execute(
                select(User.email, User.display_name)
                .join(OrganizationMember, OrganizationMember.user_id == User.id)
                .where(
                    OrganizationMember.org_id == admin_ctx.org_id,
                    User.id == user_id,
                )
            )
            row = result.first()

            if row is None:
                raise HTTPException(
                    status_code=404,
                    detail="Employee not found in your organization.",
                )

            email, display_name = row

            # Send generic nudge email
            await send_nudge_email(
                to=email,
                user_name=display_name or "there",
            )

            # Audit trail
            await log_audit_event(
                session=session,
                org_id=admin_ctx.org_id,
                actor_id=admin_ctx.user_id,
                action="nudge_sent",
                resource_type="employee",
                resource_id=user_id,
                changes={"target_user_id": user_id},
            )

    return NudgeResponse(
        status="sent",
        message="Re-engagement nudge sent successfully.",
    )
