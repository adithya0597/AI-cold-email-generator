"""
Gmail OAuth and email fetching service for JobPilot.

Handles OAuth 2.0 flow (authorization URL generation, token exchange),
token storage in the email_connections table, and fetching job-related
emails via the Gmail API.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"

# Scopes: read-only email access + user info for email address
SCOPES = "openid email https://www.googleapis.com/auth/gmail.readonly"

# Gmail search query for job-related emails only
JOB_EMAIL_QUERY = (
    "subject:(interview OR offer OR application OR applied OR rejected "
    "OR screening OR recruiter OR hiring OR position OR candidate)"
)


def build_auth_url(state: str | None = None) -> str:
    """Generate the Google OAuth authorization URL.

    Args:
        state: Optional CSRF state parameter.

    Returns:
        The full authorization URL to redirect the user to.
    """
    from app.config import settings

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    if state:
        params["state"] = state

    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    """Exchange an authorization code for access and refresh tokens.

    Args:
        code: The authorization code from the OAuth callback.

    Returns:
        Dict with access_token, refresh_token, expires_in, token_type.

    Raises:
        ValueError: If the token exchange fails.
    """
    import httpx

    from app.config import settings

    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            },
        )

    if response.status_code != 200:
        logger.error("Token exchange failed: %s", response.text)
        raise ValueError(f"Token exchange failed: {response.status_code}")

    return response.json()


async def get_user_email(access_token: str) -> str:
    """Fetch the user's email address from Google userinfo endpoint.

    Args:
        access_token: Valid Google access token.

    Returns:
        The user's email address string.

    Raises:
        ValueError: If the userinfo request fails.
    """
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if response.status_code != 200:
        raise ValueError(f"Failed to get user email: {response.status_code}")

    return response.json().get("email", "")


async def store_connection(
    user_id: str,
    email_address: str,
    access_token: str,
    refresh_token: str | None,
    expires_in: int | None,
) -> str:
    """Store or update a Gmail connection in the database.

    Args:
        user_id: Clerk user ID.
        email_address: The Gmail address.
        access_token: Google access token.
        refresh_token: Google refresh token (may be None on re-auth).
        expires_in: Token lifetime in seconds.

    Returns:
        The connection ID (UUID string).
    """
    import uuid

    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    now = datetime.now(timezone.utc)
    token_expires_at = None
    if expires_in:
        from datetime import timedelta

        token_expires_at = now + timedelta(seconds=expires_in)

    async with AsyncSessionLocal() as session:
        # Check if connection already exists for this user + provider
        existing = await session.execute(
            text(
                "SELECT id FROM email_connections "
                "WHERE user_id = (SELECT id FROM users WHERE clerk_id = :uid) "
                "AND provider = 'gmail' "
                "AND deleted_at IS NULL"
            ),
            {"uid": user_id},
        )
        row = existing.scalar()

        if row:
            # Update existing connection
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
            # Create new connection
            conn_id = str(uuid.uuid4())
            await session.execute(
                text(
                    "INSERT INTO email_connections "
                    "(id, user_id, provider, email_address, "
                    "access_token_encrypted, refresh_token_encrypted, "
                    "token_expires_at, status, connected_at) "
                    "VALUES (:id, "
                    "(SELECT id FROM users WHERE clerk_id = :uid), "
                    "'gmail', :email, :access, :refresh, :expires, "
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
    """Get the current Gmail connection status for a user.

    Returns:
        Dict with id, email_address, status, connected_at, last_sync_at
        or None if no connection exists.
    """
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "SELECT id, email_address, status, connected_at, last_sync_at "
                "FROM email_connections "
                "WHERE user_id = (SELECT id FROM users WHERE clerk_id = :uid) "
                "AND provider = 'gmail' "
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
    """Disconnect Gmail by soft-deleting the connection.

    Returns:
        True if a connection was disconnected, False if none found.
    """
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "UPDATE email_connections "
                "SET deleted_at = :now, status = 'disconnected' "
                "WHERE user_id = (SELECT id FROM users WHERE clerk_id = :uid) "
                "AND provider = 'gmail' "
                "AND deleted_at IS NULL"
            ),
            {"uid": user_id, "now": now},
        )
        await session.commit()
        return result.rowcount > 0


async def fetch_job_emails(
    access_token: str, max_results: int = 20
) -> list[dict[str, str]]:
    """Fetch recent job-related emails from Gmail API.

    Args:
        access_token: Valid Google access token.
        max_results: Maximum number of emails to fetch.

    Returns:
        List of dicts with id, subject, from_address, snippet.
    """
    import httpx

    async with httpx.AsyncClient() as client:
        # List messages matching job-related query
        list_response = await client.get(
            f"{GMAIL_API_BASE}/users/me/messages",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"q": JOB_EMAIL_QUERY, "maxResults": max_results},
        )

        if list_response.status_code != 200:
            logger.error("Gmail list failed: %s", list_response.text)
            return []

        messages = list_response.json().get("messages", [])
        if not messages:
            return []

        # Fetch details for each message
        emails = []
        for msg in messages[:max_results]:
            detail_response = await client.get(
                f"{GMAIL_API_BASE}/users/me/messages/{msg['id']}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"format": "metadata", "metadataHeaders": ["Subject", "From"]},
            )
            if detail_response.status_code != 200:
                continue

            detail = detail_response.json()
            headers = {
                h["name"]: h["value"]
                for h in detail.get("payload", {}).get("headers", [])
            }
            emails.append({
                "id": msg["id"],
                "subject": headers.get("Subject", ""),
                "from_address": headers.get("From", ""),
                "snippet": detail.get("snippet", ""),
            })

        return emails
