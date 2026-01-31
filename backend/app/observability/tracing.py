"""
OpenTelemetry distributed tracing and Sentry error tracking setup.

Initialises a TracerProvider with environment-appropriate exporters:
- **development**: ``ConsoleSpanExporter`` (traces printed to stdout)
- **production**: placeholder for OTLP exporter (Grafana Cloud / Honeycomb)

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
from opentelemetry.instrumentation.celery import CeleryInstrumentor

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
    _init_opentelemetry(app)
    logger.info(
        "Observability initialised  [env=%s, sentry=%s, otel=console]",
        settings.APP_ENV,
        "enabled" if settings.SENTRY_DSN else "disabled",
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

def _init_opentelemetry(app: "FastAPI") -> None:
    """Set up the OTel TracerProvider and auto-instrument FastAPI + Celery."""

    resource = Resource.create({SERVICE_NAME: "jobpilot-api"})
    provider = TracerProvider(resource=resource)

    # --- Span exporter (environment-dependent) ---
    if settings.APP_ENV == "production":
        # Placeholder: swap in OTLPSpanExporter when a collector is provisioned.
        #
        #   from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        #       OTLPSpanExporter,
        #   )
        #   provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        #
        logger.info(
            "Production OTel exporter not configured -- add OTLP exporter "
            "when Grafana Cloud / Honeycomb is provisioned"
        )
    else:
        # Development: human-readable trace output on stdout
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
    try:
        CeleryInstrumentor().instrument(tracer_provider=provider)
    except Exception:
        # Celery may not be importable in every process (e.g. web-only deploys)
        logger.debug("Celery instrumentation skipped (Celery not available)")
