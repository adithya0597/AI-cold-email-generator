/**
 * BriefingHistory page -- paginated list of past briefings (last 30 days).
 *
 * Each entry shows: date, type (full/lite), read status, summary preview.
 * Click to open BriefingDetail.
 * Includes empty state for new users.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useUser } from '../providers/ClerkProvider';
import {
  FiCalendar,
  FiChevronLeft,
  FiChevronRight,
  FiCheck,
  FiClock,
  FiStar,
  FiSettings,
} from 'react-icons/fi';
import { useBriefingHistory } from '../services/briefings';

const PAGE_SIZE = 20;

export default function BriefingHistory() {
  const { user, isLoaded } = useUser();
  const userId = user?.id;
  const [offset, setOffset] = useState(0);

  const { data, isLoading, error } = useBriefingHistory(
    userId,
    PAGE_SIZE,
    offset,
  );

  if (!isLoaded || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <div className="text-gray-500">Loading briefing history...</div>
      </div>
    );
  }

  const briefings = data?.briefings ?? [];
  const total = data?.total ?? 0;
  const hasMore = data?.has_more ?? false;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Briefing History
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Your daily briefings from the past 30 days
          </p>
        </div>
        <Link
          to="/briefings/settings"
          className="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md text-gray-600 bg-gray-100 hover:bg-gray-200"
        >
          <FiSettings className="mr-1.5" />
          Settings
        </Link>
      </div>

      {/* Empty state */}
      {briefings.length === 0 && !isLoading && (
        <div className="bg-white rounded-lg shadow-md p-8 text-center border border-dashed border-indigo-200">
          <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-indigo-50 mb-4">
            <FiStar className="h-8 w-8 text-indigo-500" />
          </div>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">
            No briefings yet
          </h2>
          <p className="text-gray-600 max-w-md mx-auto">
            Your first daily briefing is being prepared. Each morning, you will
            receive a personalized summary of job matches, application updates,
            and agent activity.
          </p>
          <Link
            to="/dashboard"
            className="mt-4 inline-flex items-center text-sm text-indigo-600 hover:text-indigo-800 font-medium"
          >
            Back to Dashboard
          </Link>
        </div>
      )}

      {/* Briefing list */}
      {briefings.length > 0 && (
        <div className="space-y-3">
          {briefings.map((briefing) => {
            const date = new Date(briefing.generated_at);
            const isUnread = !briefing.read_at;
            const isLite = briefing.briefing_type === 'lite';
            const summary =
              briefing.content.summary ||
              briefing.content.message ||
              'No summary available';
            const previewText =
              summary.length > 150
                ? summary.slice(0, 150) + '...'
                : summary;

            return (
              <Link
                key={briefing.id}
                to={`/briefings/${briefing.id}`}
                className={`block bg-white rounded-lg shadow-sm border p-4 hover:shadow-md transition-shadow ${
                  isUnread
                    ? 'border-indigo-200 bg-indigo-50/30'
                    : 'border-gray-100'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <FiCalendar className="h-4 w-4 text-gray-400 shrink-0" />
                      <span className="text-sm font-medium text-gray-900">
                        {date.toLocaleDateString('en-US', {
                          weekday: 'short',
                          month: 'short',
                          day: 'numeric',
                        })}
                      </span>
                      <span className="text-xs text-gray-400">
                        {date.toLocaleTimeString('en-US', {
                          hour: 'numeric',
                          minute: '2-digit',
                        })}
                      </span>
                      {isLite && (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700">
                          Lite
                        </span>
                      )}
                      {isUnread && (
                        <span className="inline-flex h-2 w-2 rounded-full bg-indigo-500" />
                      )}
                    </div>
                    <p className="text-sm text-gray-600 truncate">
                      {previewText}
                    </p>
                    {briefing.content.metrics && (
                      <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                        {briefing.content.metrics.total_matches !== undefined && (
                          <span>
                            {briefing.content.metrics.total_matches} matches
                          </span>
                        )}
                        {briefing.content.metrics.applications_sent !==
                          undefined && (
                          <span>
                            {briefing.content.metrics.applications_sent} applied
                          </span>
                        )}
                        {briefing.content.metrics.pending_approvals !==
                          undefined &&
                          briefing.content.metrics.pending_approvals > 0 && (
                            <span className="text-amber-500">
                              {briefing.content.metrics.pending_approvals}{' '}
                              pending
                            </span>
                          )}
                      </div>
                    )}
                  </div>
                  <div className="ml-4 shrink-0">
                    {briefing.read_at && (
                      <FiCheck className="h-4 w-4 text-green-500" />
                    )}
                  </div>
                </div>
              </Link>
            );
          })}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-4">
              <button
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                disabled={offset === 0}
                className="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md text-gray-600 bg-gray-100 hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <FiChevronLeft className="mr-1" />
                Previous
              </button>
              <span className="text-sm text-gray-500">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setOffset(offset + PAGE_SIZE)}
                disabled={!hasMore}
                className="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md text-gray-600 bg-gray-100 hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next
                <FiChevronRight className="ml-1" />
              </button>
            </div>
          )}

          <div className="text-center pt-2">
            <p className="text-xs text-gray-400">
              Showing {briefings.length} of {total} briefings from the last 30
              days
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
