/**
 * MatchDetail - Expanded view showing full job description, metadata, and match rationale.
 *
 * Displayed below the SwipeCard when the user taps/clicks the card
 * or presses Space. Animates in/out with framer-motion.
 */

import { motion } from 'framer-motion';
import type { MatchData } from '../../types/matches';

interface MatchDetailProps {
  match: MatchData;
}

function confidenceBadgeColor(confidence: string): string {
  switch (confidence) {
    case 'High':
      return 'bg-green-100 text-green-800';
    case 'Medium':
      return 'bg-amber-100 text-amber-800';
    case 'Low':
      return 'bg-red-100 text-red-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHrs = Math.floor(diffMins / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  const diffDays = Math.floor(diffHrs / 24);
  if (diffDays === 1) return 'Yesterday';
  return `${diffDays} days ago`;
}

export default function MatchDetail({ match }: MatchDetailProps) {
  const { job, rationale } = match;

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      className="w-full max-w-md mx-auto mt-4 overflow-hidden"
      data-testid="match-detail"
    >
      <div className="bg-white rounded-2xl shadow-lg p-6 space-y-5">
        {/* Job Description */}
        <div>
          <h4 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-2">
            Job Description
          </h4>
          <div
            className="text-sm text-gray-600 leading-relaxed max-h-64 overflow-y-auto"
            data-testid="job-description"
          >
            {job.description || 'No description available.'}
          </div>
        </div>

        {/* Job Metadata */}
        {(job.employment_type || job.posted_at || job.source) && (
          <div className="flex flex-wrap items-center gap-3 text-sm text-gray-500" data-testid="job-metadata">
            {job.employment_type && (
              <span className="inline-flex items-center gap-1" data-testid="employment-type">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                {job.employment_type}
              </span>
            )}
            {job.posted_at && (
              <span className="inline-flex items-center gap-1" data-testid="posted-at">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                Posted {formatRelativeDate(job.posted_at)}
              </span>
            )}
            {job.source && (
              <span className="inline-flex items-center gap-1" data-testid="job-source">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                {job.source.charAt(0).toUpperCase() + job.source.slice(1)}
              </span>
            )}
          </div>
        )}

        {/* H1B Sponsorship Status */}
        {job.h1b_sponsor_status && job.h1b_sponsor_status !== 'unknown' && (
          <div data-testid="h1b-badge">
            {job.h1b_sponsor_status === 'verified' ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                Verified H1B Sponsor
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.072 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                Unverified Sponsorship
              </span>
            )}
          </div>
        )}

        {/* Why this match? */}
        <div>
          <h4 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
            Why this match?
          </h4>

          {/* Top reasons */}
          {rationale.top_reasons.length > 0 && (
            <ul className="space-y-2 mb-4" data-testid="top-reasons">
              {rationale.top_reasons.map((reason, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                  <svg className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span>{reason}</span>
                </li>
              ))}
            </ul>
          )}

          {/* Concerns */}
          {rationale.concerns.length > 0 && (
            <ul className="space-y-2 mb-4" data-testid="concerns">
              {rationale.concerns.map((concern, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                  <svg className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                  <span>{concern}</span>
                </li>
              ))}
            </ul>
          )}

          {/* Confidence */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Match confidence:</span>
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${confidenceBadgeColor(rationale.confidence)}`}
              data-testid="detail-confidence"
            >
              {rationale.confidence}
            </span>
          </div>
        </div>

        {/* View full posting link */}
        {job.url && (
          <div className="pt-2 border-t border-gray-100">
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-800 transition-colors"
              data-testid="job-link"
            >
              View Full Posting
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
        )}
      </div>
    </motion.div>
  );
}
