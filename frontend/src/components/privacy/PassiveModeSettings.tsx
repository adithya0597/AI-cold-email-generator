/**
 * Passive Mode settings component.
 *
 * Allows configuration of search frequency, match threshold,
 * notifications, and auto-save. Supports Sprint Mode activation.
 */

import { useState, useEffect } from 'react';
import {
  usePassiveMode,
  useUpdatePassiveMode,
  useActivateSprint,
} from '../../services/privacy';

export default function PassiveModeSettings() {
  const { data, isLoading } = usePassiveMode();
  const updateSettings = useUpdatePassiveMode();
  const activateSprint = useActivateSprint();

  const [frequency, setFrequency] = useState('weekly');
  const [matchScore, setMatchScore] = useState(70);
  const [notifPref, setNotifPref] = useState('weekly_digest');
  const [autoSave, setAutoSave] = useState(85);

  useEffect(() => {
    if (data) {
      setFrequency(data.search_frequency);
      setMatchScore(data.min_match_score);
      setNotifPref(data.notification_pref);
      setAutoSave(data.auto_save_threshold);
    }
  }, [data]);

  const eligible = data?.eligible ?? false;
  const mode = data?.mode ?? 'passive';

  function handleSave() {
    updateSettings.mutate({
      search_frequency: frequency,
      min_match_score: matchScore,
      notification_pref: notifPref,
      auto_save_threshold: autoSave,
    });
  }

  function handleSprint() {
    activateSprint.mutate();
  }

  if (isLoading) {
    return null;
  }

  return (
    <div
      data-testid="passive-mode-settings"
      className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
    >
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            {mode === 'sprint' ? 'Sprint Mode' : 'Passive Mode'}
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            Configure how actively JobPilot searches for opportunities.
          </p>
        </div>
        {mode === 'sprint' && (
          <span
            data-testid="sprint-badge"
            className="inline-flex items-center rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-700"
          >
            Sprint Active
          </span>
        )}
      </div>

      {!eligible && (
        <div
          data-testid="passive-upgrade-prompt"
          className="mt-4 rounded-md bg-amber-50 p-3 text-sm text-amber-700"
        >
          Passive Mode requires a Career Insurance or Enterprise plan.
        </div>
      )}

      <div className={`mt-4 space-y-4 ${!eligible ? 'pointer-events-none opacity-50' : ''}`}>
        {/* Search Frequency */}
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Search Frequency
          </label>
          <select
            data-testid="frequency-select"
            value={frequency}
            onChange={(e) => setFrequency(e.target.value)}
            disabled={!eligible}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
          </select>
        </div>

        {/* Minimum Match Score */}
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Minimum Match Score: {matchScore}%
          </label>
          <input
            data-testid="match-score-slider"
            type="range"
            min="30"
            max="95"
            value={matchScore}
            onChange={(e) => setMatchScore(Number(e.target.value))}
            disabled={!eligible}
            className="mt-1 w-full"
          />
          <div className="flex justify-between text-xs text-gray-400">
            <span>More matches</span>
            <span>Fewer, better matches</span>
          </div>
        </div>

        {/* Notification Preferences */}
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Notifications
          </label>
          <select
            data-testid="notification-select"
            value={notifPref}
            onChange={(e) => setNotifPref(e.target.value)}
            disabled={!eligible}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
          >
            <option value="weekly_digest">Weekly digest</option>
            <option value="immediate">Immediate for hot matches</option>
          </select>
        </div>

        {/* Auto-save Threshold */}
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Auto-save Threshold: {autoSave}%
          </label>
          <input
            data-testid="auto-save-slider"
            type="range"
            min="50"
            max="99"
            value={autoSave}
            onChange={(e) => setAutoSave(Number(e.target.value))}
            disabled={!eligible}
            className="mt-1 w-full"
          />
          <p className="mt-1 text-xs text-gray-400">
            Jobs scoring above this threshold are saved automatically.
          </p>
        </div>

        <div className="flex gap-3 pt-2">
          <button
            data-testid="save-settings-btn"
            onClick={handleSave}
            disabled={!eligible || updateSettings.isPending}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {updateSettings.isPending ? 'Saving...' : 'Save Settings'}
          </button>
          {mode !== 'sprint' && (
            <button
              data-testid="sprint-btn"
              onClick={handleSprint}
              disabled={!eligible || activateSprint.isPending}
              className="rounded-md border border-orange-500 bg-white px-4 py-2 text-sm font-medium text-orange-600 hover:bg-orange-50 disabled:opacity-50"
            >
              {activateSprint.isPending ? 'Activating...' : 'Activate Sprint Mode'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
