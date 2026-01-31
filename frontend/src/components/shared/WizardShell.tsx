/**
 * WizardShell -- layout wrapper for multi-step wizards.
 *
 * Renders StepIndicator at top, children in center, and
 * Back/Skip/Next navigation buttons at bottom.
 */

import React from 'react';
import StepIndicator from './StepIndicator';

interface WizardShellProps {
  children: React.ReactNode;
  currentStep: number;
  totalSteps: number;
  stepLabels: string[];
  completedSteps?: Set<number>;
  onBack?: () => void;
  onNext?: () => void;
  onSkip?: () => void;
  isNextDisabled?: boolean;
  isLastStep?: boolean;
  nextLabel?: string;
}

export default function WizardShell({
  children,
  currentStep,
  totalSteps,
  stepLabels,
  completedSteps = new Set(),
  onBack,
  onNext,
  onSkip,
  isNextDisabled = false,
  isLastStep = false,
  nextLabel,
}: WizardShellProps) {
  const showBack = currentStep > 0 && onBack;
  const resolvedNextLabel = nextLabel || (isLastStep ? 'Finish' : 'Next');

  return (
    <div className="mx-auto max-w-3xl">
      {/* Step indicator */}
      <div className="mb-8">
        <StepIndicator
          currentStep={currentStep}
          totalSteps={totalSteps}
          stepLabels={stepLabels}
          completedSteps={completedSteps}
        />
      </div>

      {/* Main content area */}
      <div className="min-h-[400px]">{children}</div>

      {/* Navigation buttons */}
      <div className="mt-8 flex items-center justify-between border-t border-gray-200 pt-6">
        <div>
          {showBack && (
            <button
              type="button"
              onClick={onBack}
              className="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            >
              <svg
                className="mr-2 h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15.75 19.5L8.25 12l7.5-7.5"
                />
              </svg>
              Back
            </button>
          )}
        </div>

        <div className="flex items-center space-x-3">
          {onSkip && (
            <button
              type="button"
              onClick={onSkip}
              className="text-sm font-medium text-gray-500 hover:text-gray-700"
            >
              Skip
            </button>
          )}

          {onNext && (
            <button
              type="button"
              onClick={onNext}
              disabled={isNextDisabled}
              className={`inline-flex items-center rounded-md px-6 py-2 text-sm font-medium text-white shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 ${
                isNextDisabled
                  ? 'cursor-not-allowed bg-indigo-300'
                  : 'bg-indigo-600 hover:bg-indigo-700'
              }`}
            >
              {resolvedNextLabel}
              {!isLastStep && (
                <svg
                  className="ml-2 h-4 w-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M8.25 4.5l7.5 7.5-7.5 7.5"
                  />
                </svg>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
