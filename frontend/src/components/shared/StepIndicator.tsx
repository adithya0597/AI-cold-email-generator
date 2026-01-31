/**
 * StepIndicator -- horizontal progress bar with numbered steps.
 *
 * Shows current step highlighted, completed steps with a checkmark.
 * Responsive: collapses to "Step X of Y" on mobile.
 */

import React from 'react';

interface StepIndicatorProps {
  currentStep: number;
  totalSteps: number;
  stepLabels: string[];
  completedSteps: Set<number>;
}

export default function StepIndicator({
  currentStep,
  totalSteps,
  stepLabels,
  completedSteps,
}: StepIndicatorProps) {
  return (
    <div>
      {/* Mobile: compact display */}
      <div className="sm:hidden text-center py-2">
        <span className="text-sm font-medium text-gray-600">
          Step {currentStep + 1} of {totalSteps}
        </span>
        <p className="text-sm text-gray-500 mt-0.5">
          {stepLabels[currentStep] || ''}
        </p>
      </div>

      {/* Desktop: full step indicator */}
      <nav className="hidden sm:block" aria-label="Progress">
        <ol className="flex items-center">
          {stepLabels.map((label, index) => {
            const isCompleted = completedSteps.has(index);
            const isCurrent = index === currentStep;
            const isPast = index < currentStep;

            return (
              <li
                key={label}
                className={`relative ${
                  index < totalSteps - 1 ? 'flex-1 pr-4' : ''
                }`}
              >
                <div className="flex items-center">
                  {/* Step circle */}
                  <div
                    className={`relative flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border-2 text-sm font-medium transition-colors ${
                      isCompleted
                        ? 'border-indigo-600 bg-indigo-600 text-white'
                        : isCurrent
                        ? 'border-indigo-600 bg-white text-indigo-600'
                        : isPast
                        ? 'border-indigo-300 bg-indigo-100 text-indigo-600'
                        : 'border-gray-300 bg-white text-gray-500'
                    }`}
                  >
                    {isCompleted ? (
                      <svg
                        className="h-4 w-4"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    ) : (
                      index + 1
                    )}
                  </div>

                  {/* Label */}
                  <span
                    className={`ml-2 text-xs font-medium whitespace-nowrap ${
                      isCurrent
                        ? 'text-indigo-600'
                        : isCompleted || isPast
                        ? 'text-gray-700'
                        : 'text-gray-400'
                    }`}
                  >
                    {label}
                  </span>

                  {/* Connector line */}
                  {index < totalSteps - 1 && (
                    <div
                      className={`ml-3 h-0.5 flex-1 ${
                        isCompleted || isPast
                          ? 'bg-indigo-600'
                          : 'bg-gray-200'
                      }`}
                    />
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      </nav>
    </div>
  );
}
