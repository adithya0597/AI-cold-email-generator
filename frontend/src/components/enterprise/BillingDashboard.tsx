/**
 * Enterprise Billing Dashboard -- seat management, cost breakdown, invoices.
 *
 * Props-based component following the NetworkDashboard pattern.
 * No direct API calls -- data fetching is handled by the parent page.
 */

import { useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BillingSummary {
  seats_allocated: number;
  seats_used: number;
  seats_available: number;
  monthly_cost: number;
  cost_per_seat: number;
  billing_cycle_start: string;
  billing_cycle_end: string;
  volume_discount_percent: number;
}

interface Invoice {
  invoice_date: string;
  amount: number;
  seats: number;
  cost_per_seat: number;
  discount_percent: number;
  status: string;
  reference_id: string;
}

interface CostTrendItem {
  month: string;
  cost: number;
}

export interface BillingDashboardProps {
  summary?: BillingSummary;
  invoices?: Invoice[];
  costTrend?: CostTrendItem[];
  onUpdateSeats?: (seatCount: number) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCurrency(value: number): string {
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatDate(iso: string): string {
  if (!iso) return "N/A";
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function statusColor(status: string): string {
  switch (status.toLowerCase()) {
    case "paid":
      return "text-green-700 bg-green-50";
    case "pending":
      return "text-yellow-700 bg-yellow-50";
    case "overdue":
      return "text-red-700 bg-red-50";
    default:
      return "text-gray-700 bg-gray-50";
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function BillingDashboard({
  summary,
  invoices = [],
  costTrend = [],
  onUpdateSeats,
}: BillingDashboardProps) {
  const [seatInput, setSeatInput] = useState<number>(summary?.seats_allocated ?? 0);

  const seatsUsed = summary?.seats_used ?? 0;
  const seatsAllocated = summary?.seats_allocated ?? 0;
  const usagePercent = seatsAllocated > 0 ? Math.round((seatsUsed / seatsAllocated) * 100) : 0;

  const baseCost = (summary?.seats_allocated ?? 0) * (summary?.cost_per_seat ?? 0);
  const discountAmount = baseCost * ((summary?.volume_discount_percent ?? 0) / 100);
  const netCost = summary?.monthly_cost ?? 0;

  return (
    <div className="space-y-6">
      {/* Seats Usage Progress Bar */}
      <section aria-label="Seats Usage">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Seats Usage
        </h3>
        <div className="rounded-lg border border-gray-200 bg-white px-4 py-4 shadow-sm">
          <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
            <span>{seatsUsed} of {seatsAllocated} seats used</span>
            <span>{usagePercent}%</span>
          </div>
          <div
            className="h-3 w-full rounded-full bg-gray-200"
            role="progressbar"
            aria-valuenow={usagePercent}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Seats usage progress"
          >
            <div
              className={`h-3 rounded-full ${usagePercent > 90 ? "bg-red-500" : usagePercent > 70 ? "bg-yellow-500" : "bg-indigo-600"}`}
              style={{ width: `${Math.min(usagePercent, 100)}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-gray-400">
            {summary?.seats_available ?? 0} seats available
          </p>
        </div>
      </section>

      {/* Monthly Cost Breakdown */}
      <section aria-label="Cost Breakdown">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Monthly Cost Breakdown
        </h3>
        <div className="rounded-lg border border-gray-200 bg-white px-4 py-4 shadow-sm">
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">Base cost ({seatsAllocated} seats x {formatCurrency(summary?.cost_per_seat ?? 0)})</dt>
              <dd className="font-medium text-gray-900">{formatCurrency(baseCost)}</dd>
            </div>
            {(summary?.volume_discount_percent ?? 0) > 0 && (
              <div className="flex justify-between">
                <dt className="text-gray-500">Volume discount ({summary?.volume_discount_percent}%)</dt>
                <dd className="font-medium text-green-600">-{formatCurrency(discountAmount)}</dd>
              </div>
            )}
            <div className="flex justify-between border-t border-gray-100 pt-2">
              <dt className="font-semibold text-gray-700">Net monthly cost</dt>
              <dd className="font-semibold text-gray-900">{formatCurrency(netCost)}</dd>
            </div>
          </dl>
          <p className="mt-3 text-xs text-gray-400">
            Billing cycle: {formatDate(summary?.billing_cycle_start ?? "")} - {formatDate(summary?.billing_cycle_end ?? "")}
          </p>
        </div>
      </section>

      {/* Seat Controls */}
      <section aria-label="Seat Controls">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Manage Seats
        </h3>
        <div className="flex items-end gap-3 rounded-lg border border-gray-200 bg-white px-4 py-4 shadow-sm">
          <div>
            <label
              htmlFor="seat-count-input"
              className="block text-xs font-medium text-gray-500"
            >
              Seat Count
            </label>
            <input
              id="seat-count-input"
              type="number"
              min={1}
              aria-label="Seat count"
              className="mt-1 w-28 rounded-md border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              value={seatInput}
              onChange={(e) => setSeatInput(Number(e.target.value))}
            />
          </div>
          <button
            onClick={() => onUpdateSeats?.(seatInput)}
            aria-label="Update seats"
            className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          >
            Update Seats
          </button>
        </div>
      </section>

      {/* Invoice History Table */}
      <section aria-label="Invoice History">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Invoice History
        </h3>
        {invoices.length > 0 ? (
          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-gray-500">Date</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-500">Amount</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-500">Seats</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-500">Status</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-500">Reference</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {invoices.map((inv) => (
                  <tr key={inv.reference_id}>
                    <td className="px-4 py-2 whitespace-nowrap">{formatDate(inv.invoice_date)}</td>
                    <td className="px-4 py-2 whitespace-nowrap">{formatCurrency(inv.amount)}</td>
                    <td className="px-4 py-2 whitespace-nowrap">{inv.seats}</td>
                    <td className="px-4 py-2 whitespace-nowrap">
                      <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(inv.status)}`}>
                        {inv.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 whitespace-nowrap text-gray-400">{inv.reference_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-gray-400">No invoices yet</p>
        )}
      </section>

      {/* Cost Trend */}
      <section aria-label="Cost Trend">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Cost Trend (Last 6 Months)
        </h3>
        {costTrend.length > 0 ? (
          <ul className="space-y-1 rounded-lg border border-gray-200 bg-white px-4 py-4 shadow-sm">
            {costTrend.map((item) => (
              <li key={item.month} className="flex justify-between text-sm">
                <span className="text-gray-600">{item.month}</span>
                <span className="font-medium text-gray-900">{formatCurrency(item.cost)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-400">No cost trend data available</p>
        )}
      </section>
    </div>
  );
}
