/**
 * Matches page - Tinder-style swipe interface for reviewing job matches.
 *
 * Displays a stack of SwipeCard components for unreviewed ("new") matches.
 * Supports swipe gestures, keyboard shortcuts, and detail expansion.
 */

import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import SwipeCard from '../components/matches/SwipeCard';
import MatchDetail from '../components/matches/MatchDetail';
import TopPickCard from '../components/matches/TopPickCard';
import LearnedPreferenceBanner from '../components/matches/LearnedPreferenceBanner';
import { useMatches, useTopPick, useUpdateMatchStatus } from '../services/matches';

export default function Matches() {
  const { data, isLoading, isError } = useMatches('new');
  const { data: topPick } = useTopPick();
  const updateStatus = useUpdateMatchStatus();

  const [expandedId, setExpandedId] = useState<string | null>(null);

  const handleTopPickSave = useCallback(() => {
    if (!topPick) return;
    updateStatus.mutate({ matchId: topPick.id, status: 'saved' });
  }, [topPick, updateStatus]);

  const handleTopPickDismiss = useCallback(() => {
    if (!topPick) return;
    updateStatus.mutate({ matchId: topPick.id, status: 'dismissed' });
  }, [topPick, updateStatus]);

  const matches = data?.data ?? [];
  const currentMatch = matches[0] ?? null;

  const handleSave = useCallback(() => {
    if (!currentMatch) return;
    updateStatus.mutate({ matchId: currentMatch.id, status: 'saved' });
    setExpandedId(null);
    // Optimistic update removes the item from matches[], shifting the array.
    // Keep currentIndex the same so the next item (which slid into this position) is shown.
  }, [currentMatch, updateStatus]);

  const handleDismiss = useCallback(() => {
    if (!currentMatch) return;
    updateStatus.mutate({ matchId: currentMatch.id, status: 'dismissed' });
    setExpandedId(null);
    // Same as handleSave — no index increment needed since optimistic update shifts array.
  }, [currentMatch, updateStatus]);

  const handleToggleExpand = useCallback(() => {
    if (!currentMatch) return;
    setExpandedId((prev) => (prev === currentMatch.id ? null : currentMatch.id));
  }, [currentMatch]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') {
        e.preventDefault();
        handleSave();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        handleDismiss();
      } else if (e.key === ' ') {
        e.preventDefault();
        handleToggleExpand();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSave, handleDismiss, handleToggleExpand]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-full max-w-md mx-auto space-y-4">
          {/* Skeleton cards */}
          {[1, 2].map((i) => (
            <div
              key={i}
              className="bg-white rounded-2xl shadow-lg p-6 animate-pulse"
              style={{ opacity: 1 - i * 0.3 }}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="h-4 w-24 bg-gray-200 rounded mb-2" />
                  <div className="h-6 w-48 bg-gray-200 rounded" />
                </div>
                <div className="w-14 h-14 bg-gray-200 rounded-full" />
              </div>
              <div className="h-4 w-32 bg-gray-200 rounded mb-3" />
              <div className="h-4 w-40 bg-gray-200 rounded mb-4" />
              <div className="h-5 w-28 bg-gray-200 rounded-full" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Unable to load matches</h2>
          <p className="text-gray-600">Please try refreshing the page.</p>
        </div>
      </div>
    );
  }

  // Empty state
  if (!currentMatch) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]" data-testid="empty-state">
        <div className="text-center max-w-md mx-auto">
          <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-indigo-100 flex items-center justify-center">
            <svg className="w-10 h-10 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-3">All caught up!</h2>
          <p className="text-gray-600 mb-6">
            Your agent is finding more matches. Check back soon or adjust your preferences to broaden your search.
          </p>
          <Link
            to="/preferences"
            className="inline-flex items-center px-4 py-2 rounded-lg bg-indigo-600 text-white font-medium hover:bg-indigo-700 transition-colors"
          >
            Adjust Preferences
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center min-h-[60vh] py-8">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Job Matches</h1>
        <p className="text-sm text-gray-500 mt-1">
          {matches.length} match{matches.length !== 1 ? 'es' : ''} to review
        </p>
      </div>

      {/* Learned Preferences Banner */}
      <LearnedPreferenceBanner />

      {/* Top Pick */}
      {topPick && (
        <div className="mb-8">
          <TopPickCard
            match={topPick}
            onSave={handleTopPickSave}
            onDismiss={handleTopPickDismiss}
          />
        </div>
      )}

      {/* Card stack */}
      <div className="relative w-full max-w-md mx-auto">
        <AnimatePresence mode="wait">
          <SwipeCard
            key={currentMatch.id}
            match={currentMatch}
            onSwipeLeft={handleDismiss}
            onSwipeRight={handleSave}
            onTap={handleToggleExpand}
            isExpanded={expandedId === currentMatch.id}
          />
        </AnimatePresence>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-6 mt-6">
        <button
          onClick={handleDismiss}
          className="w-14 h-14 rounded-full bg-red-100 text-red-600 hover:bg-red-200 flex items-center justify-center transition-colors shadow-md"
          aria-label="Dismiss"
          data-testid="dismiss-button"
        >
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <button
          onClick={handleToggleExpand}
          className="w-10 h-10 rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200 flex items-center justify-center transition-colors shadow-sm"
          aria-label="Toggle details"
          data-testid="expand-button"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </button>
        <button
          onClick={handleSave}
          className="w-14 h-14 rounded-full bg-green-100 text-green-600 hover:bg-green-200 flex items-center justify-center transition-colors shadow-md"
          aria-label="Save"
          data-testid="save-button"
        >
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
        </button>
      </div>

      {/* Expanded detail */}
      <AnimatePresence>
        {expandedId === currentMatch.id && (
          <MatchDetail match={currentMatch} />
        )}
      </AnimatePresence>

      {/* Keyboard hint */}
      <div className="mt-8 text-xs text-gray-400 text-center" data-testid="keyboard-hint">
        <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-500 font-mono">←</kbd> Dismiss
        <span className="mx-3">|</span>
        <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-500 font-mono">→</kbd> Save
        <span className="mx-3">|</span>
        <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-500 font-mono">Space</kbd> Details
      </div>
    </div>
  );
}
