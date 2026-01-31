"""PostHog analytics event tracking. Fire-and-forget -- never breaks user flow."""

import logging

import posthog

from app.config import settings

logger = logging.getLogger(__name__)

_initialized = False


def _ensure_init() -> None:
    global _initialized
    if not _initialized and settings.POSTHOG_API_KEY:
        posthog.project_api_key = settings.POSTHOG_API_KEY
        posthog.host = settings.POSTHOG_HOST
        _initialized = True


def track_event(user_id: str, event: str, properties: dict | None = None) -> None:
    """Track an analytics event. Silent on failure."""
    try:
        _ensure_init()
        if not settings.POSTHOG_API_KEY:
            return  # Analytics disabled
        posthog.capture(distinct_id=user_id, event=event, properties=properties or {})
    except Exception:
        logger.debug("Analytics track_event failed for event=%s", event, exc_info=True)


def identify_user(user_id: str, properties: dict | None = None) -> None:
    """Identify a user with properties. Silent on failure."""
    try:
        _ensure_init()
        if not settings.POSTHOG_API_KEY:
            return
        posthog.identify(distinct_id=user_id, properties=properties or {})
    except Exception:
        logger.debug("Analytics identify_user failed for user=%s", user_id, exc_info=True)
