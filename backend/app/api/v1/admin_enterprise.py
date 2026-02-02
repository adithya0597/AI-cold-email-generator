"""
Enterprise admin API endpoints.

Separated from admin.py to keep enterprise-specific routes organized.
All endpoints require admin RBAC via require_admin dependency.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

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


class ROIBenchmarkDetail(BaseModel):
    benchmark_value: float
    comparison: str


class ROIBenchmarks(BaseModel):
    time_to_placement_days: ROIBenchmarkDetail
    cost_per_placement: ROIBenchmarkDetail
    engagement_rate: ROIBenchmarkDetail
    satisfaction_score: ROIBenchmarkDetail


class ROIPeriod(BaseModel):
    start_date: str
    end_date: str


class ROIMetricsResponse(BaseModel):
    cost_per_placement: Optional[float] = None
    time_to_placement_days: Optional[float] = None
    engagement_rate: float
    satisfaction_score: Optional[float] = None
    period: ROIPeriod
    benchmarks: ROIBenchmarks


class ROIScheduleRequest(BaseModel):
    enabled: bool = False
    recipients: List[str] = []


class ROIScheduleResponse(BaseModel):
    enabled: bool
    recipients: List[str]


# ---------- PII Detection schemas ----------


class PIIPatternSchema(BaseModel):
    pattern: str = Field(..., description="Regex pattern string")
    category: str = Field(..., description="Pattern category (e.g. internal_email)")
    description: str = Field("", description="Human-readable description")
    enabled: bool = Field(True, description="Whether this pattern is active")


class PIIConfigRequest(BaseModel):
    patterns: List[PIIPatternSchema] = Field(
        default_factory=list, description="Custom PII patterns"
    )
    whitelist: List[str] = Field(
        default_factory=list, description="Terms to exclude from detection"
    )


class PIIConfigResponse(BaseModel):
    patterns: List[Dict[str, Any]]
    whitelist: List[str]
    default_patterns: List[Dict[str, Any]]


class PIIAlertSchema(BaseModel):
    id: str
    hashed_user_id: str
    categories: List[str]
    detection_count: int
    created_at: str
    severity: str


class PIIAlertsResponse(BaseModel):
    alerts: List[PIIAlertSchema]
    total: int
    page: int
    page_size: int


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


# ---------- PII Configuration Endpoints ----------


@router.get("/pii-config", response_model=PIIConfigResponse)
async def get_pii_config(
    admin_ctx: AdminContext = Depends(require_admin),
):
    """Return the current PII detection configuration for the organization.

    Includes custom patterns, whitelist, and built-in default patterns.
    """
    from sqlalchemy import select

    from app.db.engine import AsyncSessionLocal
    from app.db.models import Organization
    from app.services.enterprise.pii_detection import DEFAULT_PATTERNS

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Organization.settings).where(
                Organization.id == admin_ctx.org_id
            )
        )
        settings = result.scalar() or {}

    return PIIConfigResponse(
        patterns=settings.get("pii_patterns", []),
        whitelist=settings.get("pii_whitelist", []),
        default_patterns=DEFAULT_PATTERNS,
    )


@router.put("/pii-config", response_model=PIIConfigResponse)
async def update_pii_config(
    body: PIIConfigRequest,
    admin_ctx: AdminContext = Depends(require_admin),
):
    """Update PII detection patterns and whitelist for the organization.

    Validates all regex patterns compile correctly before saving.
    """
    from sqlalchemy import select, update

    from app.db.engine import AsyncSessionLocal
    from app.db.models import Organization
    from app.services.enterprise.pii_detection import (
        DEFAULT_PATTERNS,
        PIIDetectionService,
    )

    # Validate regexes compile
    pattern_dicts = [p.model_dump() for p in body.patterns]
    errors = PIIDetectionService.validate_patterns(pattern_dicts)
    if errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "Invalid regex patterns", "errors": errors},
        )

    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Fetch current settings
            result = await session.execute(
                select(Organization.settings).where(
                    Organization.id == admin_ctx.org_id
                )
            )
            current_settings = result.scalar() or {}

            # Update PII-specific keys, preserve other settings
            current_settings["pii_patterns"] = pattern_dicts
            current_settings["pii_whitelist"] = body.whitelist

            await session.execute(
                update(Organization)
                .where(Organization.id == admin_ctx.org_id)
                .values(settings=current_settings)
            )

    return PIIConfigResponse(
        patterns=pattern_dicts,
        whitelist=body.whitelist,
        default_patterns=DEFAULT_PATTERNS,
    )


# ---------- ROI Report Endpoints ----------


@router.get("/reports/roi", response_model=ROIMetricsResponse)
async def get_roi_metrics(
    admin_ctx: AdminContext = Depends(require_admin),
    start_date: Optional[date] = Query(
        None,
        description="Start date (YYYY-MM-DD). Defaults to first day of current month.",
    ),
    end_date: Optional[date] = Query(
        None, description="End date (YYYY-MM-DD). Defaults to today."
    ),
):
    """Return ROI metrics with benchmark comparisons for the admin's org.

    All metrics use aggregate queries only (COUNT, AVG, SUM).
    No individual user data is returned.
    """
    from app.db.engine import AsyncSessionLocal
    from app.services.enterprise.roi_report import ROIReportService

    service = ROIReportService()

    async with AsyncSessionLocal() as session:
        metrics = await service.compute_metrics(
            session=session,
            org_id=admin_ctx.org_id,
            start_date=start_date,
            end_date=end_date,
        )

    return ROIMetricsResponse(**metrics)


@router.get("/reports/roi/schedule", response_model=ROIScheduleResponse)
async def get_roi_schedule(
    admin_ctx: AdminContext = Depends(require_admin),
):
    """Return the current ROI report schedule configuration."""
    from app.db.engine import AsyncSessionLocal
    from app.services.enterprise.roi_report import ROIReportService

    service = ROIReportService()

    async with AsyncSessionLocal() as session:
        schedule = await service.get_schedule(session, admin_ctx.org_id)

    return ROIScheduleResponse(**schedule)


@router.post("/reports/roi/schedule", response_model=ROIScheduleResponse)
async def save_roi_schedule(
    body: ROIScheduleRequest,
    admin_ctx: AdminContext = Depends(require_admin),
):
    """Save ROI report schedule config to Organization.settings.

    Stores under key 'roi_report_schedule' in the JSONB settings field.
    """
    from app.db.engine import AsyncSessionLocal
    from app.services.enterprise.roi_report import ROIReportService

    service = ROIReportService()

    async with AsyncSessionLocal() as session:
        async with session.begin():
            schedule = await service.save_schedule(
                session=session,
                org_id=admin_ctx.org_id,
                schedule_config=body.model_dump(),
            )

    return ROIScheduleResponse(**schedule)
