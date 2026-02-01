# Story 0.14: Performance Baseline Establishment

Status: review

## Story

As an **operator**,
I want **performance baselines established and monitored**,
so that **I can detect regressions and verify NFR1 targets**.

## Acceptance Criteria

1. **AC1 - Baseline Metrics Captured:** Given the application endpoints exist, when k6 load test scripts run, then baseline metrics are captured for: page load (<2s), API response p95 (<500ms), agent response (<30s).

2. **AC2 - k6 Test Scripts:** Given k6 is available, when test scripts are executed, then smoke, load, stress, and soak test scenarios are available.

3. **AC3 - Baselines Stored:** Given k6 runs complete, when baselines are captured, then results are stored in a structured format for future comparison.

4. **AC4 - CI Performance Check:** Given the CI pipeline exists, when a performance job is added, then the pipeline includes a performance regression check step (placeholder for post-deployment).

5. **AC5 - Regression Threshold:** Given baseline metrics exist, when a metric degrades >20% from baseline, then the CI check reports failure.

## Tasks / Subtasks

- [x] Task 1: Create k6 load test scripts (AC: #1, #2)
  - [x] 1.1: Create `backend/scripts/k6/baseline.js` with smoke, load, stress, soak scenarios
  - [x] 1.2: Script targets: GET /api/v1/health, GET /api/v1/version, WebSocket connection
  - [x] 1.3: Script outputs structured JSON results for baseline comparison

- [x] Task 2: Add CI performance job placeholder (AC: #4, #5)
  - [x] 2.1: Add `performance-check` job to `.github/workflows/ci.yml` (runs after backend-test)
  - [x] 2.2: Job installs k6 and runs smoke test in dry-run mode (no live server needed)
  - [x] 2.3: Add threshold configuration for 20% regression detection
  - [x] 2.4: Job is allowed to fail (continue-on-error: true) until baselines are populated

- [x] Task 3: Create baseline comparison script (AC: #3, #5)
  - [x] 3.1: Create `backend/scripts/k6/check-regression.sh` that compares k6 JSON output against stored baselines
  - [x] 3.2: Script exits non-zero if any p95 metric degrades >20%

## Dev Notes

### Architecture Compliance

**CRITICAL — Performance baseline doc ALREADY EXISTS:**

1. **performance-baseline.md EXISTS:** `backend/docs/performance-baseline.md` with:
   - Target metrics table (FCP <2s, API p95 <500ms, agent <30s)
   - Regression policy: >20% degradation triggers CI failure
   - Load test plan with 4 scenarios (smoke, load, stress, soak)
   - Baseline numbers table (PENDING — needs population after deployment)
   [Source: backend/docs/performance-baseline.md]

2. **pytest markers EXIST:** `performance` marker in pytest.ini
   [Source: backend/pytest.ini]

3. **CI pipeline EXISTS:** `.github/workflows/ci.yml` — no performance job yet
   [Source: .github/workflows/ci.yml]

**WHAT'S MISSING:**
- No k6 test scripts
- No CI performance job
- No baseline comparison/regression detection script
- No infrastructure/load-tests directory

### Previous Story Intelligence (0-13)

- 14 storage tests passing
- All 363 unit tests passing (plus 2 pre-existing failures, 2 pre-existing errors)
- CI pipeline already has backend-test, frontend-test, contract-test, deploy jobs
- Clean simple implementations working well

### Technical Requirements

**k6 script structure:**
k6 scripts are JavaScript modules. The baseline script should define scenarios:
```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    smoke: { executor: 'constant-vus', vus: 1, duration: '10s' },
    load: { executor: 'constant-vus', vus: 10, duration: '60s', startTime: '15s' },
  },
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};
```

**CI integration:**
k6 can be installed via GitHub Actions:
```yaml
- name: Install k6
  run: |
    curl -sSL https://dl.k6.io/key.gpg | sudo gpg --dearmor -o /etc/apt/keyrings/k6.gpg
    echo "deb [signed-by=/etc/apt/keyrings/k6.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
    sudo apt-get update && sudo apt-get install -y k6
```

For this story, the CI job is a **placeholder** since we don't have a live staging environment yet. It validates that the k6 scripts are syntactically correct.

**Regression check:** Compare current k6 JSON results against `backend/docs/performance-baseline.md` baselines. Since baselines are PENDING, the check script should gracefully handle missing baselines.

### Library/Framework Requirements

**No new Python dependencies needed.** k6 is a standalone binary (not a Python package).

### File Structure Requirements

**Files to CREATE:**
```
backend/scripts/k6/baseline.js
backend/scripts/k6/check-regression.sh
```

**Files to MODIFY:**
```
.github/workflows/ci.yml                  # Add performance-check job
```

**Files to NOT TOUCH:**
```
backend/docs/performance-baseline.md       # Already complete with targets
backend/pytest.ini                         # Performance marker already defined
```

### Testing Requirements

This story is infrastructure/tooling. The "tests" are:
- k6 scripts validate syntactically (k6 inspect)
- CI job runs without errors (even if no live server)
- Regression check script handles missing baselines gracefully

### References

- [Source: backend/docs/performance-baseline.md] — Performance targets and baseline doc
- [Source: .github/workflows/ci.yml] — Existing CI pipeline
- [Source: backend/pytest.ini] — Performance test marker

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
SIMPLE (score: 3/16) — direct execution, no GSD subagents

### Debug Log References
None — clean implementation

### Completion Notes List
- Created k6 baseline.js with 4 scenarios (smoke, load, stress, soak) and NFR1 thresholds
- k6 script targets health and version endpoints with custom metrics
- handleSummary outputs structured JSON for baseline comparison
- Created check-regression.sh that compares p95 metrics with 20% threshold
- Added performance-check CI job with k6 install, script validation, continue-on-error
- Baselines PENDING until first staging deployment

### Change Log
- 2026-02-01: Created k6 scripts, regression checker, CI performance job

### File List
**Created:**
- `backend/scripts/k6/baseline.js`
- `backend/scripts/k6/check-regression.sh`

**Modified:**
- `.github/workflows/ci.yml` — added performance-check job
