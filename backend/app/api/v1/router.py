"""
Aggregate router for all API v1 endpoints.

Every sub-router in the v1 package is included here under a single
``/api/v1`` prefix so that ``main.py`` only needs one ``include_router``
call.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import admin, agents, briefings, health, learned_preferences, matches, onboarding, preferences, users, ws

api_router = APIRouter(prefix="/api/v1")

# --- public ---
api_router.include_router(health.router)

# --- websocket ---
api_router.include_router(ws.router)

# --- authenticated ---
api_router.include_router(users.router)
api_router.include_router(onboarding.router)
api_router.include_router(preferences.router)
api_router.include_router(briefings.router)
api_router.include_router(agents.router)
api_router.include_router(matches.router)
api_router.include_router(learned_preferences.router)

# --- admin ---
api_router.include_router(admin.router)
