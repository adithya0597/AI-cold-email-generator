#!/usr/bin/env bash
# check-regression.sh — Compare k6 results against stored baselines
#
# Usage:
#   ./check-regression.sh results.json [baseline.json]
#
# Exits non-zero if any p95 metric degrades >20% from baseline.
# If no baseline file exists, prints a warning and exits 0 (first run).

set -euo pipefail

RESULTS_FILE="${1:-results.json}"
BASELINE_FILE="${2:-baseline.json}"
REGRESSION_THRESHOLD="${REGRESSION_THRESHOLD:-20}"

if [[ ! -f "$RESULTS_FILE" ]]; then
  echo "ERROR: Results file not found: $RESULTS_FILE"
  exit 1
fi

if [[ ! -f "$BASELINE_FILE" ]]; then
  echo "WARN: No baseline file found at $BASELINE_FILE"
  echo "      This appears to be the first run. Saving current results as baseline."
  cp "$RESULTS_FILE" "$BASELINE_FILE"
  exit 0
fi

echo "=== Performance Regression Check ==="
echo "Threshold: >${REGRESSION_THRESHOLD}% degradation triggers failure"
echo ""

FAILED=0

# Compare p95 metrics
for METRIC in http_req_duration_p95 health_req_duration_p95 version_req_duration_p95; do
  CURRENT=$(python3 -c "
import json, sys
with open('$RESULTS_FILE') as f:
    d = json.load(f)
v = d.get('metrics', {}).get('$METRIC')
print(v if v is not None else 'null')
")

  BASELINE=$(python3 -c "
import json, sys
with open('$BASELINE_FILE') as f:
    d = json.load(f)
v = d.get('metrics', {}).get('$METRIC')
print(v if v is not None else 'null')
")

  if [[ "$CURRENT" == "null" ]] || [[ "$BASELINE" == "null" ]]; then
    echo "  SKIP  $METRIC (no data)"
    continue
  fi

  REGRESSION=$(python3 -c "
baseline = $BASELINE
current = $CURRENT
if baseline > 0:
    pct = ((current - baseline) / baseline) * 100
    print(f'{pct:.1f}')
else:
    print('0.0')
")

  IS_FAIL=$(python3 -c "print('FAIL' if $REGRESSION > $REGRESSION_THRESHOLD else 'PASS')")

  if [[ "$IS_FAIL" == "FAIL" ]]; then
    echo "  FAIL  $METRIC: ${CURRENT}ms vs baseline ${BASELINE}ms (+${REGRESSION}%)"
    FAILED=1
  else
    echo "  PASS  $METRIC: ${CURRENT}ms vs baseline ${BASELINE}ms (${REGRESSION}%)"
  fi
done

echo ""

if [[ "$FAILED" -eq 1 ]]; then
  echo "RESULT: REGRESSION DETECTED — one or more metrics exceeded ${REGRESSION_THRESHOLD}% threshold"
  exit 1
else
  echo "RESULT: ALL CLEAR — no regressions detected"
  exit 0
fi
