"""
Outlook OAuth and email fetching service for JobPilot.

Handles Microsoft OAuth 2.0 flow (authorization URL, token exchange),
token storage in email_connections table, and fetching job-related
emails via Microsoft Graph API. Supports both personal Outlook and
Office 365 accounts via the /common tenant.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# Microsoft identity platform v2.0 endpoints (common tenant for both personal + O365)
MS_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MS_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

# Scopes: read-only mail + user info + offline for refresh tokens
SCOPES = "openid email Mail.Read offline_access"

# OData filter for job-related emails
JOB_EMAIL_FILTER = (
    "contains(subject,'interview') or contains(subject,'offer') or "
    "contains(subject,'application') or contains(subject,'rejected') or "
    "contains(subject,'screening') or contains(subject,'recruiter')"
)


def build_auth_url(state: str | None = None) -> str:
    """Generate the Microsoft OAuth authorization URL."""
    from app.config import settings

    params = {
        "client_id": settings.MICROSOFT_CLIENT_ID,
        "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "response_mode": "query",
    }
    if state:
        params["state"] = state

    return f"{MS_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    """Exchange authorization code for tokens via Microsoft token endpoint."""
    import httpx

    from app.config import settings

    async with httpx.AsyncClient() as client:
        response = await client.post(
            MS_TOKEN_URL,
            data={
                "client_id": settings.MICROSOFT_CLIENT_ID,
                "client_secret": settings.MICROSOFT_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
                "scope": SCOPES,
            },
        )

    if response.status_code != 200:
        logger.error("Microsoft token exchange failed: %s", response.text)
        raise ValueError(f"Token exchange failed: {response.status_code}")

    return response.json()


async def get_user_email(access_token: str) -> str:
    """Fetch user email from Microsoft Graph /me endpoint."""
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GRAPH_API_BASE}/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if response.status_code != 200:
        raise ValueError(f"Failed to get user email: {response.status_code}")

    data = response.json()
    return data.get("mail") or data.get("userPrincipalName", "")


async def store_connection(
    user_id: str,
    email_address: str,
    access_token: str,
    refresh_token: str | None,
    expires_in: int | None,
) -> str:
    """Store or update an Outlook connection in the database."""
    import uuid

    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    now = datetime.now(timezone.utc)
    token_expires_at = None
    if expires_in:
        from datetime import timedelta

        token_expires_at = now + timedelta(seconds=expires_in)

    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            text(
                "SELECT id FROM email_connections "
                "WHERE user_id = (SELECT id FROM users WHERE clerk_id = :uid) "
                "AND provider = 'outlook' "
                "AND deleted_at IS NULL"
            ),
            {"uid": user_id},
        )
        row = existing.scalar()

        if row:
            await session.execute(
                text(
                    "UPDATE email_connections "
                    "SET access_token_encrypted = :access, "
                    "refresh_token_encrypted = :refresh, "
                    "token_expires_at = :expires, "
                    "email_address = :email, "
                    "status = 'active', "
                    "connected_at = :now "
                    "WHERE id = :id"
                ),
                {
                    "access": access_token,
                    "refresh": refresh_token,
                    "expires": token_expires_at,
                    "email": email_address,
                    "now": now,
                    "id": str(row),
                },
            )
            await session.commit()
            return str(row)
        else:
            conn_id = str(uuid.uuid4())
            await session.execute(
                text(
                    "INSERT INTO email_connections "
                    "(id, user_id, provider, email_address, "
                    "access_token_encrypted, refresh_token_encrypted, "
                    "token_expires_at, status, connected_at) "
                    "VALUES (:id, "
                    "(SELECT id FROM users WHERE clerk_id = :uid), "
                    "'outlook', :email, :access, :refresh, :expires, "
                    "'active', :now)"
                ),
                {
                    "id": conn_id,
                    "uid": user_id,
                    "email": email_address,
                    "access": access_token,
                    "refresh": refresh_token,
                    "expires": token_expires_at,
                    "now": now,
                },
            )
            await session.commit()
            return conn_id


async def get_connection_status(user_id: str) -> Optional[dict[str, Any]]:
    """Get the current Outlook connection status for a user."""
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "SELECT id, email_address, status, connected_at, last_sync_at "
                "FROM email_connections "
                "WHERE user_id = (SELECT id FROM users WHERE clerk_id = :uid) "
                "AND provider = 'outlook' "
                "AND deleted_at IS NULL"
            ),
            {"uid": user_id},
        )
        row = result.mappings().first()

    if row is None:
        return None

    return {
        "id": str(row["id"]),
        "email_address": row["email_address"],
        "status": row["status"],
        "connected_at": row["connected_at"].isoformat() if row["connected_at"] else None,
        "last_sync_at": row["last_sync_at"].isoformat() if row["last_sync_at"] else None,
    }


async def disconnect(user_id: str) -> bool:
    """Disconnect Outlook by soft-deleting the connection."""
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "UPDATE email_connections "
                "SET deleted_at = :now, status = 'disconnected' "
                "WHERE user_id = (SELECT id FROM users WHERE clerk_id = :uid) "
                "AND provider = 'outlook' "
                "AND deleted_at IS NULL"
            ),
            {"uid": user_id, "now": now},
        )
        await session.commit()
        return result.rowcount > 0


async def fetch_job_emails(
    access_token: str, max_results: int = 20
) -> list[dict[str, str]]:
    """Fetch recent job-related emails from Microsoft Graph API."""
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GRAPH_API_BASE}/me/messages",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "$filter": JOB_EMAIL_FILTER,
                "$top": max_results,
                "$select": "id,subject,from,bodyPreview,receivedDateTime",
                "$orderby": "receivedDateTime desc",
            },
        )

    if response.status_code != 200:
        logger.error("Graph API messages failed: %s", response.text)
        return []

    messages = response.json().get("value", [])
    return [
        {
            "id": msg.get("id", ""),
            "subject": msg.get("subject", ""),
            "from_address": (msg.get("from", {}).get("emailAddress", {}).get("address", "")),
            "snippet": msg.get("bodyPreview", ""),
        }
        for msg in messages
    ]
