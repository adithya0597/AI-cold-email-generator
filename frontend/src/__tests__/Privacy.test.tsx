/**
 * Tests for Privacy/Stealth Mode UI (Story 6-10).
 *
 * Covers: toggle renders, disabled when ineligible, explanation shown,
 * badge visible when active, upgrade prompt shown.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import Privacy from '../pages/Privacy';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockMutate = vi.fn();

vi.mock('../services/privacy', async () => {
  const actual = await vi.importActual('../services/privacy');
  return {
    ...actual,
    useStealthStatus: vi.fn(() => ({
      data: {
        stealth_enabled: false,
        tier: 'career_insurance',
        eligible: true,
      },
      isLoading: false,
      error: null,
    })),
    useToggleStealth: vi.fn(() => ({
      mutate: mockMutate,
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
// Privacy page tests
// ---------------------------------------------------------------------------

describe('Privacy page', () => {
  it('renders stealth mode toggle', () => {
    renderWithProviders(<Privacy />);

    expect(screen.getByText('Stealth Mode')).toBeTruthy();
    expect(screen.getByTestId('stealth-toggle')).toBeTruthy();
  });

  it('toggle is enabled for eligible user', () => {
    renderWithProviders(<Privacy />);

    const toggle = screen.getByTestId('stealth-toggle');
    expect(toggle).not.toBeDisabled();
  });

  it('calls toggleStealth on click', () => {
    renderWithProviders(<Privacy />);

    fireEvent.click(screen.getByTestId('stealth-toggle'));
    expect(mockMutate).toHaveBeenCalledWith({ enabled: true });
  });

  it('shows upgrade prompt when ineligible', async () => {
    const { useStealthStatus } = await import('../services/privacy');
    (useStealthStatus as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        stealth_enabled: false,
        tier: 'free',
        eligible: false,
      },
      isLoading: false,
      error: null,
    });

    renderWithProviders(<Privacy />);

    expect(screen.getByTestId('upgrade-prompt')).toBeTruthy();
    expect(screen.getByText(/Career Insurance or Enterprise/)).toBeTruthy();

    const toggle = screen.getByTestId('stealth-toggle');
    expect(toggle).toBeDisabled();
  });

  it('shows explanation when stealth is enabled', async () => {
    const { useStealthStatus } = await import('../services/privacy');
    (useStealthStatus as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        stealth_enabled: true,
        tier: 'career_insurance',
        eligible: true,
      },
      isLoading: false,
      error: null,
    });

    renderWithProviders(<Privacy />);

    expect(screen.getByTestId('stealth-explanation')).toBeTruthy();
    expect(screen.getByText(/profile is hidden from public search/)).toBeTruthy();
    expect(screen.getByText(/Employer blocklist is activated/)).toBeTruthy();
    expect(screen.getByText(/agent actions avoid public visibility/)).toBeTruthy();
  });

  it('does not show explanation when stealth is disabled', async () => {
    const { useStealthStatus } = await import('../services/privacy');
    (useStealthStatus as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        stealth_enabled: false,
        tier: 'career_insurance',
        eligible: true,
      },
      isLoading: false,
      error: null,
    });

    renderWithProviders(<Privacy />);

    expect(screen.queryByTestId('stealth-explanation')).toBeNull();
  });

  it('does not call mutate when ineligible user clicks toggle', async () => {
    const { useStealthStatus } = await import('../services/privacy');
    (useStealthStatus as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        stealth_enabled: false,
        tier: 'free',
        eligible: false,
      },
      isLoading: false,
      error: null,
    });

    renderWithProviders(<Privacy />);

    fireEvent.click(screen.getByTestId('stealth-toggle'));
    expect(mockMutate).not.toHaveBeenCalled();
  });
});
