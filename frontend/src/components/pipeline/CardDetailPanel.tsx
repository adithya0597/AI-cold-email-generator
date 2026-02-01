/**
 * Slide-over detail panel for a pipeline application card.
 *
 * Opens on card click, closes on overlay click or Escape key.
 */

import { useEffect } from 'react';
import type { ApplicationItem } from '../../services/applications';

interface CardDetailPanelProps {
  application: ApplicationItem;
  onClose: () => void;
}

export default function CardDetailPanel({ application, onClose }: CardDetailPanelProps) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <div
      data-testid="detail-panel-overlay"
      className="fixed inset-0 z-50 flex justify-end"
      onClick={onClose}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/30" />

      {/* Panel */}
      <div
        data-testid="detail-panel"
        className="relative w-full max-w-md bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex h-full flex-col overflow-y-auto p-6">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {application.job_title ?? 'Untitled Position'}
              </h2>
              <p className="mt-1 text-sm text-gray-500">
                {application.company ?? 'Unknown Company'}
              </p>
            </div>
            <button
              data-testid="close-panel"
              onClick={onClose}
              className="rounded-md p-1 text-gray-400 hover:text-gray-600"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Details */}
          <dl className="mt-6 space-y-4">
            <div>
              <dt className="text-xs font-medium uppercase text-gray-500">Status</dt>
              <dd className="mt-1">
                <span className="inline-flex rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-semibold text-green-800">
                  {application.status}
                </span>
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase text-gray-500">Applied</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {application.applied_at ? new Date(application.applied_at).toLocaleDateString() : '--'}
              </dd>
            </div>
            {application.last_updated_by && (
              <div>
                <dt className="text-xs font-medium uppercase text-gray-500">Last Updated By</dt>
                <dd className="mt-1 text-sm text-gray-900">{application.last_updated_by}</dd>
              </div>
            )}
          </dl>
        </div>
      </div>
    </div>
  );
}
