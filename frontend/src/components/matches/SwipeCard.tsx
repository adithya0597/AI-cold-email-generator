/**
 * SwipeCard - A draggable card for reviewing job matches.
 *
 * Supports horizontal drag gestures with rotation tilt and
 * colored overlays indicating save (green/right) or dismiss (red/left).
 */

import { motion, useMotionValue, useTransform } from 'framer-motion';
import type { MatchData } from '../../types/matches';

interface SwipeCardProps {
  match: MatchData;
  onSwipeLeft: () => void;
  onSwipeRight: () => void;
  onTap: () => void;
  isExpanded: boolean;
}

function formatSalary(min: number | null, max: number | null): string {
  if (min == null && max == null) return 'Not specified';
  const fmt = (n: number) => `$${(n / 1000).toFixed(0)}k`;
  if (min != null && max != null) return `${fmt(min)} - ${fmt(max)}`;
  if (min != null) return `${fmt(min)}+`;
  return `Up to ${fmt(max!)}`;
}

function confidenceColor(confidence: string): string {
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

function scoreColor(score: number): string {
  if (score >= 75) return 'bg-green-500 text-white';
  if (score >= 50) return 'bg-amber-500 text-white';
  return 'bg-red-500 text-white';
}

export default function SwipeCard({
  match,
  onSwipeLeft,
  onSwipeRight,
  onTap,
  isExpanded,
}: SwipeCardProps) {
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-200, 0, 200], [-15, 0, 15]);
  const saveOpacity = useTransform(x, [0, 100, 200], [0, 0.5, 1]);
  const dismissOpacity = useTransform(x, [-200, -100, 0], [1, 0.5, 0]);

  const handleDragEnd = (
    _event: MouseEvent | TouchEvent | PointerEvent,
    info: { offset: { x: number } },
  ) => {
    if (info.offset.x > 150) {
      onSwipeRight();
    } else if (info.offset.x < -150) {
      onSwipeLeft();
    }
  };

  const { job, score, rationale } = match;

  return (
    <motion.div
      className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md mx-auto cursor-grab active:cursor-grabbing select-none relative"
      style={{ x, rotate }}
      drag="x"
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={0.8}
      onDragEnd={handleDragEnd}
      onClick={(e) => {
        // Only fire tap if not dragging
        const motionX = x.get();
        if (Math.abs(motionX) < 5) {
          onTap();
        }
      }}
      whileTap={{ scale: 1.02 }}
      data-testid="swipe-card"
    >
      {/* Save overlay */}
      <motion.div
        className="absolute inset-0 rounded-2xl bg-green-500/20 flex items-center justify-center pointer-events-none"
        style={{ opacity: saveOpacity }}
      >
        <span className="text-green-600 font-bold text-3xl border-4 border-green-600 rounded-lg px-4 py-2 rotate-[-15deg]">
          SAVE
        </span>
      </motion.div>

      {/* Dismiss overlay */}
      <motion.div
        className="absolute inset-0 rounded-2xl bg-red-500/20 flex items-center justify-center pointer-events-none"
        style={{ opacity: dismissOpacity }}
      >
        <span className="text-red-600 font-bold text-3xl border-4 border-red-600 rounded-lg px-4 py-2 rotate-[15deg]">
          DISMISS
        </span>
      </motion.div>

      {/* Card header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-indigo-600 truncate" data-testid="company">
            {job.company}
          </p>
          <h3 className="text-xl font-bold text-gray-900 mt-1" data-testid="job-title">
            {job.title}
          </h3>
        </div>
        <div
          className={`flex-shrink-0 ml-3 inline-flex items-center justify-center w-14 h-14 rounded-full text-lg font-bold ${scoreColor(score)}`}
          data-testid="score-badge"
        >
          {score}%
        </div>
      </div>

      {/* Location */}
      <div className="flex items-center gap-2 text-sm text-gray-600 mb-3" data-testid="location">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <span>{job.location || 'Location not specified'}</span>
        {job.remote && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800" data-testid="remote-badge">
            Remote
          </span>
        )}
      </div>

      {/* Salary */}
      <div className="flex items-center gap-2 text-sm text-gray-600 mb-4" data-testid="salary">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>{formatSalary(job.salary_min, job.salary_max)}</span>
      </div>

      {/* Confidence badge */}
      <div className="flex items-center gap-2">
        <span
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${confidenceColor(rationale.confidence)}`}
          data-testid="confidence-badge"
        >
          {rationale.confidence} confidence
        </span>
      </div>

      {/* Expand hint */}
      {!isExpanded && (
        <p className="text-xs text-gray-400 text-center mt-4">
          Tap for details
        </p>
      )}
    </motion.div>
  );
}
