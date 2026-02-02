/**
 * Privacy settings page — Stealth Mode toggle.
 *
 * Shows stealth mode status, explanation, and toggle control.
 * Disabled with upgrade prompt for ineligible tiers.
 */

import { useStealthStatus, useToggleStealth } from '../services/privacy';
import BlocklistManager from '../components/privacy/BlocklistManager';
import PrivacyProof from '../components/privacy/PrivacyProof';

export default function Privacy() {
  const { data, isLoading, error } = useStealthStatus();
  const toggleStealth = useToggleStealth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-indigo-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center text-red-700">
        Failed to load privacy settings.
      </div>
    );
  }

  const stealthEnabled = data?.stealth_enabled ?? false;
  const eligible = data?.eligible ?? false;

  function handleToggle() {
    if (!eligible) return;
    toggleStealth.mutate({ enabled: !stealthEnabled });
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Privacy Settings</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage your job search visibility and privacy controls.
        </p>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Stealth Mode</h2>
            <p className="mt-1 text-sm text-gray-500">
              Hide your job search activity from your current employer.
            </p>
          </div>
          <button
            data-testid="stealth-toggle"
            onClick={handleToggle}
            disabled={!eligible || toggleStealth.isPending}
            className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 ${
              !eligible ? 'cursor-not-allowed opacity-50' : ''
            } ${stealthEnabled ? 'bg-green-600' : 'bg-gray-200'}`}
            role="switch"
            aria-checked={stealthEnabled}
          >
            <span
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                stealthEnabled ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {!eligible && (
          <div
            data-testid="upgrade-prompt"
            className="mt-4 rounded-md bg-amber-50 p-3 text-sm text-amber-700"
          >
            Stealth Mode requires a Career Insurance or Enterprise plan.{' '}
            <a href="/settings" className="font-medium underline">
              Upgrade your plan
            </a>{' '}
            to enable this feature.
          </div>
        )}

        {stealthEnabled && (
          <div
            data-testid="stealth-explanation"
            className="mt-4 space-y-2 rounded-md bg-green-50 p-4 text-sm text-green-800"
          >
            <p className="font-medium">Stealth Mode is active. Here's what's protected:</p>
            <ul className="list-inside list-disc space-y-1">
              <li>Your profile is hidden from public search</li>
              <li>Employer blocklist is activated</li>
              <li>All agent actions avoid public visibility</li>
            </ul>
          </div>
        )}
      </div>

      <BlocklistManager stealthEnabled={stealthEnabled} />

      <PrivacyProof stealthEnabled={stealthEnabled} />
    </div>
  );
}
