/**
 * Enterprise Metrics Dashboard -- aggregate organization metrics display.
 *
 * Props-based component following the NetworkDashboard pattern.
 * No direct API calls -- data fetching is handled by the parent page.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface MetricsSummary {
  enrolled_count: number;
  active_count: number;
  jobs_reviewed_count: number;
  applications_submitted_count: number;
  interviews_scheduled_count: number;
  placements_count: number;
  placement_rate: number;
  avg_time_to_placement_days: number | null;
}

interface DailyBreakdown {
  date: string;
  applications: number;
  interviews: number;
  placements: number;
}

export interface EnterpriseMetricsDashboardProps {
  metrics?: MetricsSummary;
  dailyBreakdown?: DailyBreakdown[];
  dateRange?: { start: string; end: string };
  onDateRangeChange?: (start: string, end: string) => void;
  onExport?: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

interface MetricCardDef {
  label: string;
  key: keyof MetricsSummary;
  format: "integer" | "percent" | "days";
}

const METRIC_CARDS: MetricCardDef[] = [
  { label: "Enrolled", key: "enrolled_count", format: "integer" },
  { label: "Active", key: "active_count", format: "integer" },
  { label: "Jobs Reviewed", key: "jobs_reviewed_count", format: "integer" },
  { label: "Applications Submitted", key: "applications_submitted_count", format: "integer" },
  { label: "Interviews Scheduled", key: "interviews_scheduled_count", format: "integer" },
  { label: "Placements", key: "placements_count", format: "integer" },
  { label: "Placement Rate", key: "placement_rate", format: "percent" },
  { label: "Avg Time to Placement", key: "avg_time_to_placement_days", format: "days" },
];

function formatValue(value: number | null, format: MetricCardDef["format"]): string {
  if (value === null || value === undefined) return "N/A";
  switch (format) {
    case "integer":
      return value.toLocaleString();
    case "percent":
      return `${value.toFixed(1)}%`;
    case "days":
      return `${value.toFixed(1)} days`;
    default:
      return String(value);
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function EnterpriseMetricsDashboard({
  metrics,
  dailyBreakdown = [],
  dateRange,
  onDateRangeChange,
  onExport,
}: EnterpriseMetricsDashboardProps) {
  return (
    <div className="space-y-6">
      {/* Date Range Picker */}
      <section aria-label="Date Range" className="flex flex-wrap items-end gap-4">
        <div>
          <label
            htmlFor="metrics-start-date"
            className="block text-xs font-medium text-gray-500"
          >
            Start Date
          </label>
          <input
            id="metrics-start-date"
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
            htmlFor="metrics-end-date"
            className="block text-xs font-medium text-gray-500"
          >
            End Date
          </label>
          <input
            id="metrics-end-date"
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
          onClick={onExport}
          aria-label="Export CSV"
          className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
        >
          Export CSV
        </button>
      </section>

      {/* Metric Summary Cards */}
      <section aria-label="Metrics Summary">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Organization Metrics
        </h3>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {METRIC_CARDS.map((card) => {
            const raw = metrics ? metrics[card.key] : null;
            const value = typeof raw === "number" ? raw : null;
            return (
              <div
                key={card.key}
                aria-label={card.label}
                className="rounded-lg border border-gray-200 bg-white px-4 py-4 shadow-sm"
              >
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                  {card.label}
                </p>
                <p className="mt-1 text-2xl font-semibold text-gray-900">
                  {formatValue(value, card.format)}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Trend Chart Placeholder */}
      <section aria-label="Trend Chart">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Daily Trends
        </h3>
        <div className="flex min-h-[200px] items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50 text-sm text-gray-400">
          {dailyBreakdown.length > 0
            ? `Chart placeholder -- ${dailyBreakdown.length} data points`
            : "No trend data available"}
        </div>
      </section>
    </div>
  );
}
