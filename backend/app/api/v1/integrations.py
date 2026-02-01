"""
Integration API endpoints for JobPilot.

Provides:
    - GET  /integrations/gmail/auth-url     -- get OAuth authorization URL
    - POST /integrations/gmail/callback     -- handle OAuth callback
    - GET  /integrations/gmail/status       -- get connection status
    - POST /integrations/gmail/disconnect   -- disconnect Gmail
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.clerk import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class AuthUrlResponse(BaseModel):
    """Response for GET /gmail/auth-url."""

    auth_url: str


class CallbackRequest(BaseModel):
    """Request body for POST /gmail/callback."""

    code: str
    state: Optional[str] = None


class CallbackResponse(BaseModel):
    """Response for POST /gmail/callback."""

    connection_id: str
    email_address: str
    status: str


class ConnectionStatusResponse(BaseModel):
    """Response for GET /gmail/status."""

    connected: bool
    email_address: Optional[str] = None
    status: Optional[str] = None
    connected_at: Optional[str] = None
    last_sync_at: Optional[str] = None


class DisconnectResponse(BaseModel):
    """Response for POST /gmail/disconnect."""

    disconnected: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/gmail/auth-url", response_model=AuthUrlResponse)
async def get_gmail_auth_url(
    user_id: str = Depends(get_current_user_id),
):
    """Return the Google OAuth authorization URL for Gmail."""
    from app.services.gmail_service import build_auth_url

    auth_url = build_auth_url(state=user_id)
    return AuthUrlResponse(auth_url=auth_url)


@router.post("/gmail/callback", response_model=CallbackResponse)
async def gmail_oauth_callback(
    body: CallbackRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Handle Google OAuth callback — exchange code for tokens and store."""
    from app.services import gmail_service

    try:
        tokens = await gmail_service.exchange_code_for_tokens(body.code)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth token exchange failed: {exc}",
        )

    access_token = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No access token received from Google",
        )

    # Get the user's email address
    try:
        email_address = await gmail_service.get_user_email(access_token)
    except ValueError:
        email_address = ""

    # Store connection
    connection_id = await gmail_service.store_connection(
        user_id=user_id,
        email_address=email_address,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )

    return CallbackResponse(
        connection_id=connection_id,
        email_address=email_address,
        status="active",
    )


@router.get("/gmail/status", response_model=ConnectionStatusResponse)
async def get_gmail_status(
    user_id: str = Depends(get_current_user_id),
):
    """Get the current Gmail connection status for the user."""
    from app.services.gmail_service import get_connection_status

    conn = await get_connection_status(user_id)

    if conn is None:
        return ConnectionStatusResponse(connected=False)

    return ConnectionStatusResponse(
        connected=True,
        email_address=conn["email_address"],
        status=conn["status"],
        connected_at=conn["connected_at"],
        last_sync_at=conn["last_sync_at"],
    )


@router.post("/gmail/disconnect", response_model=DisconnectResponse)
async def disconnect_gmail(
    user_id: str = Depends(get_current_user_id),
):
    """Disconnect Gmail integration for the user."""
    from app.services.gmail_service import disconnect

    disconnected = await disconnect(user_id)

    if not disconnected:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Gmail connection found",
        )

    return DisconnectResponse(disconnected=True)
