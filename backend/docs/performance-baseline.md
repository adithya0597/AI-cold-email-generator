# Performance Baseline

## Target Metrics

These are the performance targets for the JobPilot platform, established
at the end of Phase 1 (Foundation Modernization).  Actual baseline
numbers will be populated after first deployment using k6 load testing.

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Page load (FCP) | < 2 s | Lighthouse / Web Vitals |
| API response (p50) | < 200 ms | k6 / OpenTelemetry |
| API response (p95) | < 500 ms | k6 / OpenTelemetry |
| API response (p99) | < 1000 ms | k6 / OpenTelemetry |
| Agent task response | < 30 s | Celery task duration metric |
| Health check | < 50 ms | k6 |
| WebSocket connect | < 500 ms | k6 WebSocket plugin |

## Regression Policy

- **Threshold**: > 20% degradation from baseline on any p95 metric triggers CI failure
- **Implementation**: Phase 9 (Performance & Scalability)
- **Tool**: k6 with GitHub Actions integration
- **Current status**: Manual benchmarking only (not yet CI-integrated)

## Baseline Numbers

> **Status**: PENDING -- populate after Phase 1 deployment

| Endpoint | p50 | p95 | p99 | RPS |
|----------|-----|-----|-----|-----|
| GET /api/v1/health | - | - | - | - |
| GET /api/v1/users/me | - | - | - | - |
| POST /api/generate-email | - | - | - | - |
| WebSocket connect | - | - | - | - |

## Load Test Plan

When ready to establish baselines, run:

```bash
# Install k6
brew install k6  # macOS

# Run baseline test (10 VUs, 30s duration)
k6 run --vus 10 --duration 30s scripts/k6-baseline.js
```

### Test Scenarios

1. **Smoke test**: 1 VU, 10s -- verify endpoints respond correctly
2. **Load test**: 10 VUs, 60s -- establish p50/p95/p99 baselines
3. **Stress test**: 50 VUs, 120s -- find saturation point
4. **Soak test**: 10 VUs, 10m -- check for memory leaks

## Infrastructure Assumptions

- **Backend**: Single uvicorn process (4 workers in production)
- **Database**: Supabase PostgreSQL (shared infrastructure)
- **Redis**: Single instance (Upstash or Railway)
- **Frontend**: Vite static build served via CDN

## Notes

- LLM-dependent endpoints (email generation, post generation) are excluded
  from strict latency targets as they depend on external API response times
- Agent tasks (Celery) have a 30s target but 240s soft timeout for complex
  multi-step operations
- WebSocket latency is measured as time-to-first-message after connection
