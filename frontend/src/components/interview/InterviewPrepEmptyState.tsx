/**
 * Interview Prep Empty State — guidance when no upcoming interviews exist.
 *
 * Shows an encouraging message with tips about calendar connection and
 * a link to practice questions.
 */

interface InterviewPrepEmptyStateProps {
  onConnectCalendar?: () => void;
  onPracticeQuestions?: () => void;
}

export function InterviewPrepEmptyState({
  onConnectCalendar,
  onPracticeQuestions,
}: InterviewPrepEmptyStateProps) {
  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-6 text-center">
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100">
        <svg
          className="h-6 w-6 text-indigo-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
      </div>

      <h3 className="mb-2 text-base font-semibold text-gray-900">
        No interviews scheduled yet
      </h3>

      <p className="mb-4 text-sm text-gray-600">
        When you have upcoming interviews, we'll prepare personalized briefings
        with company research, interviewer insights, and practice questions.
        You've got this!
      </p>

      <ul className="mb-4 space-y-1 text-sm text-gray-600">
        <li>Connect your calendar to auto-detect interviews</li>
        <li>Practice with common interview questions anytime</li>
        <li>Briefings are delivered 24 hours before your interview</li>
      </ul>

      <div className="flex flex-col gap-2 sm:flex-row sm:justify-center">
        <button
          onClick={onConnectCalendar}
          disabled={!onConnectCalendar}
          className={`rounded-md border border-indigo-300 bg-white px-4 py-2 text-sm font-medium text-indigo-600 ${
            onConnectCalendar
              ? "hover:bg-indigo-50 cursor-pointer"
              : "opacity-60 cursor-not-allowed"
          }`}
        >
          Connect Calendar
        </button>
        <button
          onClick={onPracticeQuestions}
          disabled={!onPracticeQuestions}
          className={`rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 ${
            onPracticeQuestions
              ? "hover:bg-gray-50 cursor-pointer"
              : "opacity-60 cursor-not-allowed"
          }`}
        >
          Practice Questions
        </button>
      </div>
    </div>
  );
}
