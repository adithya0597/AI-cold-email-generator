"""
User-related API endpoints.

All endpoints require Clerk JWT authentication.  The minimal ``/me``
endpoint serves as the end-to-end auth verification route -- if this
returns 200 with the user's Clerk ID, the entire auth chain is working.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.clerk import get_current_user_id

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
):
    """
    Return the currently authenticated user's identity.

    This is the simplest protected endpoint -- it proves the Clerk JWT
    was validated successfully and the ``sub`` claim was extracted.

    Future iterations will look up the user record in the database and
    return profile data.
    """
    return {
        "user_id": user_id,
        "message": "Authenticated successfully",
    }
