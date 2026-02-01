---
phase: "0"
plan: "7"
subsystem: observability
tags: [opentelemetry, tracing, otlp, sentry, otel]
depends_on: ["0-6"]
provides: ["OTLP exporter support", "create_agent_span helper", "observability test suite"]
affects: ["Phase 4+ agent tracing", "production deployment"]
tech_stack_added: ["opentelemetry-exporter-otlp-proto-grpc"]
tech_stack_patterns: ["conditional import for optional dependencies", "endpoint-driven exporter selection"]
key_files_created:
  - backend/tests/unit/test_observability/__init__.py
  - backend/tests/unit/test_observability/test_tracing.py
key_files_modified:
  - backend/app/observability/tracing.py
  - backend/app/observability/__init__.py
  - backend/app/config.py
  - backend/requirements.txt
decisions:
  - "CeleryInstrumentor import made conditional (try/except) since package not always installed locally"
  - "OTLP exporter selected by OTEL_EXPORTER_ENDPOINT setting, not APP_ENV"
  - "_init_opentelemetry returns exporter label string for dynamic log message"
metrics_duration: "~5 min"
metrics_completed: "2026-02-01"
---

# Phase 0 Plan 7: OpenTelemetry Tracing Setup Summary

OTLP exporter with endpoint-based selection, create_agent_span helper with standard attributes, 14 comprehensive tests covering all tracing paths.

## What Was Done

### Task 1: Configure OTLP exporter for production (AC#5)
- Added `OTEL_EXPORTER_ENDPOINT: str = ""` to Settings class in config.py
- Added `opentelemetry-exporter-otlp-proto-grpc>=1.29.0` to requirements.txt
- Replaced commented-out OTLP placeholder with working conditional exporter logic
- When endpoint is set: OTLPSpanExporter via BatchSpanProcessor
- When endpoint empty or import fails: ConsoleSpanExporter via SimpleSpanProcessor
- OTLP import uses try/except to avoid ImportError when package not installed locally
- Commit: `2a67c72`

### Task 2: Add create_agent_span helper (AC#3, AC#4)
- Added `create_agent_span(agent_type, step_name, user_id)` function to tracing.py
- Sets standard attributes: user_id, agent_type, step_name
- Span name format: `agent.{type}.{step}`
- Uses tracer named "jobpilot.agents"
- Exported from `app.observability` package `__init__.py`
- Commit: `4801a58`

### Task 3: Comprehensive tests (AC#1-#5)
- 14 tests covering all observability code paths
- TracerProvider configuration verified
- Exporter selection: console default, OTLP when endpoint set, fallback on import error
- FastAPI and Celery instrumentation verification
- Celery graceful fallback (raises) and skipped (not installed) paths
- Agent span: returns span, attributes set, name format, tracer name
- Sentry: init with DSN, skip without DSN
- Commit: `a7a3a07`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] CeleryInstrumentor import made conditional**
- **Found during:** Task 3
- **Issue:** `opentelemetry-instrumentation-celery` not installed locally, causing ImportError when importing `tracing.py` for testing
- **Fix:** Changed top-level `from opentelemetry.instrumentation.celery import CeleryInstrumentor` to `try/except ImportError` with `CeleryInstrumentor = None` fallback. Updated instrumentation section to check for None before calling.
- **Files modified:** backend/app/observability/tracing.py
- **Commit:** a7a3a07

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Exporter selected by OTEL_EXPORTER_ENDPOINT, not APP_ENV | More flexible -- can send traces to collector from any environment |
| CeleryInstrumentor import conditional | Package not always installed; existing try/except at call time was insufficient |
| _init_opentelemetry returns exporter label | Enables dynamic log message in setup_observability |

## Acceptance Criteria Verification

| AC | Description | Status | Evidence |
|----|-------------|--------|----------|
| AC1 | API Request Spans | PASS | FastAPIInstrumentor.instrument_app called; test_fastapi_instrumented |
| AC2 | Celery Task Spans | PASS | CeleryInstrumentor().instrument called; test_celery_instrumented |
| AC3 | Agent Step Spans | PASS | create_agent_span creates nested spans; test_create_agent_span_* |
| AC4 | Span Attributes | PASS | user_id, agent_type, step_name set; test_create_agent_span_attributes |
| AC5 | OTLP Export | PASS | OTLPSpanExporter configured when endpoint set; test_otlp_exporter_when_endpoint_set |

## Test Results

```
14 passed in 0.44s
```
