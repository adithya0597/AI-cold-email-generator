/**
 * Kanban card component for displaying an application in the pipeline board.
 *
 * Shows company, title, days in stage, last update, and agent indicator.
 * Supports HTML5 drag and drop.
 */

import type { ApplicationItem } from '../../services/applications';

interface KanbanCardProps {
  application: ApplicationItem;
  onClick: (app: ApplicationItem) => void;
}

function daysSince(dateString: string): number {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  return Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)));
}

export default function KanbanCard({ application, onClick }: KanbanCardProps) {
  const days = daysSince(application.applied_at);
  const isAgentUpdated = application.last_updated_by === 'agent';

  function handleDragStart(e: React.DragEvent) {
    e.dataTransfer.setData('application/json', JSON.stringify({ id: application.id }));
    e.dataTransfer.effectAllowed = 'move';
  }

  return (
    <div
      data-testid={`kanban-card-${application.id}`}
      draggable
      onDragStart={handleDragStart}
      onClick={() => onClick(application)}
      className="cursor-pointer rounded-lg border border-gray-200 bg-white p-3 shadow-sm transition-shadow hover:shadow-md"
    >
      <div className="flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-gray-900">
            {application.company ?? 'Unknown Company'}
          </p>
          <p className="mt-0.5 truncate text-xs text-gray-500">
            {application.job_title ?? 'Untitled Position'}
          </p>
        </div>
        {isAgentUpdated && (
          <span
            data-testid="agent-badge"
            className="ml-2 inline-flex items-center rounded-full bg-indigo-100 px-1.5 py-0.5 text-xs font-medium text-indigo-700"
          >
            Agent
          </span>
        )}
      </div>
      <div className="mt-2 flex items-center justify-between text-xs text-gray-400">
        <span>{days}d in stage</span>
        <span>{new Date(application.applied_at).toLocaleDateString()}</span>
      </div>
    </div>
  );
}
