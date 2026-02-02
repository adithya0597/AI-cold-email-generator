/**
 * Tests for Employer Blocklist UI (Story 6-11).
 *
 * Covers: renders entries, add company, remove company, stealth-required message.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import BlocklistManager from '../components/privacy/BlocklistManager';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockAddMutate = vi.fn();
const mockRemoveMutate = vi.fn();

const mockBlocklistData = {
  entries: [
    {
      id: 'entry-1',
      company_name: 'Acme Corp',
      note: 'Current employer',
      created_at: '2025-01-15T00:00:00+00:00',
    },
    {
      id: 'entry-2',
      company_name: 'Evil Inc',
      note: null,
      created_at: '2025-01-20T00:00:00+00:00',
    },
  ],
  total: 2,
};

vi.mock('../services/privacy', async () => {
  const actual = await vi.importActual('../services/privacy');
  return {
    ...actual,
    useBlocklist: vi.fn(() => ({
      data: mockBlocklistData,
      isLoading: false,
      error: null,
    })),
    useAddToBlocklist: vi.fn(() => ({
      mutate: mockAddMutate,
      isPending: false,
    })),
    useRemoveFromBlocklist: vi.fn(() => ({
      mutate: mockRemoveMutate,
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
// BlocklistManager tests
// ---------------------------------------------------------------------------

describe('BlocklistManager', () => {
  it('renders blocklist entries when stealth is enabled', () => {
    renderWithProviders(<BlocklistManager stealthEnabled={true} />);

    expect(screen.getByTestId('blocklist-manager')).toBeTruthy();
    expect(screen.getByTestId('blocklist-entry-entry-1')).toBeTruthy();
    expect(screen.getByTestId('blocklist-entry-entry-2')).toBeTruthy();
    expect(screen.getByText('Acme Corp')).toBeTruthy();
    expect(screen.getByText('Evil Inc')).toBeTruthy();
    // "Current employer" appears as both entry note and preset button
    expect(screen.getAllByText('Current employer').length).toBeGreaterThanOrEqual(2);
  });

  it('shows stealth-required message when stealth is disabled', () => {
    renderWithProviders(<BlocklistManager stealthEnabled={false} />);

    expect(screen.getByTestId('blocklist-stealth-required')).toBeTruthy();
    expect(screen.getByText(/Enable Stealth Mode/)).toBeTruthy();
    expect(screen.queryByTestId('blocklist-manager')).toBeNull();
  });

  it('calls add mutation when adding a company', () => {
    renderWithProviders(<BlocklistManager stealthEnabled={true} />);

    const input = screen.getByTestId('blocklist-company-input');
    fireEvent.change(input, { target: { value: 'NewCorp' } });

    const noteInput = screen.getByTestId('blocklist-note-input');
    fireEvent.change(noteInput, { target: { value: 'Competitor' } });

    fireEvent.click(screen.getByTestId('blocklist-add-btn'));

    expect(mockAddMutate).toHaveBeenCalledWith(
      { company_name: 'NewCorp', note: 'Competitor' },
      expect.any(Object),
    );
  });

  it('calls remove mutation when clicking remove', () => {
    renderWithProviders(<BlocklistManager stealthEnabled={true} />);

    fireEvent.click(screen.getByTestId('blocklist-remove-entry-1'));
    expect(mockRemoveMutate).toHaveBeenCalledWith({ entryId: 'entry-1' });
  });

  it('shows note preset buttons', () => {
    renderWithProviders(<BlocklistManager stealthEnabled={true} />);

    // "Current employer" appears both as entry note and preset button
    expect(screen.getAllByText('Current employer').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('Previous employer')).toBeTruthy();
  });

  it('sets note when clicking preset', () => {
    renderWithProviders(<BlocklistManager stealthEnabled={true} />);

    // Click the "Previous employer" preset (unique — no entry has this note)
    fireEvent.click(screen.getByText('Previous employer'));

    const noteInput = screen.getByTestId('blocklist-note-input') as HTMLInputElement;
    expect(noteInput.value).toBe('Previous employer');
  });
});
