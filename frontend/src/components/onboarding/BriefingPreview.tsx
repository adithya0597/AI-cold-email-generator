/**
 * BriefingPreview -- "magic moment" showing what daily briefings will look like.
 *
 * Displays mock briefing data personalized with the user's name.
 * Shows 3 mock job matches with scores, approval actions (grayed out).
 *
 * Story 1-4: Briefing Preview
 */

import { useEffect } from 'react';
import { useAnalytics } from '../../hooks/useAnalytics';

interface BriefingPreviewProps {
  userName: string;
  onContinue: () => void;
}

const MOCK_JOBS = [
  {
    id: 1,
    title: 'Senior Software Engineer',
    company: 'Stripe',
    score: 92,
    location: 'San Francisco, CA (Remote)',
    salary: '$180k - $220k',
    tags: ['TypeScript', 'React', 'Node.js'],
  },
  {
    id: 2,
    title: 'Staff Frontend Engineer',
    company: 'Notion',
    score: 87,
    location: 'New York, NY (Hybrid)',
    salary: '$190k - $240k',
    tags: ['React', 'Performance', 'Design Systems'],
  },
  {
    id: 3,
    title: 'Engineering Manager',
    company: 'Figma',
    score: 84,
    location: 'San Francisco, CA (Remote)',
    salary: '$200k - $260k',
    tags: ['Leadership', 'Frontend', 'Product'],
  },
];

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 90
      ? 'bg-green-100 text-green-700 border-green-200'
      : score >= 85
      ? 'bg-blue-100 text-blue-700 border-blue-200'
      : 'bg-amber-100 text-amber-700 border-amber-200';

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${color}`}
    >
      {score}% match
    </span>
  );
}

export default function BriefingPreview({ userName, onContinue }: BriefingPreviewProps) {
  const { track } = useAnalytics();

  useEffect(() => {
    track('briefing_preview_viewed');
  }, []);

  const firstName = userName.split(' ')[0] || 'there';

  return (
    <div className="space-y-6">
      {/* Preview label */}
      <div className="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-2 text-center">
        <p className="text-sm font-medium text-indigo-700">
          Preview -- Your first real briefing arrives tomorrow
        </p>
      </div>

      {/* Briefing card */}
      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-lg">
        {/* Briefing header */}
        <div className="bg-gradient-to-r from-indigo-600 to-blue-600 px-6 py-5 text-white">
          <p className="text-sm font-medium text-indigo-200">Daily Briefing</p>
          <h2 className="mt-1 text-2xl font-bold">Good morning, {firstName}!</h2>
          <p className="mt-2 text-sm text-indigo-100">
            Your agent found <span className="font-semibold">3 matches</span> while you were
            away
          </p>
        </div>

        {/* Job cards */}
        <div className="divide-y divide-gray-100 px-6">
          {MOCK_JOBS.map((job) => (
            <div key={job.id} className="py-4">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-base font-semibold text-gray-900">{job.title}</h3>
                    <ScoreBadge score={job.score} />
                  </div>
                  <p className="mt-0.5 text-sm font-medium text-gray-600">{job.company}</p>
                  <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500">
                    <span className="inline-flex items-center">
                      <svg className="mr-1 h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
                      </svg>
                      {job.location}
                    </span>
                    <span className="inline-flex items-center">
                      <svg className="mr-1 h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      {job.salary}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {job.tags.map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Approval actions (grayed out) */}
                <div className="ml-4 flex flex-shrink-0 items-center gap-2 opacity-40">
                  <button
                    type="button"
                    disabled
                    className="rounded-full border border-gray-300 p-2 text-gray-400"
                    title="Approve"
                  >
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6.633 10.5c.806 0 1.533-.446 2.031-1.08a9.041 9.041 0 012.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 00.322-1.672V3.226a1 1 0 01.945-.756 2.58 2.58 0 012.48 1.759c.394 1.21.058 2.581-.69 3.625A7.49 7.49 0 0014.5 12H18a2.25 2.25 0 012.25 2.25c0 .39-.1.75-.27 1.067a2.25 2.25 0 01-.963 3.922 2.25 2.25 0 01-1.394 2.78A2.233 2.233 0 0118 21H12.75a4.5 4.5 0 01-2.649-.862L8.225 19" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    disabled
                    className="rounded-full border border-gray-300 p-2 text-gray-400"
                    title="Reject"
                  >
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 15h2.25m8.024-9.75c.011.05.028.1.052.148.591 1.2.924 2.55.924 3.977a8.96 8.96 0 01-.999 4.125m.023-8.25c-.076-.365-.183-.72-.32-1.063A4.5 4.5 0 0015 3H9.375C8.339 3 7.5 3.84 7.5 4.875v.75c0 1.036.84 1.875 1.875 1.875H12M7.5 15l-1.875 1.125a2.236 2.236 0 01-1.39.375H3.75" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Briefing footer */}
        <div className="border-t border-gray-100 bg-gray-50 px-6 py-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500">
              Based on your profile and preferences
            </p>
            <span className="text-xs text-gray-400">Preview data</span>
          </div>
        </div>
      </div>

      {/* Motivational copy */}
      <div className="text-center">
        <h3 className="text-lg font-semibold text-gray-900">
          This is what your mornings will look like
        </h3>
        <p className="mt-2 text-sm text-gray-600 max-w-lg mx-auto">
          Your AI agent works 24/7 to find opportunities that match your skills and preferences.
          Every morning, you'll get a curated briefing with your best matches -- scored, sorted,
          and ready for your review.
        </p>
      </div>

      {/* Continue button */}
      <div className="flex justify-center">
        <button
          type="button"
          onClick={onContinue}
          className="inline-flex items-center rounded-lg bg-indigo-600 px-8 py-3 text-base font-medium text-white shadow-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
        >
          Continue to Preferences
          <svg className="ml-2 h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
          </svg>
        </button>
      </div>
    </div>
  );
}
