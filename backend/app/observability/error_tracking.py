"""
Error tracking helpers for Sentry integration.

This module provides:

- ``_before_send``: Event callback that scrubs PII and applies custom
  fingerprinting for known error types.
- ``configure_sentry_scope``: ASGI middleware that sets ``user_id`` on
  the Sentry scope from Clerk auth (``request.state.user_id``).
- ``capture_error``: Convenience helper for capturing exceptions with
  extra context (agent type, request path, etc.).

Alert Configuration (AC3)
-------------------------
To receive alerts when the error rate exceeds 1%, create a Sentry alert
rule in the dashboard:

1. Navigate to **Alerts > Create Alert Rule > Issues**.
2. Set condition: *"Number of events is more than 1% of total requests
   in a 5-minute window"* (use the **Percent** metric alert type with
   ``count()`` over ``transaction`` events as denominator).
3. Choose notification channels: email, Slack webhook, or PagerDuty
   integration depending on team preference.
4. Set action: notify the ``#ops-alerts`` channel (or equivalent).
5. Save the rule for both ``jobpilot-api`` and ``jobpilot-frontend``
   projects.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import sentry_sdk

logger = logging.getLogger(__name__)

# Error types that get their own Sentry fingerprint for cleaner grouping.
_FINGERPRINTED_ERRORS: set[str] = {
    "RateLimitError",
    "WebScrapingError",
    "LLMGenerationError",
}


# ---------------------------------------------------------------------------
# before_send callback
# ---------------------------------------------------------------------------

def _before_send(event: Dict[str, Any], hint: Dict[str, Any]) -> Dict[str, Any]:
    """Scrub PII from user context and apply custom fingerprinting.

    Registered as the ``before_send`` callback in ``sentry_sdk.init()``.

    * Keeps only ``id`` in ``event["user"]`` -- strips email, name,
      ip_address, and any other fields.
    * Sets ``event["fingerprint"]`` to ``[<ErrorType>]`` for known
      error classes so Sentry groups them consistently.
    """

    # -- PII scrubbing -------------------------------------------------------
    if "user" in event:
        user_id = event["user"].get("id")
        event["user"] = {"id": user_id} if user_id else {}

    # -- Custom fingerprinting -----------------------------------------------
    try:
        exc_values = event.get("exception", {}).get("values", [])
        if exc_values:
            exc_type = exc_values[0].get("type", "")
            if exc_type in _FINGERPRINTED_ERRORS:
                event["fingerprint"] = [exc_type]
    except (KeyError, IndexError, TypeError):
        pass  # malformed event -- let Sentry handle it normally

    return event


# ---------------------------------------------------------------------------
# ASGI middleware
# ---------------------------------------------------------------------------

async def configure_sentry_scope(request: Any, call_next: Any) -> Any:
    """HTTP middleware that sets ``user_id`` on the active Sentry scope.

    Must be registered **after** Clerk auth middleware so that
    ``request.state.user_id`` is available.

    Usage in ``create_app()``::

        app.middleware("http")(configure_sentry_scope)
    """

    user_id: Optional[str] = getattr(request.state, "user_id", None)
    if user_id:
        sentry_sdk.set_user({"id": user_id})

    try:
        response = await call_next(request)
    finally:
        # Clear user context after request to avoid leaking across requests
        sentry_sdk.set_user(None)

    return response


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------

def capture_error(exc: BaseException, **context: Any) -> Optional[str]:
    """Capture an exception to Sentry with optional extra context.

    Parameters
    ----------
    exc:
        The exception instance to report.
    **context:
        Arbitrary key-value pairs attached as Sentry ``extras``
        (e.g. ``agent_type="scout"``, ``request_path="/api/v1/jobs"``).

    Returns
    -------
    str | None
        The Sentry event ID if capture succeeded, ``None`` otherwise.
    """

    try:
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)
            return sentry_sdk.capture_exception(exc)
    except Exception:
        logger.debug("Sentry capture failed (SDK may not be configured)", exc_info=True)
        return None
