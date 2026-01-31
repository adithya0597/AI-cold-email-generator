/**
 * AutonomyStep -- Step 6 of the preference wizard.
 *
 * Captures the user's preferred autonomy level (L0-L3) via radio cards.
 * Story 2-6: Autonomy Level Preferences
 */

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { autonomySchema, type AutonomyFormData, AUTONOMY_LEVELS } from '../../types/preferences';

interface AutonomyStepProps {
  defaultValues?: Partial<AutonomyFormData>;
  onSubmit: (data: AutonomyFormData) => void;
  onBack?: () => void;
  onSkip?: () => void;
}

const AUTONOMY_ICONS: Record<string, React.ReactNode> = {
  l0: (
    <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
    </svg>
  ),
  l1: (
    <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
    </svg>
  ),
  l2: (
    <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
    </svg>
  ),
  l3: (
    <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
    </svg>
  ),
};

export default function AutonomyStep({
  defaultValues,
  onSubmit,
  onBack,
  onSkip,
}: AutonomyStepProps) {
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<AutonomyFormData>({
    resolver: zodResolver(autonomySchema),
    defaultValues: {
      level: defaultValues?.level || undefined,
    },
  });

  const selectedLevel = watch('level');

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900">How autonomous should your agent be?</h2>
        <p className="mt-2 text-gray-600">
          Choose how much freedom your AI agent has when acting on your behalf.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2">
          {AUTONOMY_LEVELS.map((level) => {
            const isSelected = selectedLevel === level.value;
            return (
              <label
                key={level.value}
                className={`relative flex cursor-pointer flex-col rounded-xl border-2 p-5 transition-all ${
                  isSelected
                    ? 'border-indigo-500 bg-indigo-50 ring-1 ring-indigo-500'
                    : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
                }`}
              >
                <input
                  type="radio"
                  {...register('level')}
                  value={level.value}
                  className="sr-only"
                />

                {level.recommended && (
                  <span className="absolute -top-2.5 right-3 rounded-full bg-indigo-600 px-2.5 py-0.5 text-xs font-medium text-white">
                    Recommended
                  </span>
                )}

                <div className={`mb-3 ${isSelected ? 'text-indigo-600' : 'text-gray-400'}`}>
                  {AUTONOMY_ICONS[level.value]}
                </div>

                <h4
                  className={`text-base font-semibold ${
                    isSelected ? 'text-indigo-700' : 'text-gray-900'
                  }`}
                >
                  L{level.value.charAt(1)} {level.title}
                </h4>

                <p
                  className={`mt-1 text-sm ${
                    isSelected ? 'text-indigo-600' : 'text-gray-500'
                  }`}
                >
                  {level.description}
                </p>
              </label>
            );
          })}
        </div>

        {errors.level && (
          <p className="text-center text-xs text-red-500">{errors.level.message}</p>
        )}

        {/* Note */}
        <div className="rounded-lg border border-gray-100 bg-gray-50 px-4 py-3 text-center">
          <p className="text-sm text-gray-500">
            You can change this anytime in Settings.
          </p>
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between border-t border-gray-200 pt-6">
          <div>
            {onBack && (
              <button
                type="button"
                onClick={onBack}
                className="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
              >
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
            <button
              type="submit"
              className="inline-flex items-center rounded-md bg-indigo-600 px-6 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            >
              Next
              <svg className="ml-2 h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
