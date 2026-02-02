/**
 * Enterprise Empty State — guided setup for enterprise admin dashboard.
 *
 * Shows a step-by-step setup guide with progress tracking for
 * configuring an organization's career transition program.
 * Returns null when all steps are complete (parent shows full dashboard).
 */

const SETUP_STEPS = [
  {
    number: 1,
    title: "Upload company logo",
    description:
      "Add your organization's logo to personalize the employee experience.",
  },
  {
    number: 2,
    title: "Customize welcome message",
    description:
      "Write a supportive message employees see when they first log in.",
  },
  {
    number: 3,
    title: "Set autonomy defaults",
    description:
      "Choose how much automation employees get by default for job searching and applications.",
  },
  {
    number: 4,
    title: "Upload employee list",
    description:
      "Import your employees so they can access the career transition program.",
  },
] as const;

const TOTAL_STEPS = SETUP_STEPS.length;

interface EnterpriseEmptyStateProps {
  completedSteps: Set<number>;
  onStepAction: (stepNumber: number) => void;
  helpUrl?: string;
}

export function EnterpriseEmptyState({
  completedSteps,
  onStepAction,
  helpUrl = "#",
}: EnterpriseEmptyStateProps) {
  const completedCount = SETUP_STEPS.filter((s) =>
    completedSteps.has(s.number)
  ).length;
  const percentage = Math.round((completedCount / TOTAL_STEPS) * 100);

  // AC6: Return null when all steps are complete
  if (completedCount === TOTAL_STEPS) {
    return null;
  }

  // Find the first incomplete step for aria-current
  const firstIncompleteStep = SETUP_STEPS.find(
    (s) => !completedSteps.has(s.number)
  );

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-6">
      {/* Heading section */}
      <div className="mb-6 text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100">
          <svg
            className="h-6 w-6 text-indigo-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
            />
          </svg>
        </div>
        <h3 className="mb-2 text-lg font-semibold text-gray-900">
          Set up your organization's career transition program
        </h3>
        <p className="text-sm text-gray-600">
          Complete these steps to get your team up and running. It only takes a
          few minutes.
        </p>
      </div>

      {/* Progress tracker */}
      <div className="mb-6">
        <div className="mb-2 flex items-center justify-between text-sm text-gray-700">
          <span>
            {completedCount} of {TOTAL_STEPS} steps complete &mdash;{" "}
            {percentage}%
          </span>
        </div>
        <div
          role="progressbar"
          aria-valuenow={percentage}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Setup progress: ${percentage}% complete`}
          className="h-2 w-full overflow-hidden rounded-full bg-gray-200"
        >
          <div
            className="h-full rounded-full bg-indigo-500 transition-all duration-300"
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>

      {/* Setup steps */}
      <ol className="mb-6 space-y-3">
        {SETUP_STEPS.map((step) => {
          const isCompleted = completedSteps.has(step.number);
          const isActive = step.number === firstIncompleteStep?.number;

          return (
            <li
              key={step.number}
              className={`flex items-start gap-3 rounded-md border p-3 ${
                isCompleted
                  ? "border-green-200 bg-green-50"
                  : isActive
                    ? "border-indigo-200 bg-white"
                    : "border-gray-200 bg-white"
              }`}
              aria-current={isActive ? "step" : undefined}
            >
              {/* Step number / checkmark */}
              <div className="flex-shrink-0">
                {isCompleted ? (
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-green-500">
                    <svg
                      className="h-4 w-4 text-white"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  </div>
                ) : (
                  <div
                    className={`flex h-7 w-7 items-center justify-center rounded-full text-sm font-medium ${
                      isActive
                        ? "bg-indigo-500 text-white"
                        : "bg-gray-200 text-gray-600"
                    }`}
                  >
                    {step.number}
                  </div>
                )}
              </div>

              {/* Step content */}
              <div className="flex-1">
                <p
                  className={`text-sm font-medium ${
                    isCompleted ? "text-green-800" : "text-gray-900"
                  }`}
                >
                  {step.title}
                </p>
                <p
                  className={`text-xs ${
                    isCompleted ? "text-green-600" : "text-gray-500"
                  }`}
                >
                  {step.description}
                </p>
              </div>

              {/* Action button */}
              {!isCompleted && (
                <button
                  onClick={() => onStepAction(step.number)}
                  aria-label={`${step.title}`}
                  className={`flex-shrink-0 rounded-md px-3 py-1.5 text-xs font-medium ${
                    isActive
                      ? "bg-indigo-500 text-white hover:bg-indigo-600"
                      : "border border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  {isActive ? "Start" : "Set up"}
                </button>
              )}
            </li>
          );
        })}
      </ol>

      {/* Help link */}
      <div className="text-center">
        <a
          href={helpUrl}
          className="text-sm text-indigo-600 hover:text-indigo-500"
        >
          Need help getting started?
        </a>
      </div>
    </div>
  );
}
