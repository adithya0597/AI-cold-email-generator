"""
Admin-only API endpoints.

These endpoints are intended for platform operators and require admin-level
authentication via the ``require_admin`` RBAC dependency, which verifies
that the caller holds an organization admin role.
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr

from app.auth.admin import AdminContext, require_admin
from app.observability.cost_tracker import get_all_costs_summary
from app.worker.dlq import dlq_length, get_dlq_contents

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------- Request/Response schemas ----------


class RowErrorSchema(BaseModel):
    row_number: int
    email: str
    error_reason: str


class BulkUploadResponse(BaseModel):
    total: int
    valid: int
    invalid: int
    queued: int
    errors: List[RowErrorSchema]


class InviteRequest(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class InvitationResponse(BaseModel):
    id: UUID
    email: str
    status: str
    created_at: datetime
    expires_at: datetime


# ---------- Autonomy request/response body schemas ----------


class _OrgRestrictionsBody(BaseModel):
    blocked_companies: List[str] = []
    blocked_industries: List[str] = []
    require_approval_industries: List[str] = []


class OrgAutonomySettingsBody(BaseModel):
    default_autonomy: str
    max_autonomy: str
    restrictions: Optional[_OrgRestrictionsBody] = None


class EmployeeAutonomyBody(BaseModel):
    level: str


class RestrictionsBody(BaseModel):
    blocked_companies: List[str] = []
    blocked_industries: List[str] = []
    require_approval_industries: List[str] = []


# ---------- Metrics schemas ----------


class OrgMetricsSchema(BaseModel):
    enrolled_count: int
    active_count: int
    jobs_reviewed_count: int
    applications_submitted_count: int
    interviews_scheduled_count: int
    placements_count: int
    placement_rate: float
    avg_time_to_placement_days: Optional[float] = None


class DailyMetricsSchema(BaseModel):
    date: str
    applications: int
    interviews: int
    placements: int


class MetricsResponse(BaseModel):
    summary: OrgMetricsSchema
    daily_breakdown: List[DailyMetricsSchema]
    date_range: dict


@router.get("/llm-costs")
async def get_llm_costs(admin_ctx: AdminContext = Depends(require_admin)):
    """Return aggregated LLM cost data for the current month.

    Returns total spend, per-user breakdown, and projected month-end cost.
    Data is sourced from Redis-backed monthly counters maintained by the
    ``track_llm_cost`` function in the cost tracker module.
    """
    return await get_all_costs_summary()


@router.get("/dlq")
async def get_dlq(
    admin_ctx: AdminContext = Depends(require_admin),
    queue: str = Query("default", description="Queue name to inspect"),
    limit: int = Query(50, ge=1, le=500, description="Max entries to return"),
):
    """Return dead letter queue contents for monitoring.

    Lists failed tasks that exhausted their retries, stored in Redis
    with a 7-day TTL.
    """
    entries = await get_dlq_contents(queue=queue, limit=limit)
    total = await dlq_length(queue=queue)
    return {"queue": queue, "total": total, "entries": entries}


@router.post("/employees/bulk-upload", response_model=BulkUploadResponse)
async def bulk_upload_employees(
    file: UploadFile,
    admin_ctx: AdminContext = Depends(require_admin),
):
    """Upload a CSV of employee emails for bulk onboarding.

    Parses and validates the CSV, queues valid rows for invitation
    processing via a Celery task, and returns a summary with errors.
    """
    from app.db.engine import AsyncSessionLocal
    from app.services.enterprise.audit import log_audit_event
    from app.services.enterprise.csv_onboarding import CSVOnboardingService

    content = await file.read()
    service = CSVOnboardingService()

    try:
        rows = service.parse_csv(content)
    except ValueError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(exc))

    async with AsyncSessionLocal() as session:
        async with session.begin():
            validation = await service.validate_rows(rows, admin_ctx.org_id, session)

            queued = 0
            if validation.valid_rows:
                from app.worker.tasks import bulk_onboard_employees

                bulk_onboard_employees.delay(
                    org_id=admin_ctx.org_id,
                    valid_rows=validation.valid_rows,
                )
                queued = len(validation.valid_rows)

            summary = {
                "total": len(rows),
                "valid": len(validation.valid_rows),
                "invalid": len(validation.invalid_rows),
                "queued": queued,
            }

            await log_audit_event(
                session=session,
                org_id=admin_ctx.org_id,
                actor_id=admin_ctx.user_id,
                action="bulk_upload",
                resource_type="csv_onboarding",
                changes=summary,
            )

    errors = [
        RowErrorSchema(
            row_number=e.row_number,
            email=e.email,
            error_reason=e.error_reason,
        )
        for e in validation.invalid_rows
    ]

    return BulkUploadResponse(
        total=summary["total"],
        valid=summary["valid"],
        invalid=summary["invalid"],
        queued=summary["queued"],
        errors=errors,
    )


@router.post("/employees/invite", response_model=InvitationResponse)
async def invite_employee(
    body: InviteRequest,
    admin_ctx: AdminContext = Depends(require_admin),
):
    """Send an invitation email to an employee.

    Creates an invitation record, sends a branded email with accept/decline
    links, and returns the invitation summary. Any existing pending invitation
    for the same email in this org is automatically revoked.
    """
    from app.config import settings
    from app.db.engine import AsyncSessionLocal
    from app.services.enterprise.invitation import InvitationService
    from app.services.transactional_email import send_invitation_email

    service = InvitationService()

    async with AsyncSessionLocal() as session:
        async with session.begin():
            invitation = await service.create_invitation(
                session=session,
                org_id=admin_ctx.org_id,
                email=str(body.email),
                invited_by=admin_ctx.user_id,
                first_name=body.first_name,
                last_name=body.last_name,
            )

            # Build accept/decline URLs
            base_url = getattr(settings, "FRONTEND_URL", "https://app.jobpilot.ai")
            token = str(invitation.token)
            accept_url = f"{base_url}/invitations/{token}/accept"
            decline_url = f"{base_url}/invitations/{token}/decline"

            # Send invitation email (fire-and-forget, don't block on failure)
            try:
                await send_invitation_email(
                    to=str(body.email),
                    admin_name=admin_ctx.org_name,  # Use org name as admin display
                    company_name=admin_ctx.org_name,
                    accept_url=accept_url,
                    decline_url=decline_url,
                    recipient_first_name=body.first_name,
                )
            except Exception:
                import logging
                logging.getLogger(__name__).warning(
                    "Failed to send invitation email to %s, invitation still created",
                    body.email,
                )

            return InvitationResponse(
                id=invitation.id,
                email=invitation.email,
                status=invitation.status.value,
                created_at=invitation.created_at,
                expires_at=invitation.expires_at,
            )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    admin_ctx: AdminContext = Depends(require_admin),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    export_format: Optional[str] = Query(None, description="Export format: 'csv'"),
):
    """Return aggregate organization metrics for the admin's org.

    Defaults to the last 30 days if no date range is provided.
    If ``export_format=csv``, returns a CSV file download instead of JSON.

    All data is aggregated at the org level -- no individual user data
    is ever exposed.
    """
    from app.db.engine import AsyncSessionLocal
    from app.services.enterprise.audit import log_audit_event
    from app.services.enterprise.metrics import EnterpriseMetricsService

    effective_end = end_date or date.today()
    effective_start = start_date or (effective_end - timedelta(days=30))

    service = EnterpriseMetricsService()

    async with AsyncSessionLocal() as session:
        async with session.begin():
            summary = await service.get_aggregate_metrics(
                session, admin_ctx.org_id, effective_start, effective_end
            )
            daily = await service.get_daily_breakdown(
                session, admin_ctx.org_id, effective_start, effective_end
            )

            action = "export_metrics" if export_format == "csv" else "view_metrics"
            await log_audit_event(
                session=session,
                org_id=admin_ctx.org_id,
                actor_id=admin_ctx.user_id,
                action=action,
                resource_type="org_metrics",
                changes={
                    "start_date": effective_start.isoformat(),
                    "end_date": effective_end.isoformat(),
                },
            )

    summary_schema = OrgMetricsSchema(
        enrolled_count=summary.enrolled_count,
        active_count=summary.active_count,
        jobs_reviewed_count=summary.jobs_reviewed_count,
        applications_submitted_count=summary.applications_submitted_count,
        interviews_scheduled_count=summary.interviews_scheduled_count,
        placements_count=summary.placements_count,
        placement_rate=summary.placement_rate,
        avg_time_to_placement_days=summary.avg_time_to_placement_days,
    )

    daily_schemas = [
        DailyMetricsSchema(
            date=d.date,
            applications=d.applications,
            interviews=d.interviews,
            placements=d.placements,
        )
        for d in daily
    ]

    if export_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)

        # Summary section
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Enrolled", summary.enrolled_count])
        writer.writerow(["Active", summary.active_count])
        writer.writerow(["Jobs Reviewed", summary.jobs_reviewed_count])
        writer.writerow(["Applications Submitted", summary.applications_submitted_count])
        writer.writerow(["Interviews Scheduled", summary.interviews_scheduled_count])
        writer.writerow(["Placements", summary.placements_count])
        writer.writerow(["Placement Rate (%)", summary.placement_rate])
        writer.writerow(["Avg Time to Placement (days)", summary.avg_time_to_placement_days or "N/A"])
        writer.writerow([])

        # Daily breakdown section
        writer.writerow(["Date", "Applications", "Interviews", "Placements"])
        for d in daily:
            writer.writerow([d.date, d.applications, d.interviews, d.placements])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=org_metrics.csv"},
        )

    return MetricsResponse(
        summary=summary_schema,
        daily_breakdown=daily_schemas,
        date_range={
            "start": effective_start.isoformat(),
            "end": effective_end.isoformat(),
        },
    )


# ---------- Autonomy Configuration endpoints ----------


@router.get("/autonomy-config", response_model=None)
async def get_autonomy_config(
    admin_ctx: AdminContext = Depends(require_admin),
):
    """Return the current organization autonomy config and restrictions.

    Reads from the Organization.settings JSONB 'autonomy' key.
    Returns defaults if no config has been set.
    """
    from app.db.engine import AsyncSessionLocal
    from app.services.enterprise.autonomy_config import (
        AutonomyConfigService,
        OrgAutonomyConfigResponse,
    )

    service = AutonomyConfigService()

    async with AsyncSessionLocal() as session:
        config = await service.get_org_autonomy_config(session, admin_ctx.org_id)

    return OrgAutonomyConfigResponse(
        default_autonomy=config.default_autonomy,
        max_autonomy=config.max_autonomy,
        restrictions=config.restrictions,
    )


@router.put("/autonomy-config", response_model=None)
async def update_autonomy_config(
    body: OrgAutonomySettingsBody,
    admin_ctx: AdminContext = Depends(require_admin),
):
    """Update organization autonomy config (default level, max level, restrictions).

    Validates that default_autonomy does not exceed max_autonomy.
    Logs an audit event with before/after values.
    """
    from app.db.engine import AsyncSessionLocal
    from app.services.enterprise.audit import log_audit_event
    from app.services.enterprise.autonomy_config import (
        AutonomyConfigService,
        OrgAutonomyConfigResponse,
        OrgAutonomySettings,
        OrgRestrictions,
    )

    service = AutonomyConfigService()

    async with AsyncSessionLocal() as session:
        async with session.begin():
            old_config = await service.get_org_autonomy_config(
                session, admin_ctx.org_id
            )

            new_config = OrgAutonomySettings(
                default_autonomy=body.default_autonomy,
                max_autonomy=body.max_autonomy,
                restrictions=OrgRestrictions(**body.restrictions.model_dump())
                if body.restrictions
                else old_config.restrictions,
            )

            try:
                result = await service.update_org_autonomy_config(
                    session, admin_ctx.org_id, new_config
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

            await log_audit_event(
                session=session,
                org_id=admin_ctx.org_id,
                actor_id=admin_ctx.user_id,
                action="update_autonomy_config",
                resource_type="organization",
                resource_id=admin_ctx.org_id,
                changes={
                    "before": old_config.model_dump(),
                    "after": result.model_dump(),
                },
            )

    return OrgAutonomyConfigResponse(
        default_autonomy=result.default_autonomy,
        max_autonomy=result.max_autonomy,
        restrictions=result.restrictions,
    )


@router.put("/users/{user_id}/autonomy", response_model=None)
async def set_user_autonomy(
    user_id: UUID,
    body: "EmployeeAutonomyBody",
    admin_ctx: AdminContext = Depends(require_admin),
):
    """Set per-employee autonomy override.

    Validates the requested level against the organization's max_autonomy.
    Caps the level if it exceeds the ceiling. Logs an audit event.
    """
    from app.db.engine import AsyncSessionLocal
    from app.services.enterprise.audit import log_audit_event
    from app.services.enterprise.autonomy_config import AutonomyConfigService

    service = AutonomyConfigService()

    async with AsyncSessionLocal() as session:
        async with session.begin():
            is_valid = await service.validate_employee_autonomy(
                session, admin_ctx.org_id, body.level
            )
            if not is_valid:
                config = await service.get_org_autonomy_config(
                    session, admin_ctx.org_id
                )
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Requested level '{body.level}' exceeds organization "
                        f"maximum autonomy '{config.max_autonomy}'"
                    ),
                )

            effective_level = await service.set_employee_autonomy(
                session, admin_ctx.org_id, str(user_id), body.level
            )

            await log_audit_event(
                session=session,
                org_id=admin_ctx.org_id,
                actor_id=admin_ctx.user_id,
                action="set_employee_autonomy",
                resource_type="user_autonomy",
                resource_id=str(user_id),
                changes={
                    "requested_level": body.level,
                    "effective_level": effective_level,
                },
            )

    return {"user_id": str(user_id), "effective_level": effective_level}


@router.get("/autonomy-config/restrictions", response_model=None)
async def get_restrictions(
    admin_ctx: AdminContext = Depends(require_admin),
):
    """Return current organization restrictions.

    Reads from the Organization.settings JSONB 'autonomy.restrictions' key.
    """
    from app.db.engine import AsyncSessionLocal
    from app.services.enterprise.autonomy_config import AutonomyConfigService

    service = AutonomyConfigService()

    async with AsyncSessionLocal() as session:
        config = await service.get_org_autonomy_config(session, admin_ctx.org_id)

    return config.restrictions


@router.put("/autonomy-config/restrictions", response_model=None)
async def update_restrictions(
    body: "RestrictionsBody",
    admin_ctx: AdminContext = Depends(require_admin),
):
    """Update organization restrictions (blocked companies, industries, approval rules).

    Logs an audit event with before/after values.
    """
    from app.db.engine import AsyncSessionLocal
    from app.services.enterprise.audit import log_audit_event
    from app.services.enterprise.autonomy_config import (
        AutonomyConfigService,
        OrgRestrictions,
    )

    service = AutonomyConfigService()

    async with AsyncSessionLocal() as session:
        async with session.begin():
            old_config = await service.get_org_autonomy_config(
                session, admin_ctx.org_id
            )
            old_restrictions = old_config.restrictions

            new_restrictions = OrgRestrictions(
                blocked_companies=body.blocked_companies,
                blocked_industries=body.blocked_industries,
                require_approval_industries=body.require_approval_industries,
            )

            result = await service.update_restrictions(
                session, admin_ctx.org_id, new_restrictions
            )

            await log_audit_event(
                session=session,
                org_id=admin_ctx.org_id,
                actor_id=admin_ctx.user_id,
                action="update_restrictions",
                resource_type="organization",
                resource_id=admin_ctx.org_id,
                changes={
                    "before": old_restrictions.model_dump(),
                    "after": result.model_dump(),
                },
            )

    return result
