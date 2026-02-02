/**
 * Tests for Follow-up Draft Generation UI (Story 6-8).
 *
 * Covers: list rendering, expand row, edit opens editor, save draft,
 * copy to clipboard, empty state.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import FollowUpList from '../components/followups/FollowUpList';
import FollowUpEditor from '../components/followups/FollowUpEditor';
import FollowUps from '../pages/FollowUps';
import type { FollowupSuggestion } from '../services/followups';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockMutate = vi.fn();
const mockFollowupsData = {
  suggestions: [
    {
      id: 'sugg-1',
      application_id: 'app-1',
      company: 'Acme Corp',
      job_title: 'Software Engineer',
      status: 'applied',
      followup_date: '2025-01-15T00:00:00+00:00',
      draft_subject: 'Following up on my application',
      draft_body: 'Dear Hiring Team, I wanted to follow up...',
      created_at: '2025-01-10T00:00:00+00:00',
    },
    {
      id: 'sugg-2',
      application_id: 'app-2',
      company: 'TechCo',
      job_title: 'Frontend Developer',
      status: 'interview',
      followup_date: '2025-01-20T00:00:00+00:00',
      draft_subject: 'Thank you for the interview',
      draft_body: 'Dear Team, Thank you for the opportunity...',
      created_at: '2025-01-18T00:00:00+00:00',
    },
  ] as FollowupSuggestion[],
  total: 2,
};

vi.mock('../services/followups', async () => {
  const actual = await vi.importActual('../services/followups');
  return {
    ...actual,
    useFollowups: vi.fn(() => ({
      data: mockFollowupsData,
      isLoading: false,
      error: null,
    })),
    useUpdateDraft: vi.fn(() => ({ mutate: mockMutate })),
    useSendFollowup: vi.fn(() => ({ mutate: mockMutate })),
    useCopyFollowup: vi.fn(() => ({ mutate: mockMutate })),
    useDismissFollowup: vi.fn(() => ({ mutate: mockMutate })),
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
// FollowUpList tests
// ---------------------------------------------------------------------------

describe('FollowUpList', () => {
  it('renders all suggestion rows', () => {
    const onEdit = vi.fn();
    renderWithProviders(
      <FollowUpList suggestions={mockFollowupsData.suggestions} onEdit={onEdit} />,
    );

    expect(screen.getByText('Acme Corp')).toBeTruthy();
    expect(screen.getByText('TechCo')).toBeTruthy();
    expect(screen.getByTestId('followup-list')).toBeTruthy();
  });

  it('shows empty state when no suggestions', () => {
    const onEdit = vi.fn();
    renderWithProviders(<FollowUpList suggestions={[]} onEdit={onEdit} />);

    expect(screen.getByTestId('followup-empty')).toBeTruthy();
    expect(screen.getByText('No follow-ups pending')).toBeTruthy();
  });

  it('expands row to show draft body on click', () => {
    const onEdit = vi.fn();
    renderWithProviders(
      <FollowUpList suggestions={mockFollowupsData.suggestions} onEdit={onEdit} />,
    );

    // Initially no expanded content
    expect(screen.queryByTestId('followup-expanded-sugg-1')).toBeNull();

    // Click to expand
    fireEvent.click(screen.getByTestId('followup-toggle-sugg-1'));

    expect(screen.getByTestId('followup-expanded-sugg-1')).toBeTruthy();
    expect(screen.getByText('Dear Hiring Team, I wanted to follow up...')).toBeTruthy();
  });

  it('calls onEdit when Edit button clicked', () => {
    const onEdit = vi.fn();
    renderWithProviders(
      <FollowUpList suggestions={mockFollowupsData.suggestions} onEdit={onEdit} />,
    );

    // Expand first
    fireEvent.click(screen.getByTestId('followup-toggle-sugg-1'));

    // Click Edit
    fireEvent.click(screen.getByTestId('followup-edit-sugg-1'));

    expect(onEdit).toHaveBeenCalledWith(mockFollowupsData.suggestions[0]);
  });

  it('calls send mutation when Send button clicked', () => {
    const onEdit = vi.fn();
    renderWithProviders(
      <FollowUpList suggestions={mockFollowupsData.suggestions} onEdit={onEdit} />,
    );

    fireEvent.click(screen.getByTestId('followup-toggle-sugg-1'));
    fireEvent.click(screen.getByTestId('followup-send-sugg-1'));

    expect(mockMutate).toHaveBeenCalledWith({ suggestionId: 'sugg-1' });
  });

  it('calls copy mutation when Copy to Clipboard button clicked', () => {
    const onEdit = vi.fn();
    renderWithProviders(
      <FollowUpList suggestions={mockFollowupsData.suggestions} onEdit={onEdit} />,
    );

    fireEvent.click(screen.getByTestId('followup-toggle-sugg-1'));
    fireEvent.click(screen.getByTestId('followup-copy-sugg-1'));

    expect(mockMutate).toHaveBeenCalledWith({
      suggestionId: 'sugg-1',
      subject: 'Following up on my application',
      body: 'Dear Hiring Team, I wanted to follow up...',
    });
  });
});

// ---------------------------------------------------------------------------
// FollowUpEditor tests
// ---------------------------------------------------------------------------

describe('FollowUpEditor', () => {
  const suggestion = mockFollowupsData.suggestions[0];

  it('renders editor with pre-filled subject and body', () => {
    const onClose = vi.fn();
    renderWithProviders(<FollowUpEditor suggestion={suggestion} onClose={onClose} />);

    const subjectInput = screen.getByTestId('draft-subject-input') as HTMLInputElement;
    const bodyInput = screen.getByTestId('draft-body-input') as HTMLTextAreaElement;

    expect(subjectInput.value).toBe('Following up on my application');
    expect(bodyInput.value).toBe('Dear Hiring Team, I wanted to follow up...');
  });

  it('calls save mutation when Save Draft clicked', () => {
    const onClose = vi.fn();
    renderWithProviders(<FollowUpEditor suggestion={suggestion} onClose={onClose} />);

    fireEvent.click(screen.getByTestId('editor-save-btn'));

    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        suggestionId: 'sugg-1',
        updates: {
          draft_subject: 'Following up on my application',
          draft_body: 'Dear Hiring Team, I wanted to follow up...',
        },
      }),
      expect.any(Object),
    );
  });

  it('closes when close button clicked', () => {
    const onClose = vi.fn();
    renderWithProviders(<FollowUpEditor suggestion={suggestion} onClose={onClose} />);

    fireEvent.click(screen.getByTestId('followup-editor-close'));

    expect(onClose).toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// FollowUps page tests
// ---------------------------------------------------------------------------

describe('FollowUps page', () => {
  it('renders page with suggestion list', () => {
    renderWithProviders(<FollowUps />);

    expect(screen.getByTestId('followups-page')).toBeTruthy();
    expect(screen.getByText('Follow-ups')).toBeTruthy();
    expect(screen.getByText('Acme Corp')).toBeTruthy();
  });
});
