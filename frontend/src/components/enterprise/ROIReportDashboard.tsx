/**
 * ROI Report Dashboard -- enterprise program value metrics display.
 *
 * Props-based component following the EnterpriseMetricsDashboard pattern.
 * No direct API calls -- data fetching is handled by the parent page.
 * Export uses browser window.print() (no server-side PDF generation).
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BenchmarkDetail {
  benchmark_value: number;
  comparison: "better" | "at_benchmark" | "worse" | "no_data";
}

interface ROIBenchmarks {
  time_to_placement_days: BenchmarkDetail;
  cost_per_placement: BenchmarkDetail;
  engagement_rate: BenchmarkDetail;
  satisfaction_score: BenchmarkDetail;
}

interface ROIMetrics {
  cost_per_placement: number | null;
  time_to_placement_days: number | null;
  engagement_rate: number;
  satisfaction_score: number | null;
  period: {
    start_date: string;
    end_date: string;
  };
  benchmarks: ROIBenchmarks;
}

interface ScheduleConfig {
  enabled: boolean;
  recipients: string[];
}

export interface ROIReportDashboardProps {
  metrics?: ROIMetrics;
  schedule?: ScheduleConfig;
  dateRange?: { start: string; end: string };
  onDateRangeChange?: (start: string, end: string) => void;
  onScheduleChange?: (schedule: ScheduleConfig) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const COMPARISON_COLORS: Record<BenchmarkDetail["comparison"], string> = {
  better: "bg-green-500",
  at_benchmark: "bg-amber-400",
  worse: "bg-red-500",
  no_data: "bg-gray-300",
};

const COMPARISON_LABELS: Record<BenchmarkDetail["comparison"], string> = {
  better: "Better than benchmark",
  at_benchmark: "At benchmark",
  worse: "Below benchmark",
  no_data: "No data",
};

function formatCurrency(value: number | null): string {
  if (value === null || value === undefined) return "N/A";
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

function formatDays(value: number | null): string {
  if (value === null || value === undefined) return "N/A";
  return `${value.toFixed(1)} days`;
}

function formatPercent(value: number | null): string {
  if (value === null || value === undefined) return "N/A";
  return `${(value * 100).toFixed(1)}%`;
}

function formatScore(value: number | null): string {
  if (value === null || value === undefined) return "N/A";
  return `${value.toFixed(1)} / 5`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface MetricCardProps {
  label: string;
  value: string;
  benchmark?: BenchmarkDetail;
  benchmarkLabel?: string;
}

function MetricCard({ label, value, benchmark, benchmarkLabel }: MetricCardProps) {
  return (
    <div
      aria-label={label}
      className="rounded-lg border border-gray-200 bg-white px-4 py-4 shadow-sm"
    >
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
        {label}
      </p>
      <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
      {benchmark && (
        <div className="mt-3">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>{benchmarkLabel ?? `Benchmark: ${benchmark.benchmark_value}`}</span>
            <span>{COMPARISON_LABELS[benchmark.comparison]}</span>
          </div>
          <div className="mt-1 h-2 w-full rounded-full bg-gray-100">
            <div
              data-testid={`benchmark-bar-${label.toLowerCase().replace(/\s+/g, "-")}`}
              className={`h-2 rounded-full ${COMPARISON_COLORS[benchmark.comparison]}`}
              style={{ width: benchmark.comparison === "no_data" ? "0%" : "100%" }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ROIReportDashboard({
  metrics,
  schedule,
  dateRange,
  onDateRangeChange,
  onScheduleChange,
}: ROIReportDashboardProps) {
  const handleExport = () => {
    window.print();
  };

  return (
    <div className="space-y-6">
      {/* Date Range Picker */}
      <section aria-label="Date Range" className="flex flex-wrap items-end gap-4">
        <div>
          <label
            htmlFor="roi-start-date"
            className="block text-xs font-medium text-gray-500"
          >
            Start Date
          </label>
          <input
            id="roi-start-date"
            type="date"
            aria-label="Start date"
            className="mt-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            value={dateRange?.start ?? ""}
            onChange={(e) =>
              onDateRangeChange?.(e.target.value, dateRange?.end ?? "")
            }
          />
        </div>
        <div>
          <label
            htmlFor="roi-end-date"
            className="block text-xs font-medium text-gray-500"
          >
            End Date
          </label>
          <input
            id="roi-end-date"
            type="date"
            aria-label="End date"
            className="mt-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            value={dateRange?.end ?? ""}
            onChange={(e) =>
              onDateRangeChange?.(dateRange?.start ?? "", e.target.value)
            }
          />
        </div>
        <button
          onClick={handleExport}
          aria-label="Export report"
          className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 print:hidden"
        >
          Export (Print)
        </button>
      </section>

      {/* ROI Metric Cards */}
      <section aria-label="ROI Metrics">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          ROI Metrics
        </h3>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Cost per Placement"
            value={formatCurrency(metrics?.cost_per_placement ?? null)}
            benchmark={metrics?.benchmarks.cost_per_placement}
            benchmarkLabel={
              metrics
                ? `Benchmark: ${formatCurrency(metrics.benchmarks.cost_per_placement.benchmark_value)}`
                : undefined
            }
          />
          <MetricCard
            label="Time to Placement"
            value={formatDays(metrics?.time_to_placement_days ?? null)}
            benchmark={metrics?.benchmarks.time_to_placement_days}
            benchmarkLabel={
              metrics
                ? `Benchmark: ${metrics.benchmarks.time_to_placement_days.benchmark_value} days`
                : undefined
            }
          />
          <MetricCard
            label="Engagement Rate"
            value={formatPercent(metrics?.engagement_rate ?? null)}
            benchmark={metrics?.benchmarks.engagement_rate}
            benchmarkLabel={
              metrics
                ? `Benchmark: ${(metrics.benchmarks.engagement_rate.benchmark_value * 100).toFixed(0)}%`
                : undefined
            }
          />
          <MetricCard
            label="Satisfaction Score"
            value={formatScore(metrics?.satisfaction_score ?? null)}
            benchmark={metrics?.benchmarks.satisfaction_score}
            benchmarkLabel={
              metrics
                ? `Benchmark: ${metrics.benchmarks.satisfaction_score.benchmark_value} / 5`
                : undefined
            }
          />
        </div>
      </section>

      {/* Schedule Configuration */}
      <section aria-label="Report Schedule" className="print:hidden">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Monthly Report Schedule
        </h3>
        <div className="rounded-lg border border-gray-200 bg-white px-4 py-4 shadow-sm">
          <div className="flex items-center gap-3">
            <label htmlFor="schedule-toggle" className="text-sm font-medium text-gray-700">
              Enable monthly report
            </label>
            <input
              id="schedule-toggle"
              type="checkbox"
              aria-label="Enable monthly report"
              className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              checked={schedule?.enabled ?? false}
              onChange={(e) =>
                onScheduleChange?.({
                  enabled: e.target.checked,
                  recipients: schedule?.recipients ?? [],
                })
              }
            />
          </div>
          {schedule?.enabled && (
            <div className="mt-3">
              <label
                htmlFor="schedule-recipients"
                className="block text-xs font-medium text-gray-500"
              >
                Recipients (comma-separated emails)
              </label>
              <input
                id="schedule-recipients"
                type="text"
                aria-label="Schedule recipients"
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                value={schedule?.recipients.join(", ") ?? ""}
                onChange={(e) =>
                  onScheduleChange?.({
                    enabled: schedule?.enabled ?? false,
                    recipients: e.target.value
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean),
                  })
                }
              />
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
