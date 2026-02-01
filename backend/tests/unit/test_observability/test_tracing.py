"""Tests for app.observability.tracing module.

Covers TracerProvider configuration, exporter selection (Console vs OTLP),
FastAPI/Celery instrumentation, Sentry initialisation, and the
create_agent_span helper.

All tests use unittest.mock -- no real OTel collector or Sentry DSN required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_app() -> MagicMock:
    """Return a minimal mock FastAPI application."""
    return MagicMock()


def _make_mock_settings(**overrides):
    """Return a mock Settings object with sensible defaults."""
    defaults = {
        "APP_ENV": "development",
        "SENTRY_DSN": "",
        "OTEL_EXPORTER_ENDPOINT": "",
    }
    defaults.update(overrides)
    mock_settings = MagicMock()
    for key, value in defaults.items():
        setattr(mock_settings, key, value)
    return mock_settings


# ---------------------------------------------------------------------------
# TracerProvider tests
# ---------------------------------------------------------------------------

class TestTracerProviderSetup:
    """Verify TracerProvider is configured during setup."""

    @patch("app.observability.tracing.CeleryInstrumentor", new=MagicMock())
    @patch("app.observability.tracing.FastAPIInstrumentor")
    @patch("app.observability.tracing.sentry_sdk")
    @patch(
        "app.observability.tracing.settings",
        _make_mock_settings(),
    )
    def test_tracer_provider_configured(
        self, mock_sentry, mock_fastapi_instr
    ):
        """After setup_observability, a TracerProvider should be set."""
        from app.observability.tracing import setup_observability

        app = _make_mock_app()
        setup_observability(app)

        provider = trace.get_tracer_provider()
        assert isinstance(provider, TracerProvider)


# ---------------------------------------------------------------------------
# Exporter selection tests
# ---------------------------------------------------------------------------

class TestExporterSelection:
    """Verify correct exporter is chosen based on OTEL_EXPORTER_ENDPOINT."""

    @patch("app.observability.tracing.CeleryInstrumentor", new=MagicMock())
    @patch("app.observability.tracing.FastAPIInstrumentor")
    @patch("app.observability.tracing.sentry_sdk")
    @patch("app.observability.tracing.SimpleSpanProcessor")
    @patch("app.observability.tracing.ConsoleSpanExporter")
    @patch(
        "app.observability.tracing.settings",
        _make_mock_settings(),
    )
    def test_console_exporter_when_no_endpoint(
        self,
        mock_console_cls,
        mock_simple_proc,
        mock_sentry,
        mock_fastapi_instr,
    ):
        """When OTEL_EXPORTER_ENDPOINT is empty, ConsoleSpanExporter is used."""
        from app.observability.tracing import setup_observability

        app = _make_mock_app()
        setup_observability(app)

        mock_console_cls.assert_called()
        mock_simple_proc.assert_called()

    @patch("app.observability.tracing.CeleryInstrumentor", new=MagicMock())
    @patch("app.observability.tracing.FastAPIInstrumentor")
    @patch("app.observability.tracing.sentry_sdk")
    @patch("app.observability.tracing.BatchSpanProcessor")
    @patch(
        "app.observability.tracing.settings",
        _make_mock_settings(OTEL_EXPORTER_ENDPOINT="http://localhost:4317"),
    )
    def test_otlp_exporter_when_endpoint_set(
        self,
        mock_batch_proc,
        mock_sentry,
        mock_fastapi_instr,
    ):
        """When OTEL_EXPORTER_ENDPOINT is set, OTLPSpanExporter is used."""
        mock_otlp_cls = MagicMock()
        mock_otlp_exporter = MagicMock()
        mock_otlp_cls.return_value = mock_otlp_exporter

        otlp_module = MagicMock(OTLPSpanExporter=mock_otlp_cls)
        with patch.dict(
            "sys.modules",
            {"opentelemetry.exporter.otlp.proto.grpc.trace_exporter": otlp_module},
        ):
            from app.observability.tracing import setup_observability

            app = _make_mock_app()
            setup_observability(app)

            mock_otlp_cls.assert_called_once_with(
                endpoint="http://localhost:4317"
            )
            mock_batch_proc.assert_called_once_with(mock_otlp_exporter)

    @patch("app.observability.tracing.CeleryInstrumentor", new=MagicMock())
    @patch("app.observability.tracing.FastAPIInstrumentor")
    @patch("app.observability.tracing.sentry_sdk")
    @patch("app.observability.tracing.SimpleSpanProcessor")
    @patch("app.observability.tracing.ConsoleSpanExporter")
    @patch(
        "app.observability.tracing.settings",
        _make_mock_settings(OTEL_EXPORTER_ENDPOINT="http://localhost:4317"),
    )
    def test_console_fallback_when_otlp_import_fails(
        self,
        mock_console_cls,
        mock_simple_proc,
        mock_sentry,
        mock_fastapi_instr,
    ):
        """When OTLP import fails, ConsoleSpanExporter is used as fallback."""
        with patch.dict(
            "sys.modules",
            {"opentelemetry.exporter.otlp.proto.grpc.trace_exporter": None},
        ):
            from app.observability.tracing import setup_observability

            app = _make_mock_app()
            setup_observability(app)

            mock_console_cls.assert_called()
            mock_simple_proc.assert_called()


# ---------------------------------------------------------------------------
# Instrumentation tests
# ---------------------------------------------------------------------------

class TestInstrumentation:
    """Verify FastAPI and Celery auto-instrumentation."""

    @patch("app.observability.tracing.CeleryInstrumentor", new=MagicMock())
    @patch("app.observability.tracing.FastAPIInstrumentor")
    @patch("app.observability.tracing.sentry_sdk")
    @patch(
        "app.observability.tracing.settings",
        _make_mock_settings(),
    )
    def test_fastapi_instrumented(
        self, mock_sentry, mock_fastapi_instr
    ):
        """FastAPIInstrumentor.instrument_app is called during setup."""
        from app.observability.tracing import setup_observability

        app = _make_mock_app()
        setup_observability(app)

        mock_fastapi_instr.instrument_app.assert_called_once()
        call_args = mock_fastapi_instr.instrument_app.call_args
        assert call_args[0][0] is app

    @patch("app.observability.tracing.FastAPIInstrumentor")
    @patch("app.observability.tracing.sentry_sdk")
    @patch(
        "app.observability.tracing.settings",
        _make_mock_settings(),
    )
    def test_celery_instrumented(
        self, mock_sentry, mock_fastapi_instr
    ):
        """CeleryInstrumentor().instrument is called during setup."""
        mock_celery_cls = MagicMock()
        with patch("app.observability.tracing.CeleryInstrumentor", mock_celery_cls):
            from app.observability.tracing import setup_observability

            app = _make_mock_app()
            setup_observability(app)

            mock_celery_cls.return_value.instrument.assert_called_once()

    @patch("app.observability.tracing.FastAPIInstrumentor")
    @patch("app.observability.tracing.sentry_sdk")
    @patch(
        "app.observability.tracing.settings",
        _make_mock_settings(),
    )
    def test_celery_graceful_fallback(
        self, mock_sentry, mock_fastapi_instr
    ):
        """If CeleryInstrumentor raises, setup still completes without error."""
        mock_celery_cls = MagicMock()
        mock_celery_cls.return_value.instrument.side_effect = RuntimeError("boom")

        with patch("app.observability.tracing.CeleryInstrumentor", mock_celery_cls):
            from app.observability.tracing import setup_observability

            app = _make_mock_app()
            # Should NOT raise
            setup_observability(app)

            # FastAPI instrumentation should still have been called
            mock_fastapi_instr.instrument_app.assert_called_once()

    @patch("app.observability.tracing.FastAPIInstrumentor")
    @patch("app.observability.tracing.sentry_sdk")
    @patch(
        "app.observability.tracing.settings",
        _make_mock_settings(),
    )
    def test_celery_skipped_when_not_installed(
        self, mock_sentry, mock_fastapi_instr
    ):
        """When CeleryInstrumentor is None (not installed), setup completes."""
        with patch("app.observability.tracing.CeleryInstrumentor", None):
            from app.observability.tracing import setup_observability

            app = _make_mock_app()
            # Should NOT raise
            setup_observability(app)

            mock_fastapi_instr.instrument_app.assert_called_once()


# ---------------------------------------------------------------------------
# Agent span tests
# ---------------------------------------------------------------------------

class TestCreateAgentSpan:
    """Verify create_agent_span helper."""

    def test_create_agent_span_returns_span(self):
        """create_agent_span returns an object with span-like interface."""
        from app.observability.tracing import create_agent_span

        span = create_agent_span("scout", "search_jobs", "user-123")
        try:
            assert span is not None
            assert hasattr(span, "set_attribute")
            assert hasattr(span, "end")
        finally:
            span.end()

    def test_create_agent_span_attributes(self):
        """create_agent_span sets user_id, agent_type, step_name attributes."""
        with patch("app.observability.tracing.trace") as mock_trace:
            mock_tracer = MagicMock()
            mock_span = MagicMock()
            mock_trace.get_tracer.return_value = mock_tracer
            mock_tracer.start_span.return_value = mock_span

            from app.observability.tracing import create_agent_span

            create_agent_span("scout", "search_jobs", "user-456")

            mock_span.set_attribute.assert_any_call("user_id", "user-456")
            mock_span.set_attribute.assert_any_call("agent_type", "scout")
            mock_span.set_attribute.assert_any_call("step_name", "search_jobs")

    def test_create_agent_span_name_format(self):
        """Span name follows agent.{type}.{step} format."""
        with patch("app.observability.tracing.trace") as mock_trace:
            mock_tracer = MagicMock()
            mock_trace.get_tracer.return_value = mock_tracer

            from app.observability.tracing import create_agent_span

            create_agent_span("apply", "submit_application", "user-789")

            mock_tracer.start_span.assert_called_once_with(
                "agent.apply.submit_application"
            )

    def test_create_agent_span_uses_correct_tracer_name(self):
        """Tracer is obtained with name 'jobpilot.agents'."""
        with patch("app.observability.tracing.trace") as mock_trace:
            mock_tracer = MagicMock()
            mock_trace.get_tracer.return_value = mock_tracer

            from app.observability.tracing import create_agent_span

            create_agent_span("scout", "step", "user")

            mock_trace.get_tracer.assert_called_with("jobpilot.agents")


# ---------------------------------------------------------------------------
# Sentry tests
# ---------------------------------------------------------------------------

class TestSentryInitialisation:
    """Verify Sentry SDK initialisation behaviour."""

    @patch("app.observability.tracing.CeleryInstrumentor", new=MagicMock())
    @patch("app.observability.tracing.FastAPIInstrumentor")
    @patch("app.observability.tracing.sentry_sdk")
    @patch(
        "app.observability.tracing.settings",
        _make_mock_settings(
            SENTRY_DSN="https://examplePublicKey@o0.ingest.sentry.io/0"
        ),
    )
    def test_sentry_initialized_with_dsn(
        self, mock_sentry, mock_fastapi_instr
    ):
        """When SENTRY_DSN is set, sentry_sdk.init is called."""
        from app.observability.tracing import setup_observability

        app = _make_mock_app()
        setup_observability(app)

        mock_sentry.init.assert_called_once()
        call_kwargs = mock_sentry.init.call_args[1]
        assert call_kwargs["dsn"] == "https://examplePublicKey@o0.ingest.sentry.io/0"

    @patch("app.observability.tracing.CeleryInstrumentor", new=MagicMock())
    @patch("app.observability.tracing.FastAPIInstrumentor")
    @patch("app.observability.tracing.sentry_sdk")
    @patch(
        "app.observability.tracing.settings",
        _make_mock_settings(),
    )
    def test_sentry_skipped_without_dsn(
        self, mock_sentry, mock_fastapi_instr
    ):
        """When SENTRY_DSN is empty, sentry_sdk.init is NOT called."""
        from app.observability.tracing import setup_observability

        app = _make_mock_app()
        setup_observability(app)

        mock_sentry.init.assert_not_called()
