/**
 * FollowUps page — lists pending follow-up suggestions with editing capability.
 */

import { useState } from 'react';
import FollowUpList from '../components/followups/FollowUpList';
import FollowUpEditor from '../components/followups/FollowUpEditor';
import { useFollowups } from '../services/followups';
import type { FollowupSuggestion } from '../services/followups';

export default function FollowUps() {
  const { data, isLoading, error } = useFollowups();
  const [editingSuggestion, setEditingSuggestion] = useState<FollowupSuggestion | null>(null);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8" data-testid="followups-page">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Follow-ups</h1>

      {isLoading && (
        <div data-testid="followups-loading" className="text-center py-12 text-gray-500">
          Loading follow-up suggestions...
        </div>
      )}

      {error && (
        <div data-testid="followups-error" className="text-center py-12 text-red-500">
          Failed to load follow-up suggestions.
        </div>
      )}

      {data && (
        <FollowUpList
          suggestions={data.suggestions}
          onEdit={(s) => setEditingSuggestion(s)}
        />
      )}

      {editingSuggestion && (
        <FollowUpEditor
          suggestion={editingSuggestion}
          onClose={() => setEditingSuggestion(null)}
        />
      )}
    </div>
  );
}
