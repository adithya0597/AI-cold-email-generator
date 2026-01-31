/**
 * H1BStep -- Step 5 of the preference wizard.
 *
 * Captures visa sponsorship requirements and current visa status.
 * Story 2-5: H1B/Visa Preferences
 */

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { h1bSchema, type H1BFormData, VISA_TYPES } from '../../types/preferences';

interface H1BStepProps {
  defaultValues?: Partial<H1BFormData>;
  onSubmit: (data: H1BFormData) => void;
  onBack?: () => void;
  onSkip?: () => void;
}

export default function H1BStep({
  defaultValues,
  onSubmit,
  onBack,
  onSkip,
}: H1BStepProps) {
  const {
    register,
    handleSubmit,
    watch,
  } = useForm<H1BFormData>({
    resolver: zodResolver(h1bSchema),
    defaultValues: {
      requires_h1b: defaultValues?.requires_h1b || false,
      requires_greencard: defaultValues?.requires_greencard || false,
      current_visa_type: defaultValues?.current_visa_type ?? null,
      visa_expiration: defaultValues?.visa_expiration ?? null,
    },
  });

  const requiresH1b = watch('requires_h1b');
  const requiresGreencard = watch('requires_greencard');
  const showVisaDetails = requiresH1b || requiresGreencard;

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900">Visa & Sponsorship</h2>
        <p className="mt-2 text-gray-600">
          If you need employer sponsorship, your agent will prioritize sponsors.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Sponsorship Toggles */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-base font-semibold text-gray-900">Sponsorship Requirements</h3>
          <div className="space-y-4">
            <label className="flex items-center justify-between rounded-lg border border-gray-200 px-4 py-3">
              <span className="text-sm font-medium text-gray-700">
                I require H1B visa sponsorship
              </span>
              <input
                type="checkbox"
                {...register('requires_h1b')}
                className="h-5 w-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
            </label>

            <label className="flex items-center justify-between rounded-lg border border-gray-200 px-4 py-3">
              <span className="text-sm font-medium text-gray-700">
                I require green card sponsorship
              </span>
              <input
                type="checkbox"
                {...register('requires_greencard')}
                className="h-5 w-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
            </label>
          </div>
        </div>

        {/* Visa Details (conditional) */}
        {showVisaDetails && (
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <h3 className="mb-4 text-base font-semibold text-gray-900">Current Visa Details</h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Current Visa Type
                </label>
                <select
                  {...register('current_visa_type')}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="">Select...</option>
                  {VISA_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Visa Expiration Date
                </label>
                <input
                  type="date"
                  {...register('visa_expiration')}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>
          </div>
        )}

        {/* H1B Pro note */}
        {showVisaDetails && (
          <div className="rounded-lg border border-blue-100 bg-blue-50 px-4 py-3">
            <div className="flex items-start gap-2">
              <svg className="mt-0.5 h-4 w-4 flex-shrink-0 text-blue-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />
              </svg>
              <p className="text-sm text-blue-700">
                H1B users can upgrade to H1B Pro for verified sponsor data.
              </p>
            </div>
          </div>
        )}

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
