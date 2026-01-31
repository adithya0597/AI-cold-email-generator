"""
Langfuse LLM observability client for JobPilot.

Replaces ``cost_tracker.py`` as the primary LLM observability layer.
The legacy ``cost_tracker.py`` is kept as a fallback for one sprint, then
will be removed.

Key design decisions:
    - Module-level ``langfuse`` instance (initialized once at import).
    - ``create_agent_trace()`` helper for Celery tasks -- contextvars do
      NOT propagate across Celery process boundaries, so each task must
      create an explicit Langfuse trace at the start.
    - ``flush_traces()`` must be called in Celery task ``finally`` blocks
      to ensure spans are flushed before the worker process completes.

Usage in agent methods::

    from langfuse.decorator import observe

    class MyAgent(BaseAgent):
        @observe(name="my_agent_execute")
        async def execute(self, user_id, task_data):
            ...

Usage in Celery tasks::

    from app.observability.langfuse_client import create_agent_trace, flush_traces

    @celery_app.task(...)
    def agent_job_scout(user_id, task_data):
        async def _execute():
            trace = create_agent_trace(user_id, "job_scout", agent_job_scout.request.id)
            try:
                ...
            finally:
                flush_traces()
        return asyncio.run(_execute())
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Langfuse client (lazy initialization)
# ---------------------------------------------------------------------------

_langfuse_instance = None


def _get_langfuse():
    """Lazily initialize and return the Langfuse client singleton.

    Lazy initialization avoids import-time errors when the ``langfuse``
    package is not installed or config values are missing.  The instance
    is created on first access and reused thereafter.
    """
    global _langfuse_instance
    if _langfuse_instance is not None:
        return _langfuse_instance

    try:
        from langfuse import Langfuse

        from app.config import settings

        _langfuse_instance = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY or None,
            secret_key=settings.LANGFUSE_SECRET_KEY or None,
            host=settings.LANGFUSE_HOST or "http://localhost:3000",
            enabled=bool(settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY),
        )
        logger.info(
            "Langfuse client initialized (host=%s, enabled=%s)",
            settings.LANGFUSE_HOST,
            _langfuse_instance.enabled if hasattr(_langfuse_instance, "enabled") else "unknown",
        )
    except ImportError:
        logger.warning(
            "langfuse package not installed -- observability disabled. "
            "Install with: pip install langfuse>=2.0.0"
        )
        _langfuse_instance = _NoOpLangfuse()
    except Exception as exc:
        logger.warning("Failed to initialize Langfuse client: %s", exc)
        _langfuse_instance = _NoOpLangfuse()

    return _langfuse_instance


class _NoOpLangfuse:
    """No-op stand-in when Langfuse is unavailable or disabled.

    Provides the same interface as the Langfuse client so callers do not
    need ``if langfuse:`` guards everywhere.
    """

    enabled = False

    def trace(self, **kwargs) -> "_NoOpTrace":
        return _NoOpTrace()

    def flush(self) -> None:
        pass

    def shutdown(self) -> None:
        pass


class _NoOpTrace:
    """No-op trace object returned by ``_NoOpLangfuse.trace()``."""

    id = "noop"

    def update(self, **kwargs) -> "_NoOpTrace":
        return self

    def span(self, **kwargs) -> "_NoOpTrace":
        return self

    def generation(self, **kwargs) -> "_NoOpTrace":
        return self

    def end(self, **kwargs) -> None:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@property
def langfuse():
    """Module-level accessor for the Langfuse instance."""
    return _get_langfuse()


def get_langfuse():
    """Return the Langfuse client instance.

    Prefer this function over direct ``langfuse`` access for clarity.
    """
    return _get_langfuse()


def create_agent_trace(
    user_id: str,
    agent_type: str,
    celery_task_id: str | None = None,
    metadata: dict[str, Any] | None = None,
):
    """Create an explicit Langfuse trace for a Celery agent task.

    Celery tasks run in separate processes where Python ``contextvars``
    do not propagate.  Each Celery task must call this function at the
    start to create a fresh trace, then pass the trace to nested
    ``@observe()`` calls or use it to create spans manually.

    Args:
        user_id: The user this agent is acting for.
        agent_type: The agent type string (e.g. ``"job_scout"``).
        celery_task_id: The Celery request ID for correlation.
        metadata: Optional extra metadata to attach to the trace.

    Returns:
        A Langfuse trace object (or ``_NoOpTrace`` if disabled).
    """
    client = _get_langfuse()

    trace_metadata = {
        "celery_task_id": celery_task_id or "unknown",
        "agent_type": agent_type,
    }
    if metadata:
        trace_metadata.update(metadata)

    try:
        trace = client.trace(
            name=f"{agent_type}_task",
            user_id=user_id,
            metadata=trace_metadata,
            tags=[f"agent:{agent_type}"],
        )
        logger.debug(
            "Created Langfuse trace for agent=%s user=%s celery_id=%s",
            agent_type,
            user_id,
            celery_task_id,
        )
        return trace
    except Exception as exc:
        logger.warning("Failed to create Langfuse trace: %s", exc)
        return _NoOpTrace()


def flush_traces() -> None:
    """Flush pending Langfuse spans to the server.

    Must be called in Celery task ``finally`` blocks to ensure data is
    sent before the worker process moves to the next task.
    """
    try:
        client = _get_langfuse()
        client.flush()
    except Exception as exc:
        logger.warning("Failed to flush Langfuse traces: %s", exc)


def shutdown() -> None:
    """Gracefully shut down the Langfuse client.

    Call during application shutdown to flush remaining data.
    """
    try:
        client = _get_langfuse()
        client.shutdown()
    except Exception as exc:
        logger.warning("Failed to shut down Langfuse client: %s", exc)
