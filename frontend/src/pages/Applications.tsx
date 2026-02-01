/**
 * Applications page -- shows application history or empty state.
 *
 * Story 5-14: Provides an encouraging empty state when no applications exist,
 * with a CTA to review matches and a helpful tip.
 */

import { Link } from 'react-router-dom';
import { useApplications } from '../services/applications';

export default function Applications() {
  const { data, isLoading, isError } = useApplications();

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg bg-red-50 p-6 text-center">
        <p className="text-red-600">Failed to load applications. Please try again.</p>
      </div>
    );
  }

  const applications = data?.applications ?? [];

  // Empty state
  if (applications.length === 0) {
    return (
      <div data-testid="empty-state" className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-white p-12 text-center">
        <div className="mb-4 text-5xl">📋</div>
        <h2 className="text-xl font-semibold text-gray-900">
          No applications yet. Let's change that!
        </h2>
        <p data-testid="empty-tip" className="mt-3 max-w-md text-sm text-gray-500">
          Save jobs you like, then approve applications in your briefing.
        </p>
        <Link
          to="/matches"
          data-testid="review-matches-cta"
          className="mt-6 inline-flex items-center rounded-md bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
        >
          Review your matches
        </Link>
      </div>
    );
  }

  // Application list (basic table for now)
  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Applications</h1>
      <div className="overflow-hidden rounded-lg bg-white shadow">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Job</th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Company</th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Applied</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {applications.map((app) => (
              <tr key={app.id}>
                <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">
                  {app.job_title ?? 'Untitled'}
                </td>
                <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                  {app.company ?? '—'}
                </td>
                <td className="whitespace-nowrap px-6 py-4">
                  <span className="inline-flex rounded-full bg-green-100 px-2 text-xs font-semibold leading-5 text-green-800">
                    {app.status}
                  </span>
                </td>
                <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                  {app.applied_at ? new Date(app.applied_at).toLocaleDateString() : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
