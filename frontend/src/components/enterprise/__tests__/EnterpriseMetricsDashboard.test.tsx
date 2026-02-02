import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { EnterpriseMetricsDashboard } from "../EnterpriseMetricsDashboard";
import {
  mockSummary,
  mockDailyBreakdown,
  mockDateRange,
} from "../__fixtures__/mockMetrics";

describe("EnterpriseMetricsDashboard", () => {
  // -----------------------------------------------------------------------
  // AC6: All 8 metric cards render with values
  // -----------------------------------------------------------------------

  it("renders all 8 metric cards with correct values", () => {
    render(
      <EnterpriseMetricsDashboard
        metrics={mockSummary}
        dailyBreakdown={mockDailyBreakdown}
        dateRange={mockDateRange}
      />
    );

    // Check each metric card renders by its aria-label
    expect(screen.getByLabelText("Enrolled")).toBeInTheDocument();
    expect(screen.getByLabelText("Active")).toBeInTheDocument();
    expect(screen.getByLabelText("Jobs Reviewed")).toBeInTheDocument();
    expect(screen.getByLabelText("Applications Submitted")).toBeInTheDocument();
    expect(screen.getByLabelText("Interviews Scheduled")).toBeInTheDocument();
    expect(screen.getByLabelText("Placements")).toBeInTheDocument();
    expect(screen.getByLabelText("Placement Rate")).toBeInTheDocument();
    expect(screen.getByLabelText("Avg Time to Placement")).toBeInTheDocument();

    // Verify specific formatted values
    expect(screen.getByText("48")).toBeInTheDocument(); // enrolled_count
    expect(screen.getByText("35")).toBeInTheDocument(); // active_count
    expect(screen.getByText("1,240")).toBeInTheDocument(); // jobs_reviewed_count
    expect(screen.getByText("312")).toBeInTheDocument(); // applications_submitted_count
    expect(screen.getByText("67")).toBeInTheDocument(); // interviews_scheduled_count
    expect(screen.getByText("22")).toBeInTheDocument(); // placements_count
    expect(screen.getByText("7.0%")).toBeInTheDocument(); // placement_rate (7.05 rounds to 7.0)
    expect(screen.getByText("34.2 days")).toBeInTheDocument(); // avg_time
  });

  it("renders N/A for null avg_time_to_placement_days", () => {
    const metricsWithNull = { ...mockSummary, avg_time_to_placement_days: null };
    render(<EnterpriseMetricsDashboard metrics={metricsWithNull} />);
    expect(screen.getByText("N/A")).toBeInTheDocument();
  });

  // -----------------------------------------------------------------------
  // Date range picker renders
  // -----------------------------------------------------------------------

  it("renders date range picker with start and end inputs", () => {
    render(
      <EnterpriseMetricsDashboard
        metrics={mockSummary}
        dateRange={mockDateRange}
      />
    );

    const startInput = screen.getByLabelText("Start date");
    const endInput = screen.getByLabelText("End date");

    expect(startInput).toBeInTheDocument();
    expect(endInput).toBeInTheDocument();
    expect(startInput).toHaveValue("2026-01-01");
    expect(endInput).toHaveValue("2026-01-31");
  });

  it("calls onDateRangeChange when date inputs change", () => {
    const onDateRangeChange = vi.fn();
    render(
      <EnterpriseMetricsDashboard
        metrics={mockSummary}
        dateRange={mockDateRange}
        onDateRangeChange={onDateRangeChange}
      />
    );

    const startInput = screen.getByLabelText("Start date");
    fireEvent.change(startInput, { target: { value: "2026-02-01" } });
    expect(onDateRangeChange).toHaveBeenCalledWith("2026-02-01", "2026-01-31");
  });

  // -----------------------------------------------------------------------
  // Export button calls onExport
  // -----------------------------------------------------------------------

  it("renders export button and calls onExport when clicked", () => {
    const onExport = vi.fn();
    render(
      <EnterpriseMetricsDashboard
        metrics={mockSummary}
        onExport={onExport}
      />
    );

    const exportBtn = screen.getByLabelText("Export CSV");
    expect(exportBtn).toBeInTheDocument();

    fireEvent.click(exportBtn);
    expect(onExport).toHaveBeenCalledTimes(1);
  });

  // -----------------------------------------------------------------------
  // Trend chart placeholder
  // -----------------------------------------------------------------------

  it("renders trend chart placeholder", () => {
    render(
      <EnterpriseMetricsDashboard
        metrics={mockSummary}
        dailyBreakdown={mockDailyBreakdown}
      />
    );

    expect(screen.getByLabelText("Trend Chart")).toBeInTheDocument();
    expect(
      screen.getByText(`Chart placeholder -- ${mockDailyBreakdown.length} data points`)
    ).toBeInTheDocument();
  });

  it("shows empty state when no daily breakdown", () => {
    render(<EnterpriseMetricsDashboard metrics={mockSummary} />);
    expect(screen.getByText("No trend data available")).toBeInTheDocument();
  });
});
