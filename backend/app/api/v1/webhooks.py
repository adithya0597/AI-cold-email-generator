"""
Webhook endpoints for third-party service callbacks.

Currently handles Resend email event webhooks (delivery, bounce, complaint,
open, click).  Signature verification uses Resend's svix-based HMAC-SHA256
scheme.

Alert Configuration
-------------------
Bounce and complaint events are logged at WARNING level.  In production,
configure a log-based alert (e.g. Sentry, Datadog) to fire when
``email.bounced`` or ``email.complained`` events exceed a threshold.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Event types we handle
_KNOWN_EVENTS = frozenset(
    {
        "email.delivered",
        "email.bounced",
        "email.complained",
        "email.opened",
        "email.clicked",
    }
)

# Maximum age of a webhook signature (5 minutes)
_TIMESTAMP_TOLERANCE = 300


def verify_webhook_signature(
    payload: bytes,
    svix_id: str,
    svix_timestamp: str,
    svix_signature: str,
    secret: str,
) -> bool:
    """Verify a Resend webhook signature (svix-based HMAC-SHA256).

    Parameters
    ----------
    payload:
        Raw request body bytes.
    svix_id:
        Value of the ``svix-id`` header.
    svix_timestamp:
        Value of the ``svix-timestamp`` header.
    svix_signature:
        Value of the ``svix-signature`` header (may contain multiple sigs).
    secret:
        The webhook signing secret from Resend dashboard (``whsec_...``).

    Returns
    -------
    bool
        True if the signature is valid and timestamp is fresh.
    """
    try:
        ts = int(svix_timestamp)
    except (ValueError, TypeError):
        return False

    if abs(time.time() - ts) > _TIMESTAMP_TOLERANCE:
        return False

    # Secret format: "whsec_<base64-key>"
    secret_bytes = base64.b64decode(secret.split("_", 1)[-1])
    to_sign = f"{svix_id}.{svix_timestamp}.{payload.decode()}"
    expected = base64.b64encode(
        hmac.new(secret_bytes, to_sign.encode(), hashlib.sha256).digest()
    ).decode()

    # svix-signature may contain space-separated signatures like "v1,<sig>"
    for sig in svix_signature.split(" "):
        scheme, _, value = sig.partition(",")
        if scheme == "v1" and hmac.compare_digest(value, expected):
            return True

    return False


@router.post("/resend")
async def resend_webhook(
    request: Request,
    svix_id: str = Header(default="", alias="svix-id"),
    svix_timestamp: str = Header(default="", alias="svix-timestamp"),
    svix_signature: str = Header(default="", alias="svix-signature"),
) -> Dict[str, str]:
    """Handle Resend email event webhooks.

    Verifies the svix signature header and processes email events
    (delivered, bounced, complained, opened, clicked).
    """
    body = await request.body()

    # Verify signature if secret is configured
    if settings.RESEND_WEBHOOK_SECRET:
        if not verify_webhook_signature(
            payload=body,
            svix_id=svix_id,
            svix_timestamp=svix_timestamp,
            svix_signature=svix_signature,
            secret=settings.RESEND_WEBHOOK_SECRET,
        ):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload: Dict[str, Any] = await request.json()
    event_type = payload.get("type", "")
    data = payload.get("data", {})

    if event_type not in _KNOWN_EVENTS:
        logger.debug("Ignoring unknown Resend event type: %s", event_type)
        return {"status": "ignored"}

    email_id = data.get("email_id", "unknown")
    to = data.get("to", [])

    if event_type in ("email.bounced", "email.complained"):
        logger.warning(
            "Email %s event: id=%s to=%s data=%s",
            event_type,
            email_id,
            to,
            data,
        )
    else:
        logger.info(
            "Email %s event: id=%s to=%s",
            event_type,
            email_id,
            to,
        )

    return {"status": "processed", "event_type": event_type}
