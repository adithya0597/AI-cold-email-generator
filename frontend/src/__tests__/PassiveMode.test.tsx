/**
 * Tests for Passive Mode settings (Story 6-13).
 *
 * Covers: settings render, update form, sprint activation, upgrade prompt.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import PassiveModeSettings from '../components/privacy/PassiveModeSettings';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockUpdateMutate = vi.fn();
const mockSprintMutate = vi.fn();

vi.mock('../services/privacy', async () => {
  const actual = await vi.importActual('../services/privacy');
  return {
    ...actual,
    usePassiveMode: vi.fn(() => ({
      data: {
        search_frequency: 'weekly',
        min_match_score: 70,
        notification_pref: 'weekly_digest',
        auto_save_threshold: 85,
        mode: 'passive',
        eligible: true,
        tier: 'career_insurance',
      },
      isLoading: false,
      error: null,
    })),
    useUpdatePassiveMode: vi.fn(() => ({
      mutate: mockUpdateMutate,
      isPending: false,
    })),
    useActivateSprint: vi.fn(() => ({
      mutate: mockSprintMutate,
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
// PassiveModeSettings tests
// ---------------------------------------------------------------------------

describe('PassiveModeSettings', () => {
  it('renders settings form for eligible user', () => {
    renderWithProviders(<PassiveModeSettings />);

    expect(screen.getByTestId('passive-mode-settings')).toBeTruthy();
    expect(screen.getByTestId('frequency-select')).toBeTruthy();
    expect(screen.getByTestId('match-score-slider')).toBeTruthy();
    expect(screen.getByTestId('notification-select')).toBeTruthy();
    expect(screen.getByTestId('auto-save-slider')).toBeTruthy();
    expect(screen.getByTestId('save-settings-btn')).toBeTruthy();
    expect(screen.getByTestId('sprint-btn')).toBeTruthy();
  });

  it('calls update mutation on save', () => {
    renderWithProviders(<PassiveModeSettings />);

    fireEvent.click(screen.getByTestId('save-settings-btn'));
    expect(mockUpdateMutate).toHaveBeenCalledWith({
      search_frequency: 'weekly',
      min_match_score: 70,
      notification_pref: 'weekly_digest',
      auto_save_threshold: 85,
    });
  });

  it('calls sprint mutation on sprint button click', () => {
    renderWithProviders(<PassiveModeSettings />);

    fireEvent.click(screen.getByTestId('sprint-btn'));
    expect(mockSprintMutate).toHaveBeenCalled();
  });

  it('shows upgrade prompt for ineligible user', async () => {
    const { usePassiveMode } = await import('../services/privacy');
    (usePassiveMode as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        search_frequency: 'weekly',
        min_match_score: 70,
        notification_pref: 'weekly_digest',
        auto_save_threshold: 85,
        mode: 'passive',
        eligible: false,
        tier: 'free',
      },
      isLoading: false,
      error: null,
    });

    renderWithProviders(<PassiveModeSettings />);

    expect(screen.getByTestId('passive-upgrade-prompt')).toBeTruthy();
    expect(screen.getByText(/Career Insurance or Enterprise/)).toBeTruthy();
  });

  it('shows sprint badge when in sprint mode', async () => {
    const { usePassiveMode } = await import('../services/privacy');
    (usePassiveMode as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        search_frequency: 'daily',
        min_match_score: 50,
        notification_pref: 'immediate',
        auto_save_threshold: 70,
        mode: 'sprint',
        eligible: true,
        tier: 'career_insurance',
      },
      isLoading: false,
      error: null,
    });

    renderWithProviders(<PassiveModeSettings />);

    expect(screen.getByTestId('sprint-badge')).toBeTruthy();
    expect(screen.getByText('Sprint Active')).toBeTruthy();
    // Sprint button should not show when already in sprint mode
    expect(screen.queryByTestId('sprint-btn')).toBeNull();
  });
});
