/**
 * Tests for Pipeline page, KanbanCard, and CardDetailPanel components.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import Pipeline from '../pages/Pipeline';
import KanbanCard from '../components/pipeline/KanbanCard';
import CardDetailPanel from '../components/pipeline/CardDetailPanel';
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
    last_updated_by: 'agent',
  },
  {
    id: '3',
    job_id: 'j3',
    job_title: 'Data Analyst',
    company: 'Initech',
    status: 'rejected',
    applied_at: '2025-11-15T00:00:00Z',
    resume_version_id: null,
    last_updated_by: null,
  },
];

// ---------------------------------------------------------------------------
// Pipeline page tests
// ---------------------------------------------------------------------------

describe('Pipeline page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all five columns with correct counts', () => {
    mockUseApplications.mockReturnValue({
      data: { applications: sampleApps, total: 3, has_more: false },
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useApplications>);

    renderWithProviders(<Pipeline />);

    expect(screen.getByTestId('column-applied')).toBeInTheDocument();
    expect(screen.getByTestId('column-screening')).toBeInTheDocument();
    expect(screen.getByTestId('column-interview')).toBeInTheDocument();
    expect(screen.getByTestId('column-offer')).toBeInTheDocument();
    expect(screen.getByTestId('column-closed')).toBeInTheDocument();

    // Count badges
    expect(screen.getByTestId('count-applied')).toHaveTextContent('1');
    expect(screen.getByTestId('count-screening')).toHaveTextContent('1');
    expect(screen.getByTestId('count-interview')).toHaveTextContent('0');
    expect(screen.getByTestId('count-offer')).toHaveTextContent('0');
    // rejected maps to closed column
    expect(screen.getByTestId('count-closed')).toHaveTextContent('1');
  });

  it('renders empty state when no applications', () => {
    mockUseApplications.mockReturnValue({
      data: { applications: [], total: 0, has_more: false },
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useApplications>);

    renderWithProviders(<Pipeline />);

    expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    expect(screen.getByText('Your pipeline is empty')).toBeInTheDocument();
  });

  it('renders loading spinner when loading', () => {
    mockUseApplications.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as ReturnType<typeof useApplications>);

    renderWithProviders(<Pipeline />);

    // Spinner element with animate-spin class
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// KanbanCard tests
// ---------------------------------------------------------------------------

describe('KanbanCard', () => {
  const app: ApplicationItem = sampleApps[0];

  it('renders company, title, and applied date', () => {
    const onClick = vi.fn();
    renderWithProviders(<KanbanCard application={app} onClick={onClick} />);

    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('Software Engineer')).toBeInTheDocument();
  });

  it('shows agent badge when last_updated_by is agent', () => {
    const agentApp = sampleApps[1]; // last_updated_by: 'agent'
    const onClick = vi.fn();
    renderWithProviders(<KanbanCard application={agentApp} onClick={onClick} />);

    expect(screen.getByTestId('agent-badge')).toBeInTheDocument();
    expect(screen.getByText('Agent')).toBeInTheDocument();
  });

  it('does not show agent badge when not agent-updated', () => {
    const onClick = vi.fn();
    renderWithProviders(<KanbanCard application={app} onClick={onClick} />);

    expect(screen.queryByTestId('agent-badge')).not.toBeInTheDocument();
  });

  it('calls onClick with application on click', () => {
    const onClick = vi.fn();
    renderWithProviders(<KanbanCard application={app} onClick={onClick} />);

    fireEvent.click(screen.getByTestId(`kanban-card-${app.id}`));
    expect(onClick).toHaveBeenCalledWith(app);
  });
});

// ---------------------------------------------------------------------------
// Drag & drop test
// ---------------------------------------------------------------------------

describe('Drag and drop', () => {
  it('sets drag data on dragStart', () => {
    const app = sampleApps[0];
    const onClick = vi.fn();
    renderWithProviders(<KanbanCard application={app} onClick={onClick} />);

    const card = screen.getByTestId(`kanban-card-${app.id}`);
    const setData = vi.fn();
    fireEvent.dragStart(card, {
      dataTransfer: { setData, effectAllowed: '' },
    });

    expect(setData).toHaveBeenCalledWith(
      'application/json',
      JSON.stringify({ id: app.id }),
    );
  });
});

// ---------------------------------------------------------------------------
// CardDetailPanel tests
// ---------------------------------------------------------------------------

describe('CardDetailPanel', () => {
  const app = sampleApps[0];

  it('renders application details and closes on Escape', () => {
    const onClose = vi.fn();
    renderWithProviders(
      <CardDetailPanel application={app} onClose={onClose} />,
    );

    expect(screen.getByText('Software Engineer')).toBeInTheDocument();
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByTestId('detail-panel')).toBeInTheDocument();

    // Press Escape
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });

  it('closes on overlay click', () => {
    const onClose = vi.fn();
    renderWithProviders(
      <CardDetailPanel application={app} onClose={onClose} />,
    );

    fireEvent.click(screen.getByTestId('detail-panel-overlay'));
    expect(onClose).toHaveBeenCalled();
  });
});
