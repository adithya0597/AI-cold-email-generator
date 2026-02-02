/**
 * Tests for Follow-up Tracking UI (Story 6-9).
 *
 * Covers: history display, last-followup indicator, overdue badge,
 * manual mark button, excessive warning.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import FollowUpList from '../components/followups/FollowUpList';
import FollowUpHistory from '../components/followups/FollowUpHistory';
import KanbanCard from '../components/pipeline/KanbanCard';
import type { FollowupSuggestion, FollowupHistoryItem } from '../services/followups';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockMutate = vi.fn();
const mockHistoryData = {
  history: [
    {
      id: 'hist-1',
      draft_subject: 'Follow-up: Engineer at Acme',
      sent_at: '2025-01-10T10:00:00+00:00',
    },
  ] as FollowupHistoryItem[],
  followup_count: 1,
  last_followup_at: '2025-01-10T10:00:00+00:00',
};

const overdueSuggestion: FollowupSuggestion = {
  id: 'sugg-overdue',
  application_id: 'app-1',
  company: 'Acme Corp',
  job_title: 'Software Engineer',
  status: 'applied',
  followup_date: '2024-01-01T00:00:00+00:00', // far in the past = overdue
  draft_subject: 'Follow-up',
  draft_body: 'Hello',
  created_at: '2024-12-01T00:00:00+00:00',
  followup_count: 0,
};

const excessiveSuggestion: FollowupSuggestion = {
  id: 'sugg-excessive',
  application_id: 'app-2',
  company: 'TechCo',
  job_title: 'Frontend Dev',
  status: 'applied',
  followup_date: '2025-02-01T00:00:00+00:00',
  draft_subject: 'Follow-up again',
  draft_body: 'Hello again',
  created_at: '2025-01-20T00:00:00+00:00',
  followup_count: 4,
};

vi.mock('../services/followups', async () => {
  const actual = await vi.importActual('../services/followups');
  return {
    ...actual,
    useFollowups: vi.fn(() => ({
      data: {
        suggestions: [overdueSuggestion],
        total: 1,
      },
      isLoading: false,
      error: null,
    })),
    useFollowupHistory: vi.fn(() => ({
      data: mockHistoryData,
      isLoading: false,
      error: null,
    })),
    useUpdateDraft: vi.fn(() => ({ mutate: mockMutate })),
    useSendFollowup: vi.fn(() => ({ mutate: mockMutate })),
    useCopyFollowup: vi.fn(() => ({ mutate: mockMutate })),
    useDismissFollowup: vi.fn(() => ({ mutate: mockMutate })),
    useMarkManualFollowup: vi.fn(() => ({ mutate: mockMutate })),
  };
});

vi.mock('../services/api', () => ({
  useApiClient: vi.fn(() => ({})),
}));

vi.mock('../services/applications', () => ({
  useApplications: vi.fn(() => ({
    data: { applications: [], total: 0, has_more: false },
    isLoading: false,
    error: null,
  })),
  useUpdateApplicationStatus: vi.fn(() => ({ mutate: vi.fn() })),
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
// FollowUpHistory tests
// ---------------------------------------------------------------------------

describe('FollowUpHistory', () => {
  it('renders history items with sent date', () => {
    renderWithProviders(
      <FollowUpHistory history={mockHistoryData.history} />,
    );

    expect(screen.getByTestId('followup-history')).toBeTruthy();
    expect(screen.getByText('Follow-up: Engineer at Acme')).toBeTruthy();
  });

  it('returns null when no history', () => {
    const { container } = renderWithProviders(
      <FollowUpHistory history={[]} />,
    );
    expect(container.innerHTML).toBe('');
  });
});

// ---------------------------------------------------------------------------
// FollowUpList tracking features tests
// ---------------------------------------------------------------------------

describe('FollowUpList tracking', () => {
  it('shows excessive follow-up warning when count >= 3', () => {
    const onEdit = vi.fn();
    renderWithProviders(
      <FollowUpList suggestions={[excessiveSuggestion]} onEdit={onEdit} />,
    );

    // Warning badge should show in summary row
    expect(screen.getByTestId('followup-warning-badge-sugg-excessive')).toBeTruthy();
    expect(screen.getByText('4x')).toBeTruthy();

    // Expand to see full warning
    fireEvent.click(screen.getByTestId('followup-toggle-sugg-excessive'));
    expect(screen.getByTestId('followup-warning-sugg-excessive')).toBeTruthy();
    expect(screen.getByText(/followed up 4 times/)).toBeTruthy();
  });

  it('shows manual follow-up button in expanded view', () => {
    const onEdit = vi.fn();
    renderWithProviders(
      <FollowUpList suggestions={[overdueSuggestion]} onEdit={onEdit} />,
    );

    fireEvent.click(screen.getByTestId('followup-toggle-sugg-overdue'));
    expect(screen.getByTestId('followup-mark-manual-sugg-overdue')).toBeTruthy();
    expect(screen.getByText('Followed up manually')).toBeTruthy();
  });

  it('calls mark manual mutation when button clicked', () => {
    const onEdit = vi.fn();
    renderWithProviders(
      <FollowUpList suggestions={[overdueSuggestion]} onEdit={onEdit} />,
    );

    fireEvent.click(screen.getByTestId('followup-toggle-sugg-overdue'));
    fireEvent.click(screen.getByTestId('followup-mark-manual-sugg-overdue'));
    expect(mockMutate).toHaveBeenCalledWith({ suggestionId: 'sugg-overdue' });
  });

  it('shows follow-up history in expanded view', () => {
    const onEdit = vi.fn();
    renderWithProviders(
      <FollowUpList suggestions={[overdueSuggestion]} onEdit={onEdit} />,
    );

    fireEvent.click(screen.getByTestId('followup-toggle-sugg-overdue'));
    expect(screen.getByTestId('followup-history')).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// KanbanCard tracking features tests
// ---------------------------------------------------------------------------

describe('KanbanCard tracking', () => {
  const mockApp = {
    id: 'app-1',
    job_id: 'job-1',
    job_title: 'Software Engineer',
    company: 'Acme Corp',
    status: 'applied',
    applied_at: '2025-01-01T00:00:00+00:00',
    resume_version_id: null,
    updated_at: null,
    last_updated_by: null,
  };

  it('shows last-followup indicator when history exists', () => {
    renderWithProviders(
      <KanbanCard application={mockApp} onClick={vi.fn()} />,
    );

    expect(screen.getByTestId('last-followup-indicator')).toBeTruthy();
    expect(screen.getByText(/Last followed up:/)).toBeTruthy();
  });

  it('shows overdue badge when follow-up is overdue', () => {
    renderWithProviders(
      <KanbanCard application={mockApp} onClick={vi.fn()} />,
    );

    expect(screen.getByTestId('overdue-badge')).toBeTruthy();
    expect(screen.getByText('Overdue')).toBeTruthy();
  });
});
