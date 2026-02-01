"""WebSocket-specific JWT validation for Clerk tokens."""
from __future__ import annotations

import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


async def validate_ws_token(token: str) -> Optional[str]:
    """Validate a Clerk JWT token for WebSocket connections.

    Returns the user_id (sub claim) if valid, None otherwise.

    Behaviour by environment:
      - CLERK_DOMAIN set (production): validate JWT via JWKS, return sub claim.
      - CLERK_DOMAIN empty (dev): log warning, return None.  The caller should
        fall through and use the URL path ``user_id`` as a dev-mode fallback.
    """
    if not token:
        return None

    if not settings.CLERK_DOMAIN:
        logger.warning(
            "CLERK_DOMAIN not set — WebSocket JWT validation skipped (dev mode)"
        )
        return None

    try:
        from fastapi_clerk_auth import ClerkConfig

        config = ClerkConfig(
            jwks_url=f"https://{settings.CLERK_DOMAIN}/.well-known/jwks.json"
        )
        decoded = config.decode(token)
        user_id = decoded.get("sub")
        if not user_id:
            logger.warning("JWT valid but missing 'sub' claim")
            return None
        return user_id
    except ImportError:
        logger.warning(
            "fastapi-clerk-auth not installed — WebSocket auth unavailable"
        )
        return None
    except Exception as exc:
        logger.debug("WebSocket JWT validation failed: %s", exc)
        return None
