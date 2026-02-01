/**
 * LearnedPreferenceBanner — displays pending learned preference suggestions.
 *
 * Shows suggestion cards for patterns detected from swipe behavior,
 * with Accept/Dismiss buttons for each. Hidden when no pending preferences.
 */

import { useLearnedPreferences, useUpdateLearnedPreference } from '../../services/learnedPreferences';
import type { LearnedPreference } from '../../types/matches';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function describePattern(pref: LearnedPreference): string {
  const confidence = Math.round(pref.confidence * 100);
  switch (pref.pattern_type) {
    case 'company':
      return `You tend to dismiss jobs at ${pref.pattern_value} (${confidence}% of the time)`;
    case 'location':
      return `You tend to dismiss jobs in ${pref.pattern_value} (${confidence}% of the time)`;
    case 'remote':
      return pref.pattern_value === 'true'
        ? `You tend to dismiss remote jobs (${confidence}% of the time)`
        : `You tend to dismiss on-site jobs (${confidence}% of the time)`;
    case 'employment_type':
      return `You tend to dismiss ${pref.pattern_value} positions (${confidence}% of the time)`;
    default:
      return `Pattern detected: ${pref.pattern_type} = ${pref.pattern_value}`;
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function LearnedPreferenceBanner() {
  const { data: preferences, isLoading } = useLearnedPreferences();
  const updatePref = useUpdateLearnedPreference();

  if (isLoading || !preferences || preferences.length === 0) {
    return null;
  }

  return (
    <div className="w-full max-w-md mx-auto mb-6" data-testid="learned-preference-banner">
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
        Learned Preferences
      </h3>
      <div className="space-y-3">
        {preferences.map((pref) => (
          <div
            key={pref.id}
            data-testid={`learned-pref-${pref.id}`}
            className="bg-amber-50 border border-amber-200 rounded-xl p-4 shadow-sm"
          >
            <p className="text-sm text-gray-800 mb-3">
              {describePattern(pref)}
            </p>
            <div className="flex items-center gap-3">
              <button
                data-testid={`accept-pref-${pref.id}`}
                onClick={() => updatePref.mutate({ id: pref.id, status: 'acknowledged' })}
                className="px-3 py-1.5 text-xs font-medium rounded-lg bg-green-100 text-green-700 hover:bg-green-200 transition-colors"
              >
                Accept
              </button>
              <button
                data-testid={`dismiss-pref-${pref.id}`}
                onClick={() => updatePref.mutate({ id: pref.id, status: 'rejected' })}
                className="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
              >
                Dismiss
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
