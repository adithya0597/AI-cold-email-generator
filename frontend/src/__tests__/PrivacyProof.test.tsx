/**
 * Tests for Privacy Proof dashboard (Story 6-12).
 *
 * Covers: renders entries, blocked actions shown, download button, empty state.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import PrivacyProof from '../components/privacy/PrivacyProof';
import type { PrivacyProofResponse } from '../services/privacy';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockDownloadMutate = vi.fn();

const mockProofData: PrivacyProofResponse = {
  entries: [
    {
      company_name: 'Acme Corp',
      note: 'Current employer',
      last_checked: '2025-01-20T12:00:00+00:00',
      exposure_count: 0,
      blocked_actions: [
        {
          id: 'audit-1',
          company_name: 'Acme Corp',
          action_type: 'blocked_match',
          details: 'Blocked job match from Acme Corp',
          created_at: '2025-01-15T00:00:00+00:00',
        },
      ],
    },
  ],
  total: 1,
};

vi.mock('../services/privacy', async () => {
  const actual = await vi.importActual('../services/privacy');
  return {
    ...actual,
    usePrivacyProof: vi.fn(() => ({
      data: mockProofData,
      isLoading: false,
      error: null,
    })),
    useDownloadReport: vi.fn(() => ({
      mutate: mockDownloadMutate,
      isPending: false,
    })),
  };
});

vi.mock('../services/api', () => ({
  useApiClient: vi.fn(() => ({})),
}));

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// PrivacyProof tests
// ---------------------------------------------------------------------------

describe('PrivacyProof', () => {
  it('renders proof entries with verification data', () => {
    renderWithProviders(<PrivacyProof stealthEnabled={true} />);

    expect(screen.getByTestId('privacy-proof')).toBeTruthy();
    expect(screen.getByTestId('proof-entry-0')).toBeTruthy();
    expect(screen.getByText('Acme Corp')).toBeTruthy();
    expect(screen.getByTestId('exposure-badge-0')).toBeTruthy();
    expect(screen.getByText('0 exposures')).toBeTruthy();
    expect(screen.getByText(/Last checked:/)).toBeTruthy();
  });

  it('shows blocked actions log', () => {
    renderWithProviders(<PrivacyProof stealthEnabled={true} />);

    expect(screen.getByTestId('blocked-actions-0')).toBeTruthy();
    expect(screen.getByText('blocked_match')).toBeTruthy();
    expect(screen.getByText(/Blocked job match from Acme Corp/)).toBeTruthy();
  });

  it('renders download report button', () => {
    renderWithProviders(<PrivacyProof stealthEnabled={true} />);

    const btn = screen.getByTestId('download-report-btn');
    expect(btn).toBeTruthy();
    expect(screen.getByText('Download Report')).toBeTruthy();

    fireEvent.click(btn);
    expect(mockDownloadMutate).toHaveBeenCalled();
  });

  it('shows empty state when no entries', async () => {
    const { usePrivacyProof } = await import('../services/privacy');
    (usePrivacyProof as ReturnType<typeof vi.fn>).mockReturnValue({
      data: { entries: [], total: 0 },
      isLoading: false,
      error: null,
    });

    renderWithProviders(<PrivacyProof stealthEnabled={true} />);

    expect(screen.getByTestId('proof-empty')).toBeTruthy();
    expect(screen.getByText(/No companies blocklisted/)).toBeTruthy();
  });

  it('returns null when stealth is disabled', () => {
    const { container } = renderWithProviders(
      <PrivacyProof stealthEnabled={false} />,
    );
    expect(container.innerHTML).toBe('');
  });
});
