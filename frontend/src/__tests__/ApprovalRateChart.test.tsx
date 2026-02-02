import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ApprovalRateChart, type YearlyData } from '../components/h1b/ApprovalRateChart';

describe('ApprovalRateChart', () => {
  const sampleData: YearlyData[] = [
    { year: 2020, approvalRate: 0.70, petitions: 100 },
    { year: 2021, approvalRate: 0.75, petitions: 120 },
    { year: 2022, approvalRate: 0.80, petitions: 150 },
    { year: 2023, approvalRate: 0.88, petitions: 180 },
    { year: 2024, approvalRate: 0.95, petitions: 200 },
  ];

  it('renders data points for each year', () => {
    render(<ApprovalRateChart data={sampleData} />);

    expect(screen.getByText('2020')).toBeInTheDocument();
    expect(screen.getByText('2024')).toBeInTheDocument();
    expect(screen.getByText('95%')).toBeInTheDocument();
  });

  it('shows increasing trend indicator for improving rates', () => {
    render(<ApprovalRateChart data={sampleData} />);

    expect(screen.getByTestId('trend-indicator')).toHaveTextContent(/improving|↑/i);
  });

  it('shows red flag for declining rates', () => {
    const declining: YearlyData[] = [
      { year: 2022, approvalRate: 0.90, petitions: 150 },
      { year: 2023, approvalRate: 0.70, petitions: 120 },
      { year: 2024, approvalRate: 0.50, petitions: 80 },
    ];

    render(<ApprovalRateChart data={declining} />);

    expect(screen.getByTestId('trend-indicator')).toHaveTextContent(/declining|↓/i);
    expect(screen.getByTestId('trend-flag')).toBeInTheDocument();
  });

  it('shows message for empty data', () => {
    render(<ApprovalRateChart data={[]} />);

    expect(screen.getByText(/no historical data/i)).toBeInTheDocument();
  });

  it('shows petition counts', () => {
    render(<ApprovalRateChart data={sampleData} />);

    expect(screen.getByText('200')).toBeInTheDocument();
  });
});
