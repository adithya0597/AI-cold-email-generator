"""
Exponential backoff retry utilities for Celery tasks.

Provides ``calculate_backoff`` for delay calculation and
``retry_with_backoff`` as a convenience wrapper around ``task.retry()``.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def calculate_backoff(
    attempt: int,
    base_delay: int = 30,
    max_delay: int = 600,
) -> int:
    """Calculate exponential backoff delay in seconds.

    Args:
        attempt: Zero-indexed retry attempt number (0, 1, 2, ...).
        base_delay: Base delay in seconds (default 30).
        max_delay: Maximum delay cap in seconds (default 600).

    Returns:
        Delay in seconds: ``min(base_delay * 2^attempt, max_delay)``.
    """
    delay = base_delay * (2 ** attempt)
    return min(delay, max_delay)


def retry_with_backoff(task, exc, attempt: int | None = None) -> None:
    """Retry a Celery task with exponential backoff.

    Convenience wrapper that calculates the delay and calls
    ``task.retry()`` with the appropriate countdown.

    Args:
        task: Bound Celery task instance (``self`` in a bound task).
        exc: The exception that triggered the retry.
        attempt: Override attempt number. If ``None``, uses
                 ``task.request.retries`` (current retry count).

    Raises:
        celery.exceptions.Retry: Always (this is how ``task.retry`` works).
    """
    if attempt is None:
        attempt = task.request.retries
    delay = calculate_backoff(attempt)
    logger.info(
        "Retrying task %s (attempt %d) in %ds: %s",
        task.name,
        attempt,
        delay,
        str(exc)[:200],
    )
    raise task.retry(exc=exc, countdown=delay)
