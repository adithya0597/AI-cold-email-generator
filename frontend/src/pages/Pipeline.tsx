/**
 * Pipeline page -- Kanban board and list view of job applications.
 *
 * Story 6-5: Displays applications grouped by status in draggable columns.
 * Story 6-6: Adds list view with sort, filter, search, and bulk actions.
 */

import { useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useApplications, useUpdateApplicationStatus } from '../services/applications';
import type { ApplicationItem } from '../services/applications';
import KanbanCard from '../components/pipeline/KanbanCard';
import CardDetailPanel from '../components/pipeline/CardDetailPanel';
import PipelineListView from '../components/pipeline/PipelineListView';

/** Pipeline column definitions — order matters for display. */
const COLUMNS = [
  { key: 'applied', label: 'Applied' },
  { key: 'screening', label: 'Screening' },
  { key: 'interview', label: 'Interview' },
  { key: 'offer', label: 'Offer' },
  { key: 'closed', label: 'Closed' },
] as const;

/** Statuses that map to the "Closed" column. */
const CLOSED_STATUSES = new Set(['closed', 'rejected']);

function groupByStatus(applications: ApplicationItem[]): Record<string, ApplicationItem[]> {
  const groups: Record<string, ApplicationItem[]> = {};
  for (const col of COLUMNS) {
    groups[col.key] = [];
  }
  for (const app of applications) {
    const status = app.status.toLowerCase();
    if (CLOSED_STATUSES.has(status)) {
      groups['closed'].push(app);
    } else if (groups[status]) {
      groups[status].push(app);
    } else {
      // Unknown status falls into applied
      groups['applied'].push(app);
    }
  }
  return groups;
}

export default function Pipeline() {
  const { data, isLoading, isError } = useApplications();
  const updateStatus = useUpdateApplicationStatus();
  const [selectedApp, setSelectedApp] = useState<ApplicationItem | null>(null);
  const [viewMode, setViewMode] = useState<'kanban' | 'list'>('kanban');

  const handleDrop = useCallback(
    (e: React.DragEvent, targetStatus: string) => {
      e.preventDefault();
      const raw = e.dataTransfer.getData('application/json');
      if (!raw) return;
      try {
        const { id } = JSON.parse(raw);
        updateStatus.mutate({ applicationId: id, status: targetStatus });
      } catch {
        // ignore bad data
      }
    },
    [updateStatus],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }, []);

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg bg-red-50 p-6 text-center">
        <p className="text-red-600">Failed to load pipeline. Please try again.</p>
      </div>
    );
  }

  const applications = data?.applications ?? [];

  if (applications.length === 0) {
    return (
      <div data-testid="empty-state" className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-white p-12 text-center">
        <h2 className="text-xl font-semibold text-gray-900">Your pipeline is empty. Let's fill it up!</h2>

        {/* Kanban flow illustration */}
        <div data-testid="kanban-illustration" className="mt-6 flex items-center gap-2">
          {['Applied', 'Screening', 'Interview', 'Offer'].map((stage, i) => (
            <div key={stage} className="flex items-center gap-2">
              <div className="rounded-md bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-700 border border-indigo-200">
                {stage}
              </div>
              {i < 3 && <span className="text-gray-400">→</span>}
            </div>
          ))}
        </div>

        <Link
          to="/matches"
          data-testid="cta-find-matches"
          className="mt-6 inline-flex items-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
        >
          Find your first matches
        </Link>

        <p data-testid="email-tip" className="mt-4 max-w-md text-sm text-gray-500">
          Connect your email to auto-track existing applications
        </p>

        <Link
          to="/import"
          data-testid="import-link"
          className="mt-2 text-sm font-medium text-indigo-600 hover:text-indigo-500"
        >
          Import applications
        </Link>
      </div>
    );
  }

  const grouped = groupByStatus(applications);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Pipeline</h1>
        <div data-testid="view-toggle" className="inline-flex rounded-md shadow-sm">
          <button
            data-testid="toggle-kanban"
            onClick={() => setViewMode('kanban')}
            className={`rounded-l-md px-3 py-1.5 text-sm font-medium ${
              viewMode === 'kanban'
                ? 'bg-indigo-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-50'
            } border border-gray-300`}
          >
            Board
          </button>
          <button
            data-testid="toggle-list"
            onClick={() => setViewMode('list')}
            className={`-ml-px rounded-r-md px-3 py-1.5 text-sm font-medium ${
              viewMode === 'list'
                ? 'bg-indigo-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-50'
            } border border-gray-300`}
          >
            List
          </button>
        </div>
      </div>

      {viewMode === 'kanban' ? (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {COLUMNS.map((col) => (
            <div
              key={col.key}
              data-testid={`column-${col.key}`}
              onDrop={(e) => handleDrop(e, col.key)}
              onDragOver={handleDragOver}
              className="flex w-64 flex-shrink-0 flex-col rounded-lg bg-gray-50 p-3"
            >
              {/* Column header */}
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-700">{col.label}</h3>
                <span
                  data-testid={`count-${col.key}`}
                  className="inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-gray-200 px-1.5 text-xs font-medium text-gray-600"
                >
                  {grouped[col.key].length}
                </span>
              </div>

              {/* Cards */}
              <div className="flex flex-col gap-2">
                {grouped[col.key].map((app) => (
                  <KanbanCard
                    key={app.id}
                    application={app}
                    onClick={setSelectedApp}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <PipelineListView applications={applications} onCardClick={setSelectedApp} />
      )}

      {/* Detail panel */}
      {selectedApp && (
        <CardDetailPanel
          application={selectedApp}
          onClose={() => setSelectedApp(null)}
        />
      )}
    </div>
  );
}
