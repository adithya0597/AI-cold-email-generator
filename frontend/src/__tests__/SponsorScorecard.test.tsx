import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SponsorScorecard, calculateGrade } from '../components/h1b/SponsorScorecard';

// Mock the h1b service
vi.mock('../services/h1b', () => ({
  useSponsorData: vi.fn(),
}));

import { useSponsorData } from '../services/h1b';
const mockUseSponsorData = vi.mocked(useSponsorData);

describe('calculateGrade', () => {
  it('returns A+ for ≥95%', () => {
    expect(calculateGrade(0.96)).toBe('A+');
  });

  it('returns A for ≥90%', () => {
    expect(calculateGrade(0.92)).toBe('A');
  });

  it('returns B+ for ≥85%', () => {
    expect(calculateGrade(0.87)).toBe('B+');
  });

  it('returns B for ≥80%', () => {
    expect(calculateGrade(0.82)).toBe('B');
  });

  it('returns C for ≥70%', () => {
    expect(calculateGrade(0.73)).toBe('C');
  });

  it('returns D for ≥50%', () => {
    expect(calculateGrade(0.55)).toBe('D');
  });

  it('returns F for <50%', () => {
    expect(calculateGrade(0.30)).toBe('F');
  });

  it('returns F for null', () => {
    expect(calculateGrade(null)).toBe('F');
  });
});

describe('SponsorScorecard', () => {
  it('renders all sponsor fields', () => {
    mockUseSponsorData.mockReturnValue({
      data: {
        company_name: 'Google LLC',
        total_petitions: 500,
        approval_rate: 0.95,
        avg_wage: 150000,
        freshness: {
          h1bgrader: '2025-01-15T00:00:00Z',
          myvisajobs: '2025-01-14T00:00:00Z',
          uscis: '2025-01-13T00:00:00Z',
        },
        updated_at: '2025-01-15T00:00:00Z',
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as any);

    render(<SponsorScorecard company="Google" />);

    expect(screen.getByTestId('sponsor-grade')).toHaveTextContent('A+');
    expect(screen.getByTestId('approval-rate')).toHaveTextContent('95');
    expect(screen.getByTestId('petition-count')).toHaveTextContent('500');
    expect(screen.getByTestId('avg-wage')).toHaveTextContent('150,000');
    expect(screen.getByText(/Data last updated/i)).toBeInTheDocument();
  });

  it('shows skeleton loader when loading', () => {
    mockUseSponsorData.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    } as any);

    render(<SponsorScorecard company="Google" />);

    expect(screen.getByTestId('scorecard-skeleton')).toBeInTheDocument();
  });

  it('shows error state with retry', () => {
    const mockRefetch = vi.fn();
    mockUseSponsorData.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch: mockRefetch,
    } as any);

    render(<SponsorScorecard company="Google" />);

    expect(screen.getByText(/Failed to load/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('shows scoring methodology', () => {
    mockUseSponsorData.mockReturnValue({
      data: {
        company_name: 'Test Corp',
        total_petitions: 10,
        approval_rate: 0.50,
        avg_wage: null,
        freshness: {},
        updated_at: null,
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as any);

    render(<SponsorScorecard company="Test" />);

    expect(screen.getByText(/Scoring Methodology/i)).toBeInTheDocument();
  });
});
