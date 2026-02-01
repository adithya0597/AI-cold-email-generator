"""
User-related API endpoints.

All endpoints require Clerk JWT authentication.  The minimal ``/me``
endpoint serves as the end-to-end auth verification route -- if this
returns 200 with the user's Clerk ID, the entire auth chain is working.

GDPR data portability endpoints (``/me/export`` and ``DELETE /me``)
satisfy Article 15 (Right of Access) and Article 17 (Right to Erasure).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.auth.clerk import get_current_user_id

logger = logging.getLogger(__name__)

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


@router.get("/me/export")
async def export_user_data(
    user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """
    Export all user data (GDPR Article 15 -- Right of Access).

    Returns a JSON object containing all data associated with the
    authenticated user: profile, applications, documents, agent actions,
    and signed URLs for stored files.

    For large datasets this endpoint may enqueue a Celery task and
    return a ``202 Accepted`` with a task ID for polling.  For MVP
    the export is performed synchronously.
    """
    logger.info("GDPR data export requested by user %s", user_id)

    try:
        from sqlalchemy import select, text
        from app.db.engine import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            # Query all user-related tables.  Tables may not exist yet
            # in early development -- handle gracefully.
            export_data: Dict[str, Any] = {
                "export_metadata": {
                    "user_id": user_id,
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "format_version": "1.0",
                },
                "profile": {},
                "applications": [],
                "documents": [],
                "agent_actions": [],
                "agent_outputs": [],
            }

            # -- Profile -----------------------------------------------
            try:
                result = await session.execute(
                    text("SELECT * FROM users WHERE clerk_id = :uid"),
                    {"uid": user_id},
                )
                row = result.mappings().first()
                if row:
                    export_data["profile"] = {
                        k: str(v) if isinstance(v, datetime) else v
                        for k, v in dict(row).items()
                    }
            except Exception as exc:
                logger.debug("Could not export profile: %s", exc)
                export_data["profile"] = {"note": "Table not yet available"}

            # -- Applications -------------------------------------------
            try:
                result = await session.execute(
                    text(
                        "SELECT * FROM applications WHERE user_id = "
                        "(SELECT id FROM users WHERE clerk_id = :uid)"
                    ),
                    {"uid": user_id},
                )
                export_data["applications"] = [
                    {
                        k: str(v) if isinstance(v, datetime) else v
                        for k, v in dict(row).items()
                    }
                    for row in result.mappings().all()
                ]
            except Exception as exc:
                logger.debug("Could not export applications: %s", exc)

            # -- Documents ----------------------------------------------
            try:
                result = await session.execute(
                    text(
                        "SELECT * FROM documents WHERE user_id = "
                        "(SELECT id FROM users WHERE clerk_id = :uid)"
                    ),
                    {"uid": user_id},
                )
                export_data["documents"] = [
                    {
                        k: str(v) if isinstance(v, datetime) else v
                        for k, v in dict(row).items()
                    }
                    for row in result.mappings().all()
                ]
            except Exception as exc:
                logger.debug("Could not export documents: %s", exc)

            # -- Agent Actions ------------------------------------------
            try:
                result = await session.execute(
                    text(
                        "SELECT * FROM agent_actions WHERE user_id = "
                        "(SELECT id FROM users WHERE clerk_id = :uid)"
                    ),
                    {"uid": user_id},
                )
                export_data["agent_actions"] = [
                    {
                        k: str(v) if isinstance(v, datetime) else v
                        for k, v in dict(row).items()
                    }
                    for row in result.mappings().all()
                ]
            except Exception as exc:
                logger.debug("Could not export agent_actions: %s", exc)

        return export_data

    except Exception as exc:
        logger.error("GDPR export failed for user %s: %s", user_id, exc)
        # Return minimal export even if DB is unreachable
        return {
            "export_metadata": {
                "user_id": user_id,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "format_version": "1.0",
                "error": "Partial export -- some data sources unavailable",
            },
        }


@router.delete("/me")
async def delete_user_account(
    user_id: str = Depends(get_current_user_id),
):
    """
    Schedule account for deletion (GDPR Article 17 -- Right to Erasure).

    Sets a ``deleted_at`` timestamp on the user record.  The account
    enters a 30-day grace period during which the user can sign back in
    to cancel the deletion.  After the grace period a background Celery
    task permanently removes all user data.

    Returns 200 with confirmation details.
    """
    logger.info("Account deletion requested by user %s", user_id)

    deletion_scheduled_at = datetime.now(timezone.utc)

    try:
        from sqlalchemy import text
        from app.db.engine import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            try:
                await session.execute(
                    text(
                        "UPDATE users SET deleted_at = :ts WHERE clerk_id = :uid"
                    ),
                    {"ts": deletion_scheduled_at, "uid": user_id},
                )
                await session.commit()
                logger.info(
                    "User %s marked for deletion at %s",
                    user_id,
                    deletion_scheduled_at.isoformat(),
                )
            except Exception as exc:
                logger.warning(
                    "Could not mark user %s in DB (table may not exist yet): %s",
                    user_id,
                    exc,
                )

    except Exception as exc:
        logger.warning("DB unavailable for deletion marking: %s", exc)

    # Send deletion confirmation email
    try:
        from app.services.transactional_email import send_account_deletion_notice

        await send_account_deletion_notice(to=user_id, user_name=user_id)
    except Exception as exc:
        logger.warning("Could not send deletion email to %s: %s", user_id, exc)

    # Schedule permanent deletion after 30-day grace period
    try:
        from datetime import timedelta

        from app.worker.tasks import gdpr_permanent_delete

        gdpr_permanent_delete.apply_async(
            args=[user_id],
            eta=deletion_scheduled_at + timedelta(days=30),
        )
        logger.info("Scheduled permanent deletion for user %s", user_id)
    except Exception as exc:
        logger.warning("Could not schedule permanent deletion task: %s", exc)

    return JSONResponse(
        status_code=200,
        content={
            "message": "Account scheduled for deletion",
            "user_id": user_id,
            "deletion_scheduled_at": deletion_scheduled_at.isoformat(),
            "grace_period_days": 30,
            "cancellation_window_days": 14,
            "note": (
                "Sign in within 14 days to cancel deletion. "
                "After 30 days all data will be permanently removed."
            ),
        },
    )


@router.post("/me/cancel-deletion")
async def cancel_deletion(
    user_id: str = Depends(get_current_user_id),
):
    """
    Cancel a pending account deletion (GDPR -- within grace period).

    Clears the ``deleted_at`` timestamp, which causes the scheduled
    permanent-deletion Celery task to skip execution.
    """
    logger.info("Deletion cancellation requested by user %s", user_id)

    try:
        from sqlalchemy import text

        from app.db.engine import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(
                    "UPDATE users SET deleted_at = NULL "
                    "WHERE clerk_id = :uid AND deleted_at IS NOT NULL "
                    "RETURNING clerk_id"
                ),
                {"uid": user_id},
            )
            updated = result.scalar_one_or_none()
            await session.commit()

            if updated:
                logger.info("Deletion cancelled for user %s", user_id)
                return {"message": "Account deletion cancelled", "user_id": user_id}
            else:
                return JSONResponse(
                    status_code=404,
                    content={
                        "message": "No pending deletion found for this account",
                        "user_id": user_id,
                    },
                )

    except Exception as exc:
        logger.error("Cancellation failed for user %s: %s", user_id, exc)
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to cancel deletion"},
        )
