/**
 * Tests for Pipeline list view: toggle, table rendering, sort, filter, search, bulk actions.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import Pipeline from '../pages/Pipeline';
import PipelineListView from '../components/pipeline/PipelineListView';
import type { ApplicationItem } from '../services/applications';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockMutate = vi.fn();

vi.mock('../services/applications', () => ({
  useApplications: vi.fn(),
  useUpdateApplicationStatus: () => ({ mutate: mockMutate }),
}));

vi.mock('../services/api', () => ({
  useApiClient: () => ({}),
}));

import { useApplications } from '../services/applications';
const mockUseApplications = vi.mocked(useApplications);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      {ui}
    </QueryClientProvider>,
  );
}

const sampleApps: ApplicationItem[] = [
  {
    id: '1',
    job_id: 'j1',
    job_title: 'Software Engineer',
    company: 'Acme Corp',
    status: 'applied',
    applied_at: '2025-12-01T00:00:00Z',
    resume_version_id: null,
    updated_at: '2025-12-02T00:00:00Z',
    last_updated_by: null,
  },
  {
    id: '2',
    job_id: 'j2',
    job_title: 'Product Manager',
    company: 'Globex Inc',
    status: 'screening',
    applied_at: '2025-12-05T00:00:00Z',
    resume_version_id: null,
    updated_at: '2025-12-06T00:00:00Z',
    last_updated_by: 'agent',
  },
  {
    id: '3',
    job_id: 'j3',
    job_title: 'Data Analyst',
    company: 'Initech',
    status: 'interview',
    applied_at: '2025-11-15T00:00:00Z',
    resume_version_id: null,
    updated_at: null,
    last_updated_by: null,
  },
];

// ---------------------------------------------------------------------------
// View toggle tests (Task 1)
// ---------------------------------------------------------------------------

describe('View toggle', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseApplications.mockReturnValue({
      data: { applications: sampleApps, total: 3, has_more: false },
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useApplications>);
  });

  it('defaults to kanban view and switches to list on toggle click', () => {
    renderWithProviders(<Pipeline />);

    // Kanban columns should be visible by default
    expect(screen.getByTestId('column-applied')).toBeInTheDocument();
    expect(screen.queryByTestId('pipeline-list-view')).not.toBeInTheDocument();

    // Click list toggle
    fireEvent.click(screen.getByTestId('toggle-list'));

    // List view should now be visible, kanban hidden
    expect(screen.getByTestId('pipeline-list-view')).toBeInTheDocument();
    expect(screen.queryByTestId('column-applied')).not.toBeInTheDocument();
  });

  it('switches back to kanban from list', () => {
    renderWithProviders(<Pipeline />);

    fireEvent.click(screen.getByTestId('toggle-list'));
    expect(screen.getByTestId('pipeline-list-view')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('toggle-kanban'));
    expect(screen.getByTestId('column-applied')).toBeInTheDocument();
    expect(screen.queryByTestId('pipeline-list-view')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// PipelineListView component tests (Task 2)
// ---------------------------------------------------------------------------

describe('PipelineListView table rendering', () => {
  it('renders all rows with correct columns', () => {
    const onClick = vi.fn();
    renderWithProviders(
      <PipelineListView applications={sampleApps} onCardClick={onClick} />,
    );

    // All rows present
    expect(screen.getByTestId('list-row-1')).toBeInTheDocument();
    expect(screen.getByTestId('list-row-2')).toBeInTheDocument();
    expect(screen.getByTestId('list-row-3')).toBeInTheDocument();

    // Check column content
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('Software Engineer')).toBeInTheDocument();
    expect(screen.getByText('applied')).toBeInTheDocument();
  });

  it('triggers onCardClick when row is clicked', () => {
    const onClick = vi.fn();
    renderWithProviders(
      <PipelineListView applications={sampleApps} onCardClick={onClick} />,
    );

    fireEvent.click(screen.getByTestId('list-row-1'));
    expect(onClick).toHaveBeenCalledWith(sampleApps[0]);
  });
});

// ---------------------------------------------------------------------------
// Column sorting tests (Task 3)
// ---------------------------------------------------------------------------

describe('Column sorting', () => {
  it('sorts by company when header is clicked', () => {
    const onClick = vi.fn();
    renderWithProviders(
      <PipelineListView applications={sampleApps} onCardClick={onClick} />,
    );

    // Click company header to sort ascending
    fireEvent.click(screen.getByTestId('sort-company'));

    const rows = screen.getAllByTestId(/^list-row-/);
    // Acme Corp (1), Globex Inc (2), Initech (3) — ascending
    expect(rows[0]).toHaveAttribute('data-testid', 'list-row-1');
    expect(rows[1]).toHaveAttribute('data-testid', 'list-row-2');
    expect(rows[2]).toHaveAttribute('data-testid', 'list-row-3');

    // Click again to sort descending
    fireEvent.click(screen.getByTestId('sort-company'));

    const rowsDesc = screen.getAllByTestId(/^list-row-/);
    expect(rowsDesc[0]).toHaveAttribute('data-testid', 'list-row-3');
    expect(rowsDesc[1]).toHaveAttribute('data-testid', 'list-row-2');
    expect(rowsDesc[2]).toHaveAttribute('data-testid', 'list-row-1');
  });
});

// ---------------------------------------------------------------------------
// Filter and search tests (Task 4)
// ---------------------------------------------------------------------------

describe('Status filter and keyword search', () => {
  it('filters by status', () => {
    const onClick = vi.fn();
    renderWithProviders(
      <PipelineListView applications={sampleApps} onCardClick={onClick} />,
    );

    fireEvent.change(screen.getByTestId('status-filter'), {
      target: { value: 'screening' },
    });

    expect(screen.getByTestId('list-row-2')).toBeInTheDocument();
    expect(screen.queryByTestId('list-row-1')).not.toBeInTheDocument();
    expect(screen.queryByTestId('list-row-3')).not.toBeInTheDocument();
  });

  it('filters by search keyword', () => {
    const onClick = vi.fn();
    renderWithProviders(
      <PipelineListView applications={sampleApps} onCardClick={onClick} />,
    );

    fireEvent.change(screen.getByTestId('search-input'), {
      target: { value: 'initech' },
    });

    expect(screen.getByTestId('list-row-3')).toBeInTheDocument();
    expect(screen.queryByTestId('list-row-1')).not.toBeInTheDocument();
    expect(screen.queryByTestId('list-row-2')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Bulk actions tests (Task 5)
// ---------------------------------------------------------------------------

describe('Bulk actions', () => {
  it('shows bulk action bar when rows selected and applies status change', () => {
    const onClick = vi.fn();
    renderWithProviders(
      <PipelineListView applications={sampleApps} onCardClick={onClick} />,
    );

    // No bulk bar initially
    expect(screen.queryByTestId('bulk-action-bar')).not.toBeInTheDocument();

    // Select first row checkbox
    const checkboxes = screen.getAllByRole('checkbox');
    // First checkbox is select-all, rest are row checkboxes
    fireEvent.click(checkboxes[1]); // row 1

    expect(screen.getByTestId('bulk-action-bar')).toBeInTheDocument();
    expect(screen.getByText('1 selected')).toBeInTheDocument();

    // Choose status and apply
    fireEvent.change(screen.getByTestId('bulk-status-select'), {
      target: { value: 'interview' },
    });
    fireEvent.click(screen.getByTestId('bulk-apply-btn'));

    expect(mockMutate).toHaveBeenCalledWith({
      applicationId: expect.any(String),
      status: 'interview',
    });
  });

  it('select all toggles all rows', () => {
    const onClick = vi.fn();
    renderWithProviders(
      <PipelineListView applications={sampleApps} onCardClick={onClick} />,
    );

    fireEvent.click(screen.getByTestId('select-all'));
    expect(screen.getByText('3 selected')).toBeInTheDocument();

    // Deselect all
    fireEvent.click(screen.getByTestId('select-all'));
    expect(screen.queryByTestId('bulk-action-bar')).not.toBeInTheDocument();
  });
});
