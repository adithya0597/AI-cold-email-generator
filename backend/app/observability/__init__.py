"""
Observability package -- OpenTelemetry tracing, Sentry error tracking, and LLM cost tracking.

Usage in app factory::

    from app.observability.tracing import setup_observability
    setup_observability(app)
"""

from app.observability.tracing import setup_observability

__all__ = ["setup_observability"]
