/**
 * Kanban card component for displaying an application in the pipeline board.
 *
 * Shows company, title, days in stage, last update, agent indicator,
 * last-followed-up indicator, and overdue follow-up badge.
 * Supports HTML5 drag and drop.
 */

import type { ApplicationItem } from '../../services/applications';
import { useFollowupHistory, useFollowups } from '../../services/followups';

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

  const { data: historyData } = useFollowupHistory(application.id);
  const { data: followupsData } = useFollowups();

  // Check if there's an overdue, unsent follow-up for this application
  const hasOverdue = followupsData?.suggestions.some(
    (s) =>
      s.application_id === application.id &&
      s.followup_date &&
      new Date(s.followup_date) < new Date(),
  );

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
        <div className="ml-2 flex items-center gap-1">
          {hasOverdue && (
            <span
              data-testid="overdue-badge"
              className="inline-flex items-center rounded-full bg-red-100 px-1.5 py-0.5 text-xs font-medium text-red-700"
            >
              Overdue
            </span>
          )}
          {isAgentUpdated && (
            <span
              data-testid="agent-badge"
              className="inline-flex items-center rounded-full bg-indigo-100 px-1.5 py-0.5 text-xs font-medium text-indigo-700"
            >
              Agent
            </span>
          )}
        </div>
      </div>
      <div className="mt-2 flex items-center justify-between text-xs text-gray-400">
        <span>{days}d in stage</span>
        <span>{new Date(application.applied_at).toLocaleDateString()}</span>
      </div>
      {historyData && historyData.last_followup_at && (
        <div
          className="mt-1 text-xs text-gray-400"
          data-testid="last-followup-indicator"
        >
          Last followed up: {daysSince(historyData.last_followup_at)}d ago
        </div>
      )}
    </div>
  );
}
