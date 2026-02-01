# Story 0.7: OpenTelemetry Tracing Setup

Status: ready-for-dev

## Story

As an **operator**,
I want **distributed tracing for all API requests and agent executions**,
so that **I can diagnose performance issues and errors**.

## Acceptance Criteria

1. **AC1 - API Request Spans:** Given OpenTelemetry is configured, when an API request is processed, then a trace span is created with request metadata.

2. **AC2 - Celery Task Spans:** Given a Celery task executes, when it runs, then child spans are created linked to the originating trace.

3. **AC3 - Agent Step Spans:** Given an agent runs steps, when each step executes, then nested spans are created with step names.

4. **AC4 - Span Attributes:** Given spans are created, when recorded, then they include: user_id, agent_type, duration, success/failure.

5. **AC5 - OTLP Export:** Given a production environment, when traces are generated, then they are exportable to an observability backend via OTLP protocol.

## Tasks / Subtasks

- [x] Task 1: Configure OTLP exporter for production (AC: #5)
  - [x] 1.1: Add `OTEL_EXPORTER_ENDPOINT` to config.py settings
  - [x] 1.2: Update tracing.py to use OTLPSpanExporter when endpoint is configured, ConsoleSpanExporter as fallback
  - [x] 1.3: Add `opentelemetry-exporter-otlp-proto-grpc` to requirements.txt

- [x] Task 2: Ensure span attributes include required metadata (AC: #3, #4)
  - [x] 2.1: Add a `create_agent_span()` helper in tracing.py that creates spans with user_id, agent_type, step_name attributes
  - [x] 2.2: Verify BaseAgent's run() method can use OTel spans for step tracking

- [x] Task 3: Write comprehensive OTel tests (AC: #1-#5)
  - [x] 3.1: Create `backend/tests/unit/test_observability/__init__.py`
  - [x] 3.2: Create `backend/tests/unit/test_observability/test_tracing.py` — test TracerProvider setup, span creation, exporter selection, instrumentation registration
  - [x] 3.3: Test span attributes include user_id, agent_type when set
  - [x] 3.4: Test OTLP exporter selected when endpoint configured, console exporter as default

## Dev Notes

### Architecture Compliance

**CRITICAL — OpenTelemetry is ALREADY SUBSTANTIALLY IMPLEMENTED:**

1. **TracerProvider EXISTS:** `backend/app/observability/tracing.py` configures TracerProvider with service name "jobpilot-api", ConsoleSpanExporter for dev.
   [Source: backend/app/observability/tracing.py:88-127]

2. **FastAPI instrumentation EXISTS:** FastAPIInstrumentor auto-instruments all routes with excluded URLs (health, docs).
   [Source: backend/app/observability/tracing.py:116-120]

3. **Celery instrumentation EXISTS:** CeleryInstrumentor with graceful fallback if not importable.
   [Source: backend/app/observability/tracing.py:123-127]

4. **Sentry integration EXISTS:** Full Sentry setup with environment-based sample rates.
   [Source: backend/app/observability/tracing.py:65-81]

5. **Langfuse agent tracing EXISTS:** Per-task traces in tasks.py with user_id, agent_type, celery_task_id.
   [Source: backend/app/worker/tasks.py]

6. **setup_observability() called in main.py:** Already wired into app lifecycle.
   [Source: backend/app/main.py:23,62]

**WHAT'S MISSING:**
- OTLP exporter for production (only ConsoleSpanExporter exists, OTLPSpanExporter is commented out)
- No OTEL_EXPORTER_ENDPOINT config setting
- No `opentelemetry-exporter-otlp-proto-grpc` in requirements.txt
- No `create_agent_span()` helper for standardized span creation with required attributes
- No tests for any observability code

### Previous Story Intelligence (0-6)

- Test pattern: mock with unittest.mock, tests in backend/tests/unit/test_<module>/
- 42 worker tests all passing
- Admin endpoints pattern established in admin.py

### Technical Requirements

**OTLP Exporter Configuration:**
```python
# In tracing.py — replace commented OTLP section:
if settings.OTEL_EXPORTER_ENDPOINT:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_ENDPOINT)
    provider.add_span_processor(BatchSpanProcessor(exporter))
else:
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
```

**Agent Span Helper:**
```python
def create_agent_span(agent_type: str, step_name: str, user_id: str) -> trace.Span:
    tracer = trace.get_tracer("jobpilot.agents")
    span = tracer.start_span(f"agent.{agent_type}.{step_name}")
    span.set_attribute("user_id", user_id)
    span.set_attribute("agent_type", agent_type)
    span.set_attribute("step_name", step_name)
    return span
```

### Library/Framework Requirements

**New dependency needed:**
```
opentelemetry-exporter-otlp-proto-grpc>=1.29.0
```

### File Structure Requirements

**Files to CREATE:**
```
backend/tests/unit/test_observability/__init__.py
backend/tests/unit/test_observability/test_tracing.py
```

**Files to MODIFY:**
```
backend/app/observability/tracing.py     # Add OTLP exporter, agent span helper
backend/app/config.py                     # Add OTEL_EXPORTER_ENDPOINT setting
backend/requirements.txt                  # Add otlp exporter package
```

**Files to NOT TOUCH:**
```
backend/app/main.py                       # Already calls setup_observability
backend/app/observability/langfuse_client.py  # Separate LLM observability
backend/app/observability/cost_tracker.py     # Separate cost tracking (story 0-8)
backend/app/worker/tasks.py               # Already has Langfuse tracing
```

### Testing Requirements

- **Backend Framework:** Pytest + pytest-asyncio
- **Mocking:** Mock OTel trace API, mock exporters
- **Tests to write:**
  - TracerProvider is configured with service name "jobpilot-api"
  - ConsoleSpanExporter used when OTEL_EXPORTER_ENDPOINT is empty
  - OTLPSpanExporter used when OTEL_EXPORTER_ENDPOINT is set
  - FastAPIInstrumentor is called during setup
  - CeleryInstrumentor is called during setup (with fallback)
  - create_agent_span creates span with correct attributes (user_id, agent_type, step_name)
  - Sentry initialized when SENTRY_DSN is set

### References

- [Source: backend/app/observability/tracing.py] — Full OTel configuration
- [Source: backend/app/observability/__init__.py] — Public API
- [Source: backend/app/main.py:23,62] — Initialization call
- [Source: backend/requirements.txt:33-36] — Current OTel packages
- [Source: backend/app/config.py] — Settings (no OTEL_EXPORTER_ENDPOINT yet)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
