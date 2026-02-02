import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BillingDashboard } from '../components/enterprise/BillingDashboard';

const mockSummary = {
  seats_allocated: 50,
  seats_used: 35,
  seats_available: 15,
  monthly_cost: 1125.0,
  cost_per_seat: 25.0,
  billing_cycle_start: '2026-01-01',
  billing_cycle_end: '2026-02-01',
  volume_discount_percent: 10,
};

const mockInvoices = [
  {
    invoice_date: '2026-01-15',
    amount: 1125.0,
    seats: 50,
    cost_per_seat: 25.0,
    discount_percent: 10,
    status: 'paid',
    reference_id: 'INV-12345678-20260115',
  },
  {
    invoice_date: '2025-12-15',
    amount: 1000.0,
    seats: 40,
    cost_per_seat: 25.0,
    discount_percent: 0,
    status: 'pending',
    reference_id: 'INV-12345678-20251215',
  },
];

const mockCostTrend = [
  { month: '2025-08', cost: 800.0 },
  { month: '2025-09', cost: 900.0 },
  { month: '2025-10', cost: 950.0 },
  { month: '2025-11', cost: 1000.0 },
  { month: '2025-12', cost: 1000.0 },
  { month: '2026-01', cost: 1125.0 },
];

describe('BillingDashboard', () => {
  // AC5: Seats usage progress bar
  it('renders seats usage progress bar', () => {
    render(<BillingDashboard summary={mockSummary} />);
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toBeInTheDocument();
    expect(progressBar).toHaveAttribute('aria-valuenow', '70');
    expect(screen.getByText('35 of 50 seats used')).toBeInTheDocument();
  });

  // AC5: Cost breakdown
  it('renders monthly cost breakdown', () => {
    render(<BillingDashboard summary={mockSummary} />);
    expect(screen.getByText(/Net monthly cost/i)).toBeInTheDocument();
    // Volume discount should be visible
    expect(screen.getByText(/Volume discount/i)).toBeInTheDocument();
  });

  // AC5: Seat controls
  it('renders seat management controls', () => {
    render(<BillingDashboard summary={mockSummary} />);
    expect(screen.getByLabelText('Seat count')).toBeInTheDocument();
    expect(screen.getByLabelText('Update seats')).toBeInTheDocument();
  });

  // AC5: Invoice table
  it('renders invoice history table', () => {
    render(<BillingDashboard summary={mockSummary} invoices={mockInvoices} />);
    expect(screen.getByText('INV-12345678-20260115')).toBeInTheDocument();
    expect(screen.getByText('INV-12345678-20251215')).toBeInTheDocument();
    expect(screen.getByText('paid')).toBeInTheDocument();
    expect(screen.getByText('pending')).toBeInTheDocument();
  });

  // AC6: Cost trend
  it('renders cost trend list', () => {
    render(<BillingDashboard summary={mockSummary} costTrend={mockCostTrend} />);
    expect(screen.getByText('2025-08')).toBeInTheDocument();
    expect(screen.getByText('2026-01')).toBeInTheDocument();
  });

  // Interaction: Update seats callback
  it('calls onUpdateSeats when update button is clicked', () => {
    const handler = vi.fn();
    render(<BillingDashboard summary={mockSummary} onUpdateSeats={handler} />);

    const input = screen.getByLabelText('Seat count');
    fireEvent.change(input, { target: { value: '60' } });

    const button = screen.getByLabelText('Update seats');
    fireEvent.click(button);

    expect(handler).toHaveBeenCalledWith(60);
  });

  // Empty state
  it('shows empty messages when no data provided', () => {
    render(<BillingDashboard />);
    expect(screen.getByText(/No invoices yet/i)).toBeInTheDocument();
    expect(screen.getByText(/No cost trend data available/i)).toBeInTheDocument();
  });

  // No discount row when discount is 0
  it('hides discount row when volume discount is 0', () => {
    const noDiscountSummary = { ...mockSummary, volume_discount_percent: 0 };
    render(<BillingDashboard summary={noDiscountSummary} />);
    expect(screen.queryByText(/Volume discount/i)).not.toBeInTheDocument();
  });
});
