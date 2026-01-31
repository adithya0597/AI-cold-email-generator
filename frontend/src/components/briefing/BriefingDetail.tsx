/**
 * BriefingDetail -- full-page view for a single briefing.
 *
 * Accessed from briefing history or "View Full Briefing" link.
 * Shows complete briefing content with all sections expanded.
 * Provides Previous/Next navigation between briefings.
 */

import { useParams, useNavigate, Link } from 'react-router-dom';
import { useUser } from '@clerk/clerk-react';
import {
  FiArrowLeft,
  FiChevronLeft,
  FiChevronRight,
  FiBriefcase,
  FiAlertCircle,
  FiActivity,
  FiCheck,
  FiClock,
  FiStar,
} from 'react-icons/fi';
import { useBriefing, useMarkBriefingRead } from '../../services/briefings';

export default function BriefingDetail() {
  const { briefingId } = useParams<{ briefingId: string }>();
  const { user } = useUser();
  const navigate = useNavigate();
  const userId = user?.id;

  const { data: briefing, isLoading, error } = useBriefing(userId, briefingId);
  const markRead = useMarkBriefingRead(userId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <div className="text-gray-500">Loading briefing...</div>
      </div>
    );
  }

  if (error || !briefing) {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-8 text-center">
          <p className="text-gray-500">Briefing not found.</p>
          <Link
            to="/briefings"
            className="mt-4 inline-flex items-center text-sm text-indigo-600 hover:text-indigo-800"
          >
            <FiArrowLeft className="mr-1" />
            Back to History
          </Link>
        </div>
      </div>
    );
  }

  const content = briefing.content;
  const metrics = content.metrics;
  const isLite = briefing.briefing_type === 'lite';
  const isUnread = !briefing.read_at;

  const handleMarkRead = () => {
    markRead.mutate(briefing.id);
  };

  return (
    <div className="max-w-3xl mx-auto">
      {/* Back link */}
      <div className="mb-4">
        <button
          onClick={() => navigate('/briefings')}
          className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
        >
          <FiArrowLeft className="mr-1" />
          Back to Briefing History
        </button>
      </div>

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        {/* Header */}
        <div
          className={`px-6 py-5 ${
            isLite
              ? 'bg-gradient-to-r from-amber-50 to-yellow-50'
              : 'bg-gradient-to-r from-indigo-50 to-blue-50'
          }`}
        >
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">
                Daily Briefing
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                {new Date(briefing.generated_at).toLocaleDateString('en-US', {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </p>
              {isLite && (
                <p className="text-sm text-amber-700 mt-2">
                  This is a lite briefing generated from cached data.
                </p>
              )}
            </div>
            <div className="flex items-center gap-2">
              {isUnread && (
                <button
                  onClick={handleMarkRead}
                  disabled={markRead.isPending}
                  className="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md text-indigo-700 bg-indigo-100 hover:bg-indigo-200 disabled:opacity-50"
                >
                  <FiCheck className="mr-1" />
                  Mark as Read
                </button>
              )}
              <span
                className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                  isLite
                    ? 'bg-amber-100 text-amber-800'
                    : 'bg-indigo-100 text-indigo-800'
                }`}
              >
                {isLite ? 'Lite' : 'Full'}
              </span>
            </div>
          </div>

          {/* Metrics */}
          {metrics && (
            <div className="grid grid-cols-3 gap-3 mt-4">
              {metrics.total_matches !== undefined && (
                <div className="bg-blue-50 rounded-lg p-3 text-center">
                  <FiBriefcase className="h-5 w-5 text-blue-600 mx-auto mb-1" />
                  <p className="text-lg font-bold text-blue-900">
                    {metrics.total_matches}
                  </p>
                  <p className="text-xs text-blue-600">New Matches</p>
                </div>
              )}
              {metrics.pending_approvals !== undefined && (
                <div className="bg-amber-50 rounded-lg p-3 text-center">
                  <FiAlertCircle className="h-5 w-5 text-amber-600 mx-auto mb-1" />
                  <p className="text-lg font-bold text-amber-900">
                    {metrics.pending_approvals}
                  </p>
                  <p className="text-xs text-amber-600">Pending Approvals</p>
                </div>
              )}
              {metrics.applications_sent !== undefined && (
                <div className="bg-green-50 rounded-lg p-3 text-center">
                  <FiCheck className="h-5 w-5 text-green-600 mx-auto mb-1" />
                  <p className="text-lg font-bold text-green-900">
                    {metrics.applications_sent}
                  </p>
                  <p className="text-xs text-green-600">Applications Sent</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Content sections (all expanded in detail view) */}
        <div className="px-6 py-5 space-y-6">
          {/* Summary */}
          {content.summary && (
            <section>
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Summary
              </h2>
              <p className="text-gray-700">{content.summary}</p>
            </section>
          )}

          {/* Actions Needed */}
          {content.actions_needed && content.actions_needed.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Actions Needed
              </h2>
              <ul className="space-y-2">
                {content.actions_needed.map((action, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-gray-700 bg-amber-50 p-3 rounded-lg"
                  >
                    <FiAlertCircle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                    {action}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* New Matches */}
          {content.new_matches && content.new_matches.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
                New Matches
              </h2>
              <div className="space-y-2">
                {content.new_matches.map((match, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {match.title}
                      </p>
                      <p className="text-xs text-gray-500">{match.company}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {match.match_score !== undefined && (
                        <span className="text-xs font-medium text-green-700 bg-green-100 px-2 py-1 rounded-full">
                          {match.match_score}% match
                        </span>
                      )}
                      {match.url && (
                        <a
                          href={match.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-indigo-600 hover:text-indigo-800"
                        >
                          View
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Activity Log */}
          {content.activity_log && content.activity_log.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Activity Log
              </h2>
              <div className="space-y-2">
                {content.activity_log.map((entry, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between text-sm p-2 border-b border-gray-100 last:border-0"
                  >
                    <div className="flex items-center gap-2">
                      <FiActivity className="h-4 w-4 text-gray-400" />
                      <span className="text-gray-700">{entry.event}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-gray-400">
                      {entry.agent_type && (
                        <span className="bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                          {entry.agent_type}
                        </span>
                      )}
                      <FiClock className="h-3 w-3" />
                      {new Date(entry.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Tips */}
          {content.tips && content.tips.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Tips
              </h2>
              <ul className="space-y-1.5">
                {content.tips.map((tip, i) => (
                  <li
                    key={i}
                    className="text-sm text-gray-600 flex items-start gap-2"
                  >
                    <FiStar className="h-3.5 w-3.5 text-indigo-400 mt-0.5 shrink-0" />
                    {tip}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Message (simple text content) */}
          {content.message && !content.summary && (
            <section>
              <p className="text-gray-700">{content.message}</p>
            </section>
          )}
        </div>

        {/* Footer with delivery info */}
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-100 flex items-center justify-between text-xs text-gray-400">
          <div className="flex items-center gap-1.5">
            <FiClock className="h-3.5 w-3.5" />
            Generated {new Date(briefing.generated_at).toLocaleString()}
          </div>
          {briefing.delivery_channels.length > 0 && (
            <span>
              Delivered via {briefing.delivery_channels.join(', ')}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
