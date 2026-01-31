"""
Aggregate router for all API v1 endpoints.

Every sub-router in the v1 package is included here under a single
``/api/v1`` prefix so that ``main.py`` only needs one ``include_router``
call.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import admin, health, users

api_router = APIRouter(prefix="/api/v1")

# --- public ---
api_router.include_router(health.router)

# --- authenticated ---
api_router.include_router(users.router)

# --- admin ---
api_router.include_router(admin.router)
