/**
 * k6 Performance Baseline Test Suite for JobPilot
 *
 * Scenarios:
 *   - smoke:  1 VU, 10s  — verify endpoints respond correctly
 *   - load:   10 VUs, 60s — establish p50/p95/p99 baselines
 *   - stress: 50 VUs, 120s — find saturation point
 *   - soak:   10 VUs, 10m  — check for memory leaks
 *
 * Usage:
 *   k6 run baseline.js                           # run all scenarios
 *   k6 run baseline.js --env SCENARIO=smoke      # run smoke only
 *   k6 run baseline.js --out json=results.json   # output JSON for comparison
 *
 * Environment variables:
 *   BASE_URL  — target server (default: http://localhost:8000)
 *   SCENARIO  — run specific scenario: smoke|load|stress|soak (default: all)
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// ---------------------------------------------------------------------------
// Custom metrics
// ---------------------------------------------------------------------------

const healthDuration = new Trend("health_req_duration", true);
const versionDuration = new Trend("version_req_duration", true);
const errorRate = new Rate("errors");

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const SCENARIO = __ENV.SCENARIO || "all";

function buildScenarios() {
  const scenarios = {
    smoke: {
      executor: "constant-vus",
      vus: 1,
      duration: "10s",
      tags: { scenario: "smoke" },
    },
    load: {
      executor: "constant-vus",
      vus: 10,
      duration: "60s",
      startTime: "15s",
      tags: { scenario: "load" },
    },
    stress: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: 50 },
        { duration: "60s", target: 50 },
        { duration: "30s", target: 0 },
      ],
      startTime: "80s",
      tags: { scenario: "stress" },
    },
    soak: {
      executor: "constant-vus",
      vus: 10,
      duration: "10m",
      startTime: "200s",
      tags: { scenario: "soak" },
    },
  };

  if (SCENARIO !== "all" && scenarios[SCENARIO]) {
    const selected = scenarios[SCENARIO];
    delete selected.startTime;
    return { [SCENARIO]: selected };
  }
  return scenarios;
}

export const options = {
  scenarios: buildScenarios(),
  thresholds: {
    // NFR1 targets from performance-baseline.md
    http_req_duration: ["p(95)<500"],    // API response p95 < 500ms
    health_req_duration: ["p(95)<50"],   // Health check p95 < 50ms
    http_req_failed: ["rate<0.01"],      // Error rate < 1%
    errors: ["rate<0.01"],
  },
};

// ---------------------------------------------------------------------------
// Test logic
// ---------------------------------------------------------------------------

export default function () {
  // Health endpoint
  const healthRes = http.get(`${BASE_URL}/api/v1/health`);
  healthDuration.add(healthRes.timings.duration);
  check(healthRes, {
    "health status 200": (r) => r.status === 200,
  }) || errorRate.add(1);

  sleep(0.5);

  // Version endpoint
  const versionRes = http.get(`${BASE_URL}/api/v1/version`);
  versionDuration.add(versionRes.timings.duration);
  check(versionRes, {
    "version status 200": (r) => r.status === 200,
  }) || errorRate.add(1);

  sleep(0.5);
}

// ---------------------------------------------------------------------------
// Summary output
// ---------------------------------------------------------------------------

export function handleSummary(data) {
  const summary = {
    timestamp: new Date().toISOString(),
    metrics: {
      http_req_duration_p50: data.metrics.http_req_duration?.values?.["p(50)"],
      http_req_duration_p95: data.metrics.http_req_duration?.values?.["p(95)"],
      http_req_duration_p99: data.metrics.http_req_duration?.values?.["p(99)"],
      health_req_duration_p95: data.metrics.health_req_duration?.values?.["p(95)"],
      version_req_duration_p95: data.metrics.version_req_duration?.values?.["p(95)"],
      http_req_failed_rate: data.metrics.http_req_failed?.values?.rate,
      error_rate: data.metrics.errors?.values?.rate,
      iterations: data.metrics.iterations?.values?.count,
      vus_max: data.metrics.vus_max?.values?.value,
    },
    thresholds: data.root_group?.checks
      ? Object.fromEntries(
          Object.entries(data.metrics).map(([k, v]) => [
            k,
            v.thresholds
              ? Object.fromEntries(
                  Object.entries(v.thresholds).map(([tk, tv]) => [tk, tv.ok])
                )
              : null,
          ])
        )
      : {},
  };

  return {
    stdout: JSON.stringify(summary, null, 2) + "\n",
    "results.json": JSON.stringify(summary, null, 2),
  };
}
