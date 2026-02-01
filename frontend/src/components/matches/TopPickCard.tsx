/**
 * TopPickCard - Featured "Top Pick of the Day" card.
 *
 * Displays the highest-scoring match with enhanced styling:
 * gradient border, star badge, extended rationale, and action buttons.
 */

import { motion } from 'framer-motion';
import { FiStar } from 'react-icons/fi';
import type { MatchData } from '../../types/matches';

interface TopPickCardProps {
  match: MatchData;
  onSave: () => void;
  onDismiss: () => void;
}

function formatSalary(min: number | null, max: number | null): string {
  if (min == null && max == null) return 'Not specified';
  const fmt = (n: number) => `$${(n / 1000).toFixed(0)}k`;
  if (min != null && max != null) return `${fmt(min)} - ${fmt(max)}`;
  if (min != null) return `${fmt(min)}+`;
  return `Up to ${fmt(max!)}`;
}

function scoreColor(score: number): string {
  if (score >= 75) return 'bg-green-500 text-white';
  if (score >= 50) return 'bg-amber-500 text-white';
  return 'bg-red-500 text-white';
}

export default function TopPickCard({ match, onSave, onDismiss }: TopPickCardProps) {
  const { job, score, rationale } = match;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="border-2 border-indigo-300 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-2xl shadow-lg p-6 w-full max-w-lg mx-auto"
      data-testid="top-pick-card"
    >
      {/* Star badge */}
      <div
        className="flex items-center gap-2 mb-4"
        data-testid="top-pick-badge"
      >
        <FiStar className="h-5 w-5 text-indigo-600 fill-indigo-600" />
        <span className="text-sm font-semibold text-indigo-700">Top Pick of the Day</span>
      </div>

      {/* Header: title + score */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-indigo-600 truncate" data-testid="top-pick-company">
            {job.company}
          </p>
          <h3 className="text-xl font-bold text-gray-900 mt-1" data-testid="top-pick-title">
            {job.title}
          </h3>
        </div>
        <div
          className={`flex-shrink-0 ml-3 inline-flex items-center justify-center w-16 h-16 rounded-full text-xl font-bold ${scoreColor(score)}`}
          data-testid="top-pick-score"
        >
          {score}%
        </div>
      </div>

      {/* Location */}
      <div className="flex items-center gap-2 text-sm text-gray-600 mb-3">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <span>{job.location || 'Location not specified'}</span>
        {job.remote && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            Remote
          </span>
        )}
      </div>

      {/* Salary */}
      <div className="flex items-center gap-2 text-sm text-gray-600 mb-5">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>{formatSalary(job.salary_min, job.salary_max)}</span>
      </div>

      {/* Extended rationale */}
      <div className="bg-white/60 rounded-xl p-4 mb-5">
        <h4 className="text-sm font-semibold text-gray-900 mb-2">
          Here&apos;s why this is your #1 match today
        </h4>
        {rationale.summary && (
          <p
            className="text-sm italic text-gray-600 mb-3"
            data-testid="top-pick-rationale-summary"
          >
            {rationale.summary}
          </p>
        )}
        {rationale.top_reasons.length > 0 && (
          <ul className="space-y-1.5 mb-3" data-testid="top-pick-reasons">
            {rationale.top_reasons.map((reason, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <svg className="w-4 h-4 text-green-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                {reason}
              </li>
            ))}
          </ul>
        )}
        {rationale.concerns.length > 0 && (
          <ul className="space-y-1.5">
            {rationale.concerns.map((concern, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                <svg className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.072 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                {concern}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex items-center justify-center gap-6">
        <button
          onClick={onDismiss}
          className="w-14 h-14 rounded-full bg-red-100 text-red-600 hover:bg-red-200 flex items-center justify-center transition-colors shadow-md"
          aria-label="Dismiss"
          data-testid="top-pick-dismiss"
        >
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <button
          onClick={onSave}
          className="w-14 h-14 rounded-full bg-green-100 text-green-600 hover:bg-green-200 flex items-center justify-center transition-colors shadow-md"
          aria-label="Save"
          data-testid="top-pick-save"
        >
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
        </button>
      </div>
    </motion.div>
  );
}
