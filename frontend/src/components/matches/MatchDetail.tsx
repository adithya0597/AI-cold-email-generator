/**
 * MatchDetail - Expanded view showing job description and match rationale.
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

export default function MatchDetail({ match }: MatchDetailProps) {
  const { job, rationale } = match;
  const truncatedDescription = job.description
    ? job.description.length > 500
      ? job.description.slice(0, 500) + '...'
      : job.description
    : 'No description available.';

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
          <p className="text-sm text-gray-600 leading-relaxed" data-testid="job-description">
            {truncatedDescription}
          </p>
        </div>

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
