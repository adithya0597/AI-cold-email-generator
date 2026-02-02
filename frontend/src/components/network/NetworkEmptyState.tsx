/**
 * Network Empty State — guidance when user hasn't started networking.
 *
 * Shows encouraging messaging about warm introductions with CTAs
 * to import LinkedIn connections and save target companies.
 */

interface NetworkEmptyStateProps {
  onImportLinkedIn?: () => void;
  onSaveTargetCompanies?: () => void;
}

export function NetworkEmptyState({
  onImportLinkedIn,
  onSaveTargetCompanies,
}: NetworkEmptyStateProps) {
  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-6 text-center">
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100">
        <svg
          className="h-6 w-6 text-indigo-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
          />
        </svg>
      </div>

      <h3 className="mb-2 text-base font-semibold text-gray-900">
        Build your professional network strategically
      </h3>

      <p className="mb-4 text-sm text-gray-600">
        Warm introductions are the most effective way to land your next role.
        Quality connections matter more than quantity. Let us help you identify
        the right people and craft the perfect outreach.
      </p>

      <ul className="mb-4 space-y-1 text-sm text-gray-600">
        <li>Discover warm paths to target companies through your connections</li>
        <li>Get AI-crafted introduction messages that feel authentic</li>
        <li>Track relationship warmth so you reach out at the right time</li>
      </ul>

      <div className="flex flex-col gap-2 sm:flex-row sm:justify-center">
        <button
          onClick={onImportLinkedIn}
          disabled={!onImportLinkedIn}
          aria-label="Import your LinkedIn connections"
          className={`rounded-md border border-indigo-300 bg-white px-4 py-2 text-sm font-medium text-indigo-600 ${
            onImportLinkedIn
              ? "hover:bg-indigo-50 cursor-pointer"
              : "opacity-60 cursor-not-allowed"
          }`}
        >
          Import your LinkedIn connections
        </button>
        <button
          onClick={onSaveTargetCompanies}
          disabled={!onSaveTargetCompanies}
          aria-label="Save target companies to find warm paths"
          className={`rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 ${
            onSaveTargetCompanies
              ? "hover:bg-gray-50 cursor-pointer"
              : "opacity-60 cursor-not-allowed"
          }`}
        >
          Save target companies to find warm paths
        </button>
      </div>
    </div>
  );
}
