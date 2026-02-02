import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  ROIReportDashboard,
  type ROIReportDashboardProps,
} from '../components/enterprise/ROIReportDashboard';

const mockMetrics: NonNullable<ROIReportDashboardProps['metrics']> = {
  cost_per_placement: 8000,
  time_to_placement_days: 45.2,
  engagement_rate: 0.72,
  satisfaction_score: null,
  period: {
    start_date: '2026-01-01',
    end_date: '2026-01-31',
  },
  benchmarks: {
    cost_per_placement: {
      benchmark_value: 15000,
      comparison: 'better',
    },
    time_to_placement_days: {
      benchmark_value: 90,
      comparison: 'better',
    },
    engagement_rate: {
      benchmark_value: 0.35,
      comparison: 'better',
    },
    satisfaction_score: {
      benchmark_value: 3.5,
      comparison: 'no_data',
    },
  },
};

const defaultProps: ROIReportDashboardProps = {
  metrics: mockMetrics,
  schedule: { enabled: false, recipients: [] },
  dateRange: { start: '2026-01-01', end: '2026-01-31' },
  onDateRangeChange: vi.fn(),
  onScheduleChange: vi.fn(),
};

describe('ROIReportDashboard', () => {
  // AC5: All 4 metric cards rendered
  it('renders all four metric cards', () => {
    render(<ROIReportDashboard {...defaultProps} />);
    expect(screen.getByLabelText('Cost per Placement')).toBeInTheDocument();
    expect(screen.getByLabelText('Time to Placement')).toBeInTheDocument();
    expect(screen.getByLabelText('Engagement Rate')).toBeInTheDocument();
    expect(screen.getByLabelText('Satisfaction Score')).toBeInTheDocument();
  });

  // AC5: Metric values displayed
  it('displays formatted metric values', () => {
    render(<ROIReportDashboard {...defaultProps} />);
    expect(screen.getByText('$8,000')).toBeInTheDocument();
    expect(screen.getByText('45.2 days')).toBeInTheDocument();
    expect(screen.getByText('72.0%')).toBeInTheDocument();
    expect(screen.getByText('N/A')).toBeInTheDocument(); // satisfaction is null
  });

  // AC5: Benchmark comparison bars
  it('renders benchmark bars with correct colors', () => {
    render(<ROIReportDashboard {...defaultProps} />);
    const costBar = screen.getByTestId('benchmark-bar-cost-per-placement');
    expect(costBar).toHaveClass('bg-green-500');

    const timeBar = screen.getByTestId('benchmark-bar-time-to-placement');
    expect(timeBar).toHaveClass('bg-green-500');

    const engagementBar = screen.getByTestId('benchmark-bar-engagement-rate');
    expect(engagementBar).toHaveClass('bg-green-500');

    const satisfactionBar = screen.getByTestId('benchmark-bar-satisfaction-score');
    expect(satisfactionBar).toHaveClass('bg-gray-300'); // no_data
  });

  // AC5: Export button
  it('renders export button', () => {
    render(<ROIReportDashboard {...defaultProps} />);
    const exportBtn = screen.getByLabelText('Export report');
    expect(exportBtn).toBeInTheDocument();
    expect(exportBtn).toHaveTextContent('Export (Print)');
  });

  it('calls window.print on export click', () => {
    const printSpy = vi.spyOn(window, 'print').mockImplementation(() => {});
    render(<ROIReportDashboard {...defaultProps} />);
    fireEvent.click(screen.getByLabelText('Export report'));
    expect(printSpy).toHaveBeenCalledOnce();
    printSpy.mockRestore();
  });

  // Date range
  it('renders date range inputs with values', () => {
    render(<ROIReportDashboard {...defaultProps} />);
    const startInput = screen.getByLabelText('Start date') as HTMLInputElement;
    const endInput = screen.getByLabelText('End date') as HTMLInputElement;
    expect(startInput.value).toBe('2026-01-01');
    expect(endInput.value).toBe('2026-01-31');
  });

  it('calls onDateRangeChange when dates change', () => {
    const onDateRangeChange = vi.fn();
    render(
      <ROIReportDashboard {...defaultProps} onDateRangeChange={onDateRangeChange} />
    );
    fireEvent.change(screen.getByLabelText('Start date'), {
      target: { value: '2026-02-01' },
    });
    expect(onDateRangeChange).toHaveBeenCalledWith('2026-02-01', '2026-01-31');
  });

  // Schedule toggle
  it('renders schedule toggle', () => {
    render(<ROIReportDashboard {...defaultProps} />);
    const toggle = screen.getByLabelText('Enable monthly report');
    expect(toggle).toBeInTheDocument();
    expect(toggle).not.toBeChecked();
  });

  it('shows recipient input when schedule enabled', () => {
    render(
      <ROIReportDashboard
        {...defaultProps}
        schedule={{ enabled: true, recipients: ['admin@example.com'] }}
      />
    );
    const recipientInput = screen.getByLabelText('Schedule recipients') as HTMLInputElement;
    expect(recipientInput).toBeInTheDocument();
    expect(recipientInput.value).toBe('admin@example.com');
  });

  it('hides recipient input when schedule disabled', () => {
    render(<ROIReportDashboard {...defaultProps} />);
    expect(screen.queryByLabelText('Schedule recipients')).not.toBeInTheDocument();
  });

  // Renders without metrics (loading state)
  it('renders N/A values when no metrics provided', () => {
    render(<ROIReportDashboard />);
    const cards = screen.getAllByText('N/A');
    expect(cards.length).toBeGreaterThanOrEqual(4);
  });

  // Benchmark labels
  it('shows benchmark labels with values', () => {
    render(<ROIReportDashboard {...defaultProps} />);
    expect(screen.getByText(/Benchmark: \$15,000/)).toBeInTheDocument();
    expect(screen.getByText(/Benchmark: 90 days/)).toBeInTheDocument();
    expect(screen.getByText(/Benchmark: 35%/)).toBeInTheDocument();
  });
});
