/**
 * H1B Filter — filter jobs by sponsorship status.
 *
 * Persists selection to localStorage for cross-session persistence.
 */

import { useState } from 'react';

export type H1BFilterValue = 'all' | 'verified_only' | 'high_approval' | 'any_history';

export const H1B_FILTER_KEY = 'jobpilot_h1b_filter';

const FILTER_OPTIONS: { value: H1BFilterValue; label: string; description: string }[] = [
  { value: 'all', label: 'All jobs', description: 'Show all jobs regardless of sponsorship' },
  { value: 'verified_only', label: 'Verified sponsors only', description: 'Only companies with confirmed H1B history' },
  { value: 'high_approval', label: 'High approval rate (80%+)', description: 'Companies with strong approval rates' },
  { value: 'any_history', label: 'Any sponsorship history', description: 'Any company that has sponsored before' },
];

interface H1BFilterProps {
  onFilterChange: (value: H1BFilterValue) => void;
}

export function H1BFilter({ onFilterChange }: H1BFilterProps) {
  const [selected, setSelected] = useState<H1BFilterValue>(() => {
    const stored = localStorage.getItem(H1B_FILTER_KEY);
    if (stored && FILTER_OPTIONS.some((o) => o.value === stored)) {
      return stored as H1BFilterValue;
    }
    return 'all';
  });

  function handleChange(value: H1BFilterValue) {
    setSelected(value);
    localStorage.setItem(H1B_FILTER_KEY, value);
    onFilterChange(value);
  }

  return (
    <fieldset className="rounded-lg border border-gray-200 bg-white p-4">
      <legend className="px-1 text-sm font-semibold text-gray-900">H1B Sponsorship Filter</legend>
      <div className="mt-2 space-y-2">
        {FILTER_OPTIONS.map((option) => (
          <label
            key={option.value}
            className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 hover:bg-gray-50"
          >
            <input
              type="radio"
              name="h1b-filter"
              value={option.value}
              checked={selected === option.value}
              onChange={() => handleChange(option.value)}
              className="h-4 w-4 border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <div>
              <span className="text-sm font-medium text-gray-700">{option.label}</span>
              <p className="text-xs text-gray-500">{option.description}</p>
            </div>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
