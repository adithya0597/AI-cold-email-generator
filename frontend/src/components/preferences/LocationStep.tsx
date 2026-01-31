/**
 * LocationStep -- Step 2 of the preference wizard.
 *
 * Captures work arrangement, target/excluded locations, relocation preference.
 * Story 2-2: Location Preferences
 */

import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { locationSchema, type LocationFormData, WORK_ARRANGEMENTS } from '../../types/preferences';
import TagInput from './TagInput';

interface LocationStepProps {
  defaultValues?: Partial<LocationFormData>;
  onSubmit: (data: LocationFormData) => void;
  onBack?: () => void;
  onSkip?: () => void;
}

export default function LocationStep({
  defaultValues,
  onSubmit,
  onBack,
  onSkip,
}: LocationStepProps) {
  const {
    register,
    control,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<LocationFormData>({
    resolver: zodResolver(locationSchema),
    defaultValues: {
      work_arrangement: defaultValues?.work_arrangement || '',
      target_locations: defaultValues?.target_locations || [],
      excluded_locations: defaultValues?.excluded_locations || [],
      willing_to_relocate: defaultValues?.willing_to_relocate || false,
    },
  });

  const arrangement = watch('work_arrangement');

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900">Where do you want to work?</h2>
        <p className="mt-2 text-gray-600">
          Set your location preferences so your agent finds roles in the right places.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Work Arrangement */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-3 text-base font-semibold text-gray-900">Work Arrangement</h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {WORK_ARRANGEMENTS.map((option) => (
              <label
                key={option.value}
                className={`flex cursor-pointer items-center justify-center rounded-lg border px-4 py-3 text-sm font-medium transition-colors ${
                  arrangement === option.value
                    ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  {...register('work_arrangement')}
                  value={option.value}
                  className="sr-only"
                />
                {option.label}
              </label>
            ))}
          </div>
          {errors.work_arrangement && (
            <p className="mt-2 text-xs text-red-500">{errors.work_arrangement.message}</p>
          )}
        </div>

        {/* Target Locations */}
        {arrangement !== 'remote' && (
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <h3 className="mb-3 text-base font-semibold text-gray-900">Target Cities / Metro Areas</h3>
            <p className="mb-4 text-sm text-gray-500">
              Add cities or metro areas where you'd like to work
            </p>
            <Controller
              control={control}
              name="target_locations"
              render={({ field }) => (
                <TagInput
                  tags={field.value}
                  onChange={field.onChange}
                  placeholder="e.g., San Francisco, New York"
                />
              )}
            />
          </div>
        )}

        {/* Excluded Locations */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-3 text-base font-semibold text-gray-900">Excluded Locations</h3>
          <p className="mb-4 text-sm text-gray-500">
            Any areas you want to exclude from results (optional)
          </p>
          <Controller
            control={control}
            name="excluded_locations"
            render={({ field }) => (
              <TagInput
                tags={field.value}
                onChange={field.onChange}
                placeholder="e.g., locations to avoid"
              />
            )}
          />
        </div>

        {/* Willing to Relocate */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              {...register('willing_to_relocate')}
              className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <span className="text-sm font-medium text-gray-700">
              I'm willing to relocate for the right opportunity
            </span>
          </label>
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
