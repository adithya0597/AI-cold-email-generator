/**
 * Employer blocklist management component.
 *
 * Allows adding/removing companies from the blocklist with optional notes.
 * Requires active Stealth Mode.
 */

import { useState } from 'react';
import {
  useBlocklist,
  useAddToBlocklist,
  useRemoveFromBlocklist,
} from '../../services/privacy';

const NOTE_PRESETS = ['Current employer', 'Competitor', 'Previous employer'];

interface BlocklistManagerProps {
  stealthEnabled: boolean;
}

export default function BlocklistManager({ stealthEnabled }: BlocklistManagerProps) {
  const { data, isLoading } = useBlocklist();
  const addEntry = useAddToBlocklist();
  const removeEntry = useRemoveFromBlocklist();

  const [companyName, setCompanyName] = useState('');
  const [note, setNote] = useState('');

  if (!stealthEnabled) {
    return (
      <div
        data-testid="blocklist-stealth-required"
        className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
      >
        <h2 className="text-lg font-semibold text-gray-900">Employer Blocklist</h2>
        <p className="mt-2 text-sm text-gray-500">
          Enable Stealth Mode above to manage your employer blocklist.
        </p>
      </div>
    );
  }

  function handleAdd() {
    if (!companyName.trim()) return;
    addEntry.mutate(
      { company_name: companyName.trim(), note: note.trim() || undefined },
      {
        onSuccess: () => {
          setCompanyName('');
          setNote('');
        },
      },
    );
  }

  function handleRemove(entryId: string) {
    removeEntry.mutate({ entryId });
  }

  const entries = data?.entries ?? [];

  return (
    <div
      data-testid="blocklist-manager"
      className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
    >
      <h2 className="text-lg font-semibold text-gray-900">Employer Blocklist</h2>
      <p className="mt-1 text-sm text-gray-500">
        Companies on this list will never see your activity, appear in matches, or receive applications.
      </p>

      {/* Add form */}
      <div className="mt-4 space-y-3">
        <div className="flex gap-2">
          <input
            data-testid="blocklist-company-input"
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            placeholder="Company name"
            className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
          <button
            data-testid="blocklist-add-btn"
            onClick={handleAdd}
            disabled={!companyName.trim() || addEntry.isPending}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            Add
          </button>
        </div>
        <div className="flex items-center gap-2">
          <input
            data-testid="blocklist-note-input"
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Note (optional)"
            className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
          {NOTE_PRESETS.map((preset) => (
            <button
              key={preset}
              onClick={() => setNote(preset)}
              className="rounded-full border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-gray-100"
            >
              {preset}
            </button>
          ))}
        </div>
      </div>

      {/* Entries list */}
      <div className="mt-4">
        {isLoading ? (
          <div className="py-4 text-center text-sm text-gray-400">Loading...</div>
        ) : entries.length === 0 ? (
          <div
            data-testid="blocklist-empty"
            className="py-4 text-center text-sm text-gray-400"
          >
            No companies blocklisted yet.
          </div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {entries.map((entry) => (
              <li
                key={entry.id}
                data-testid={`blocklist-entry-${entry.id}`}
                className="flex items-center justify-between py-3"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {entry.company_name}
                  </p>
                  {entry.note && (
                    <p className="text-xs text-gray-500">{entry.note}</p>
                  )}
                </div>
                <button
                  data-testid={`blocklist-remove-${entry.id}`}
                  onClick={() => handleRemove(entry.id)}
                  className="text-sm text-red-600 hover:text-red-800"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
