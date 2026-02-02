/**
 * Approval Rate Chart — simple Tailwind-based bar visualization.
 *
 * Shows year-over-year approval rates and petition counts without
 * requiring a heavy charting library.
 */

export interface YearlyData {
  year: number;
  approvalRate: number;
  petitions: number;
}

interface ApprovalRateChartProps {
  data: YearlyData[];
}

function getTrend(data: YearlyData[]): 'improving' | 'declining' | 'stable' {
  if (data.length < 2) return 'stable';
  const first = data[0].approvalRate;
  const last = data[data.length - 1].approvalRate;
  const change = last - first;
  if (change > 0.10) return 'improving';
  if (change < -0.10) return 'declining';
  return 'stable';
}

function barColor(rate: number): string {
  if (rate >= 0.80) return 'bg-green-500';
  if (rate >= 0.50) return 'bg-yellow-500';
  return 'bg-red-500';
}

export function ApprovalRateChart({ data }: ApprovalRateChartProps) {
  if (data.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-center text-sm text-gray-500">
        No historical data available
      </div>
    );
  }

  const trend = getTrend(data);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-900">Approval Rate Trend</h4>
        <div className="flex items-center gap-1">
          <span
            data-testid="trend-indicator"
            className={`text-xs font-medium ${
              trend === 'improving'
                ? 'text-green-600'
                : trend === 'declining'
                ? 'text-red-600'
                : 'text-gray-500'
            }`}
          >
            {trend === 'improving' ? '↑ Improving' : trend === 'declining' ? '↓ Declining' : '→ Stable'}
          </span>
          {trend === 'declining' && (
            <span
              data-testid="trend-flag"
              className="ml-1 inline-flex items-center rounded-full bg-red-100 px-1.5 py-0.5 text-xs font-medium text-red-700"
            >
              !
            </span>
          )}
        </div>
      </div>

      <div className="space-y-2">
        {data.map((entry) => (
          <div key={entry.year} className="flex items-center gap-2">
            <span className="w-10 text-xs text-gray-500">{entry.year}</span>
            <div className="flex-1">
              <div className="h-5 w-full rounded-full bg-gray-100">
                <div
                  className={`h-5 rounded-full ${barColor(entry.approvalRate)} flex items-center justify-end pr-2`}
                  style={{ width: `${Math.max(8, Math.round(entry.approvalRate * 100))}%` }}
                >
                  <span className="text-xs font-medium text-white">
                    {Math.round(entry.approvalRate * 100)}%
                  </span>
                </div>
              </div>
            </div>
            <span className="w-10 text-right text-xs text-gray-400">{entry.petitions}</span>
          </div>
        ))}
      </div>

      <div className="mt-2 flex justify-between text-xs text-gray-400">
        <span>Approval Rate</span>
        <span>Petitions</span>
      </div>
    </div>
  );
}
