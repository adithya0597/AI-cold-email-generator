"""
Clerk JWT authentication for FastAPI.

Uses the ``fastapi-clerk-auth`` package to validate JWTs against Clerk's
JWKS endpoint.  If CLERK_DOMAIN is not configured (empty string), the
dependency will always reject requests with 401 -- this is intentional so
that protected routes are never accidentally left open.

Usage as a FastAPI dependency::

    from app.auth.clerk import require_auth, get_current_user_id

    @router.get("/protected")
    async def protected(user_id: str = Depends(get_current_user_id)):
        ...
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import Depends, HTTPException, status

from app.config import settings

logger = logging.getLogger(__name__)


def _build_clerk_auth():
    """
    Build the Clerk HTTP bearer dependency.

    Returns a FastAPI dependency that validates the Authorization header
    against Clerk's JWKS.  Lazily imports ``fastapi_clerk_auth`` so the
    module can be loaded even if the package is not yet installed (the
    import error will surface only when a protected endpoint is hit).
    """
    try:
        from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer

        if not settings.CLERK_DOMAIN:
            logger.warning(
                "CLERK_DOMAIN is not set -- all protected endpoints will "
                "return 401.  Set CLERK_DOMAIN in your .env to enable auth."
            )

        clerk_config = ClerkConfig(
            jwks_url=f"https://{settings.CLERK_DOMAIN}/.well-known/jwks.json"
        )
        return ClerkHTTPBearer(clerk_config=clerk_config)

    except ImportError:
        logger.warning(
            "fastapi-clerk-auth is not installed.  Protected endpoints "
            "will reject all requests until the package is available."
        )

        async def _reject_all(**_kwargs: Any):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication service unavailable (fastapi-clerk-auth not installed)",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return _reject_all


# Module-level dependency -- used in ``Depends(require_auth)``
require_auth = _build_clerk_auth()


async def get_current_user_id(
    auth=Depends(require_auth),
) -> str:
    """
    Extract the Clerk user ID (``sub`` claim) from a validated JWT.

    Use this as a FastAPI dependency on any endpoint that needs the
    authenticated user's identity::

        @router.get("/me")
        async def me(user_id: str = Depends(get_current_user_id)):
            return {"user_id": user_id}
    """
    try:
        # fastapi-clerk-auth stores decoded payload in `decoded` attribute
        decoded: Dict[str, Any] = auth.decoded  # type: ignore[union-attr]
        user_id: str = decoded["sub"]
        return user_id
    except (AttributeError, KeyError, TypeError) as exc:
        logger.error("Failed to extract user_id from JWT: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
