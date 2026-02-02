/**
 * FollowUpList — displays pending follow-up suggestions.
 *
 * Each row shows company, job title, due date, and draft subject.
 * Expandable rows reveal the full draft body with action buttons,
 * follow-up history, and excessive follow-up warnings.
 */

import { useState } from 'react';
import type { FollowupSuggestion } from '../../services/followups';
import {
  useDismissFollowup,
  useSendFollowup,
  useCopyFollowup,
  useFollowupHistory,
  useMarkManualFollowup,
} from '../../services/followups';
import FollowUpHistory from './FollowUpHistory';

interface FollowUpListProps {
  suggestions: FollowupSuggestion[];
  onEdit: (suggestion: FollowupSuggestion) => void;
}

function ExpandedContent({
  s,
  onEdit,
}: {
  s: FollowupSuggestion;
  onEdit: (suggestion: FollowupSuggestion) => void;
}) {
  const dismissMutation = useDismissFollowup();
  const sendMutation = useSendFollowup();
  const copyMutation = useCopyFollowup();
  const markManualMutation = useMarkManualFollowup();
  const { data: historyData } = useFollowupHistory(s.application_id);

  return (
    <div
      className="px-4 pb-4 border-t border-gray-100"
      data-testid={`followup-expanded-${s.id}`}
    >
      {/* Excessive follow-up warning */}
      {s.followup_count >= 3 && (
        <div
          className="mt-3 px-3 py-2 rounded bg-amber-50 border border-amber-200 text-sm text-amber-700"
          data-testid={`followup-warning-${s.id}`}
        >
          You've followed up {s.followup_count} times — consider moving on
        </div>
      )}

      <div className="mt-3">
        <p className="text-sm font-medium text-gray-700">
          Subject: {s.draft_subject ?? '(no subject)'}
        </p>
        <p className="mt-2 text-sm text-gray-600 whitespace-pre-wrap">
          {s.draft_body ?? '(no body)'}
        </p>
      </div>

      {/* Follow-up history */}
      {historyData && historyData.history.length > 0 && (
        <FollowUpHistory history={historyData.history} />
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          className="px-3 py-1.5 text-sm font-medium rounded bg-blue-600 text-white hover:bg-blue-700"
          onClick={() => onEdit(s)}
          data-testid={`followup-edit-${s.id}`}
        >
          Edit
        </button>
        <button
          type="button"
          className="px-3 py-1.5 text-sm font-medium rounded bg-green-600 text-white hover:bg-green-700"
          onClick={() => sendMutation.mutate({ suggestionId: s.id })}
          data-testid={`followup-send-${s.id}`}
        >
          Send
        </button>
        <button
          type="button"
          className="px-3 py-1.5 text-sm font-medium rounded bg-gray-100 text-gray-700 hover:bg-gray-200"
          onClick={() =>
            copyMutation.mutate({
              suggestionId: s.id,
              subject: s.draft_subject ?? '',
              body: s.draft_body ?? '',
            })
          }
          data-testid={`followup-copy-${s.id}`}
        >
          Copy to Clipboard
        </button>
        <button
          type="button"
          className="px-3 py-1.5 text-sm font-medium rounded bg-gray-100 text-gray-700 hover:bg-gray-200"
          onClick={() => markManualMutation.mutate({ suggestionId: s.id })}
          data-testid={`followup-mark-manual-${s.id}`}
        >
          Followed up manually
        </button>
        <button
          type="button"
          className="px-3 py-1.5 text-sm font-medium rounded text-red-600 hover:bg-red-50"
          onClick={() => dismissMutation.mutate({ suggestionId: s.id })}
          data-testid={`followup-dismiss-${s.id}`}
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}

export default function FollowUpList({ suggestions, onEdit }: FollowUpListProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  if (suggestions.length === 0) {
    return (
      <div data-testid="followup-empty" className="text-center py-12 text-gray-500">
        <p className="text-lg font-medium">No follow-ups pending</p>
        <p className="text-sm mt-1">When follow-ups are due, they'll appear here.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2" data-testid="followup-list">
      {suggestions.map((s) => {
        const isExpanded = expandedId === s.id;
        return (
          <div
            key={s.id}
            className="border border-gray-200 rounded-lg bg-white"
            data-testid={`followup-row-${s.id}`}
          >
            {/* Summary row */}
            <button
              type="button"
              className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-gray-50"
              onClick={() => toggleExpand(s.id)}
              data-testid={`followup-toggle-${s.id}`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-900 truncate">
                    {s.company ?? 'Unknown Company'}
                  </span>
                  <span className="text-gray-400">—</span>
                  <span className="text-gray-600 truncate">
                    {s.job_title ?? 'Unknown Position'}
                  </span>
                  {s.followup_count >= 3 && (
                    <span
                      className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700"
                      data-testid={`followup-warning-badge-${s.id}`}
                    >
                      {s.followup_count}x
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
                  {s.followup_date && (
                    <span>Due: {new Date(s.followup_date).toLocaleDateString()}</span>
                  )}
                  {s.draft_subject && (
                    <span className="truncate">Subject: {s.draft_subject}</span>
                  )}
                </div>
              </div>
              <span className="ml-2 text-gray-400">{isExpanded ? '▲' : '▼'}</span>
            </button>

            {/* Expanded draft preview */}
            {isExpanded && <ExpandedContent s={s} onEdit={onEdit} />}
          </div>
        );
      })}
    </div>
  );
}
