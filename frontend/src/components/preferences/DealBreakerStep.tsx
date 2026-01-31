/**
 * DealBreakerStep -- Step 4 of the preference wizard.
 *
 * Captures must-haves (min company size, benefits) and never-haves
 * (excluded companies/industries, max travel, no on-call).
 * Story 2-4: Deal-Breaker Preferences
 */

import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { dealBreakerSchema, type DealBreakerFormData, BENEFITS_OPTIONS } from '../../types/preferences';
import ChipPicker from './ChipPicker';
import TagInput from './TagInput';

interface DealBreakerStepProps {
  defaultValues?: Partial<DealBreakerFormData>;
  onSubmit: (data: DealBreakerFormData) => void;
  onBack?: () => void;
  onSkip?: () => void;
}

export default function DealBreakerStep({
  defaultValues,
  onSubmit,
  onBack,
  onSkip,
}: DealBreakerStepProps) {
  const {
    register,
    control,
    handleSubmit,
    setValue,
    watch,
  } = useForm<DealBreakerFormData>({
    resolver: zodResolver(dealBreakerSchema),
    defaultValues: {
      min_company_size: defaultValues?.min_company_size ?? null,
      excluded_companies: defaultValues?.excluded_companies || [],
      excluded_industries: defaultValues?.excluded_industries || [],
      must_have_benefits: defaultValues?.must_have_benefits || [],
      max_travel_percent: defaultValues?.max_travel_percent ?? null,
      no_oncall: defaultValues?.no_oncall || false,
    },
  });

  const maxTravel = watch('max_travel_percent');

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900">Set your deal-breakers</h2>
        <p className="mt-2 text-gray-600">
          Your agent will automatically filter out any roles that violate these.
        </p>
      </div>

      {/* Warning banner */}
      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
        <div className="flex items-start gap-2">
          <svg className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
          <p className="text-sm text-amber-700">
            Jobs violating deal-breakers will be automatically filtered out.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Must-Haves Section */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-green-700">Must-Haves</h3>

          <div className="space-y-5">
            {/* Min Company Size */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Minimum Company Size (employees)
              </label>
              <input
                type="number"
                {...register('min_company_size', { valueAsNumber: true })}
                placeholder="e.g., 50"
                className="mt-1 block w-48 rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            {/* Required Benefits */}
            <div>
              <label className="mb-3 block text-sm font-medium text-gray-700">
                Required Benefits
              </label>
              <Controller
                control={control}
                name="must_have_benefits"
                render={({ field }) => (
                  <ChipPicker
                    options={BENEFITS_OPTIONS}
                    selected={field.value}
                    onChange={field.onChange}
                    columns={3}
                  />
                )}
              />
            </div>
          </div>
        </div>

        {/* Never-Haves Section */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-red-700">Never-Haves</h3>

          <div className="space-y-5">
            {/* Excluded Companies */}
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">
                Excluded Companies
              </label>
              <Controller
                control={control}
                name="excluded_companies"
                render={({ field }) => (
                  <TagInput
                    tags={field.value}
                    onChange={field.onChange}
                    placeholder="Type a company name and press Enter"
                  />
                )}
              />
            </div>

            {/* Excluded Industries */}
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">
                Excluded Industries
              </label>
              <Controller
                control={control}
                name="excluded_industries"
                render={({ field }) => (
                  <TagInput
                    tags={field.value}
                    onChange={field.onChange}
                    placeholder="e.g., Defense, Gambling"
                  />
                )}
              />
            </div>

            {/* Max Travel */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Maximum Travel ({maxTravel ?? 0}%)
              </label>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                value={maxTravel ?? 0}
                onChange={(e) => setValue('max_travel_percent', parseInt(e.target.value, 10))}
                className="mt-2 w-full accent-indigo-600"
              />
              <div className="mt-1 flex justify-between text-xs text-gray-400">
                <span>0%</span>
                <span>50%</span>
                <span>100%</span>
              </div>
            </div>

            {/* No On-Call */}
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                {...register('no_oncall')}
                className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              <span className="text-sm font-medium text-gray-700">No on-call required</span>
            </label>
          </div>
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
