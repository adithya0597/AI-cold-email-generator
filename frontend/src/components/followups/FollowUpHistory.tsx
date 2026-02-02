/**
 * FollowUpHistory — shows sent follow-ups for a specific application.
 */

import type { FollowupHistoryItem } from '../../services/followups';

interface FollowUpHistoryProps {
  history: FollowupHistoryItem[];
}

function daysSince(dateString: string): number {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  return Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)));
}

export default function FollowUpHistory({ history }: FollowUpHistoryProps) {
  if (history.length === 0) {
    return null;
  }

  return (
    <div className="mt-3 border-t border-gray-100 pt-3" data-testid="followup-history">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
        Follow-up History
      </p>
      <ul className="space-y-1">
        {history.map((item) => (
          <li
            key={item.id}
            className="flex items-center justify-between text-xs text-gray-500"
            data-testid={`history-item-${item.id}`}
          >
            <span className="truncate">
              {item.draft_subject ?? 'Follow-up sent'}
            </span>
            <span className="ml-2 whitespace-nowrap">
              {item.sent_at
                ? `${daysSince(item.sent_at)}d ago`
                : 'unknown'}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
