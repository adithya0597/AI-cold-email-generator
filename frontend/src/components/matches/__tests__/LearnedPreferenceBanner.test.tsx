/**
 * Tests for LearnedPreferenceBanner component.
 *
 * Verifies rendering of pending suggestions, accept/dismiss functionality,
 * and hidden state when no pending preferences exist.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import type { LearnedPreference } from '../../../types/matches';

// ---------------------------------------------------------------------------
// Mock hooks
// ---------------------------------------------------------------------------

const mockMutate = vi.fn();

vi.mock('../../../services/learnedPreferences', () => ({
  useLearnedPreferences: vi.fn(),
  useUpdateLearnedPreference: vi.fn(() => ({
    mutate: mockMutate,
    isPending: false,
  })),
}));

import LearnedPreferenceBanner from '../LearnedPreferenceBanner';
import { useLearnedPreferences } from '../../../services/learnedPreferences';

const mockedUseLearnedPreferences = vi.mocked(useLearnedPreferences);

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

const pendingPrefs: LearnedPreference[] = [
  {
    id: 'pref-1',
    pattern_type: 'company',
    pattern_value: 'BadCo',
    confidence: 0.80,
    occurrences: 5,
    status: 'pending',
    created_at: '2025-07-01T10:00:00Z',
  },
  {
    id: 'pref-2',
    pattern_type: 'location',
    pattern_value: 'NYC',
    confidence: 0.75,
    occurrences: 4,
    status: 'pending',
    created_at: '2025-07-01T11:00:00Z',
  },
];

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('LearnedPreferenceBanner', () => {
  beforeEach(() => {
    mockMutate.mockClear();
  });

  it('renders pending preference suggestions', () => {
    mockedUseLearnedPreferences.mockReturnValue({
      data: pendingPrefs,
      isLoading: false,
    } as any);

    render(<LearnedPreferenceBanner />);

    expect(screen.getByTestId('learned-preference-banner')).toBeDefined();
    expect(screen.getByTestId('learned-pref-pref-1')).toBeDefined();
    expect(screen.getByTestId('learned-pref-pref-2')).toBeDefined();
    expect(screen.getByText(/dismiss jobs at BadCo/)).toBeDefined();
    expect(screen.getByText(/dismiss jobs in NYC/)).toBeDefined();
  });

  it('accept button calls mutation with acknowledged status', () => {
    mockedUseLearnedPreferences.mockReturnValue({
      data: pendingPrefs,
      isLoading: false,
    } as any);

    render(<LearnedPreferenceBanner />);

    const acceptBtn = screen.getByTestId('accept-pref-pref-1');
    fireEvent.click(acceptBtn);

    expect(mockMutate).toHaveBeenCalledWith({
      id: 'pref-1',
      status: 'acknowledged',
    });
  });

  it('dismiss button calls mutation with rejected status', () => {
    mockedUseLearnedPreferences.mockReturnValue({
      data: pendingPrefs,
      isLoading: false,
    } as any);

    render(<LearnedPreferenceBanner />);

    const dismissBtn = screen.getByTestId('dismiss-pref-pref-1');
    fireEvent.click(dismissBtn);

    expect(mockMutate).toHaveBeenCalledWith({
      id: 'pref-1',
      status: 'rejected',
    });
  });

  it('is hidden when no pending preferences', () => {
    mockedUseLearnedPreferences.mockReturnValue({
      data: [],
      isLoading: false,
    } as any);

    const { container } = render(<LearnedPreferenceBanner />);
    expect(container.innerHTML).toBe('');
  });

  it('is hidden while loading', () => {
    mockedUseLearnedPreferences.mockReturnValue({
      data: undefined,
      isLoading: true,
    } as any);

    const { container } = render(<LearnedPreferenceBanner />);
    expect(container.innerHTML).toBe('');
  });

  it('renders remote pattern description correctly', () => {
    const remotePrefs: LearnedPreference[] = [
      {
        id: 'pref-3',
        pattern_type: 'remote',
        pattern_value: 'true',
        confidence: 0.70,
        occurrences: 4,
        status: 'pending',
        created_at: '2025-07-01T12:00:00Z',
      },
    ];

    mockedUseLearnedPreferences.mockReturnValue({
      data: remotePrefs,
      isLoading: false,
    } as any);

    render(<LearnedPreferenceBanner />);
    expect(screen.getByText(/dismiss remote jobs/)).toBeDefined();
  });

  it('renders employment type pattern description correctly', () => {
    const empPrefs: LearnedPreference[] = [
      {
        id: 'pref-4',
        pattern_type: 'employment_type',
        pattern_value: 'Contract',
        confidence: 0.65,
        occurrences: 3,
        status: 'pending',
        created_at: '2025-07-01T13:00:00Z',
      },
    ];

    mockedUseLearnedPreferences.mockReturnValue({
      data: empPrefs,
      isLoading: false,
    } as any);

    render(<LearnedPreferenceBanner />);
    expect(screen.getByText(/dismiss Contract positions/)).toBeDefined();
  });
});
