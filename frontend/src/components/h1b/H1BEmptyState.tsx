/**
 * H1B Empty State — guidance when no sponsor data exists for a company.
 */

interface H1BEmptyStateProps {
  company: string;
}

export function H1BEmptyState({ company }: H1BEmptyStateProps) {
  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-6 text-center">
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-gray-200">
        <svg className="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M12 20a8 8 0 100-16 8 8 0 000 16z" />
        </svg>
      </div>

      <h3 className="mb-2 text-base font-semibold text-gray-900">
        No sponsorship data found for {company}
      </h3>

      <ul className="mb-4 space-y-1 text-sm text-gray-600">
        <li>This may be a new company or one that hasn't sponsored recently</li>
        <li>Check the company's careers page for sponsorship policy</li>
        <li>Ask during the interview process</li>
      </ul>

      <div className="flex flex-col gap-2 sm:flex-row sm:justify-center">
        <button
          disabled
          title="Coming soon"
          className="rounded-md border border-indigo-300 bg-white px-4 py-2 text-sm font-medium text-indigo-600 opacity-60 cursor-not-allowed"
        >
          Notify me when data becomes available
        </button>
        <button
          disabled
          title="Coming soon"
          className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 opacity-60 cursor-not-allowed"
        >
          Share anonymous tip
        </button>
      </div>
    </div>
  );
}
