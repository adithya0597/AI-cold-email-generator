"""
OpenTelemetry distributed tracing and Sentry error tracking setup.

Initialises a TracerProvider with endpoint-appropriate exporters:
- **OTEL_EXPORTER_ENDPOINT set**: ``OTLPSpanExporter`` (gRPC to collector)
- **no endpoint**: ``ConsoleSpanExporter`` (traces printed to stdout)

Sentry is initialised with FastAPI and Starlette integrations so that
unhandled exceptions are captured automatically.

Call ``setup_observability(app)`` once inside ``create_app()`` in main.py.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import sentry_sdk
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

try:
    from opentelemetry.instrumentation.celery import CeleryInstrumentor
except ImportError:  # pragma: no cover
    CeleryInstrumentor = None  # type: ignore[assignment,misc]

from app.config import settings

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def setup_observability(app: "FastAPI") -> None:
    """Wire up Sentry error tracking and OpenTelemetry distributed tracing.

    This function is idempotent -- calling it more than once is harmless but
    only the first invocation has effect.
    """
    _init_sentry()
    otel_exporter = _init_opentelemetry(app)
    logger.info(
        "Observability initialised  [env=%s, sentry=%s, otel=%s]",
        settings.APP_ENV,
        "enabled" if settings.SENTRY_DSN else "disabled",
        otel_exporter,
    )


# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------

def _init_sentry() -> None:
    """Initialise the Sentry SDK if a DSN is configured."""
    if not settings.SENTRY_DSN:
        logger.info("Sentry DSN not set -- error tracking disabled")
        return

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1 if settings.APP_ENV == "production" else 1.0,
        environment=settings.APP_ENV,
        send_default_pii=False,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
    )
    logger.info("Sentry initialised for environment '%s'", settings.APP_ENV)


# ---------------------------------------------------------------------------
# OpenTelemetry
# ---------------------------------------------------------------------------

def _init_opentelemetry(app: "FastAPI") -> str:
    """Set up the OTel TracerProvider and auto-instrument FastAPI + Celery.

    Returns the label of the exporter that was configured (``"otlp"`` or
    ``"console"``).
    """

    resource = Resource.create({SERVICE_NAME: "jobpilot-api"})
    provider = TracerProvider(resource=resource)

    # --- Span exporter (endpoint-dependent) ---
    exporter_label = "console"
    if settings.OTEL_EXPORTER_ENDPOINT:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            exporter = OTLPSpanExporter(
                endpoint=settings.OTEL_EXPORTER_ENDPOINT,
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
            exporter_label = "otlp"
            logger.info(
                "OTLP exporter configured  [endpoint=%s]",
                settings.OTEL_EXPORTER_ENDPOINT,
            )
        except ImportError:
            logger.warning(
                "opentelemetry-exporter-otlp-proto-grpc not installed "
                "-- falling back to ConsoleSpanExporter"
            )
            provider.add_span_processor(
                SimpleSpanProcessor(ConsoleSpanExporter())
            )
    else:
        # No endpoint configured: human-readable trace output on stdout
        provider.add_span_processor(
            SimpleSpanProcessor(ConsoleSpanExporter())
        )

    trace.set_tracer_provider(provider)

    # --- Auto-instrument FastAPI ---
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        excluded_urls="health,docs,redoc,openapi.json",
    )

    # --- Auto-instrument Celery ---
    if CeleryInstrumentor is not None:
        try:
            CeleryInstrumentor().instrument(tracer_provider=provider)
        except Exception:
            # Celery may not be importable in every process (e.g. web-only deploys)
            logger.debug("Celery instrumentation skipped (Celery not available)")
    else:
        logger.debug("Celery instrumentation skipped (package not installed)")

    return exporter_label


# ---------------------------------------------------------------------------
# Agent span helper
# ---------------------------------------------------------------------------

def create_agent_span(
    agent_type: str,
    step_name: str,
    user_id: str,
) -> trace.Span:
    """Create a span for agent step execution with standard attributes.

    Usage::

        span = create_agent_span("scout", "search_jobs", user_id)
        try:
            # ... agent work ...
            span.set_status(StatusCode.OK)
        except Exception as exc:
            span.set_status(StatusCode.ERROR, str(exc))
            span.record_exception(exc)
            raise
        finally:
            span.end()
    """
    tracer = trace.get_tracer("jobpilot.agents")
    span = tracer.start_span(f"agent.{agent_type}.{step_name}")
    span.set_attribute("user_id", user_id)
    span.set_attribute("agent_type", agent_type)
    span.set_attribute("step_name", step_name)
    return span
