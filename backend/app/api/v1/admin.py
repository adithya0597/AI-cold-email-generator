"""
Admin-only API endpoints.

These endpoints are intended for platform operators and require admin-level
authentication via the ``require_admin`` RBAC dependency, which verifies
that the caller holds an organization admin role.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth.admin import AdminContext, require_admin
from app.observability.cost_tracker import get_all_costs_summary
from app.worker.dlq import dlq_length, get_dlq_contents

router = APIRouter(prefix="/admin", tags=["admin"])


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
