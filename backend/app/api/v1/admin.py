"""
Admin-only API endpoints.

These endpoints are intended for platform operators and require admin-level
authentication.  For now the ``/admin`` prefix is used as a namespace
convention -- full admin RBAC will be added when user roles are implemented.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.observability.cost_tracker import get_all_costs_summary

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/llm-costs")
async def get_llm_costs():
    """Return aggregated LLM cost data for the current month.

    Returns total spend, per-user breakdown, and projected month-end cost.
    Data is sourced from Redis-backed monthly counters maintained by the
    ``track_llm_cost`` function in the cost tracker module.
    """
    return await get_all_costs_summary()
