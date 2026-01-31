/**
 * JobTypeStep -- Step 1 of the preference wizard.
 *
 * Captures job categories, target job titles, and seniority levels.
 * Story 2-1: Job Type Preferences
 */

import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  jobTypeSchema,
  type JobTypeFormData,
  JOB_CATEGORIES,
  SENIORITY_LEVELS,
} from '../../types/preferences';
import ChipPicker from './ChipPicker';
import TagInput from './TagInput';

interface JobTypeStepProps {
  defaultValues?: Partial<JobTypeFormData>;
  onSubmit: (data: JobTypeFormData) => void;
  onBack?: () => void;
  onSkip?: () => void;
}

export default function JobTypeStep({
  defaultValues,
  onSubmit,
  onBack,
  onSkip,
}: JobTypeStepProps) {
  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<JobTypeFormData>({
    resolver: zodResolver(jobTypeSchema),
    defaultValues: {
      categories: defaultValues?.categories || [],
      target_titles: defaultValues?.target_titles || [],
      seniority_levels: defaultValues?.seniority_levels || [],
    },
  });

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900">What kind of roles interest you?</h2>
        <p className="mt-2 text-gray-600">
          Help your agent understand the types of positions you're looking for.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Job Categories */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-3 text-base font-semibold text-gray-900">Job Categories</h3>
          <p className="mb-4 text-sm text-gray-500">Select all that apply</p>
          <Controller
            control={control}
            name="categories"
            render={({ field }) => (
              <ChipPicker
                options={JOB_CATEGORIES}
                selected={field.value}
                onChange={field.onChange}
                columns={4}
              />
            )}
          />
          {errors.categories && (
            <p className="mt-2 text-xs text-red-500">{errors.categories.message}</p>
          )}
        </div>

        {/* Target Job Titles */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-3 text-base font-semibold text-gray-900">Target Job Titles</h3>
          <p className="mb-4 text-sm text-gray-500">
            Add specific titles you're targeting (e.g., "Senior Software Engineer")
          </p>
          <Controller
            control={control}
            name="target_titles"
            render={({ field }) => (
              <TagInput
                tags={field.value}
                onChange={field.onChange}
                placeholder="Type a job title and press Enter"
              />
            )}
          />
          {errors.target_titles && (
            <p className="mt-2 text-xs text-red-500">{errors.target_titles.message}</p>
          )}
        </div>

        {/* Seniority Levels */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-3 text-base font-semibold text-gray-900">Seniority Level</h3>
          <p className="mb-4 text-sm text-gray-500">Select all levels you'd consider</p>
          <Controller
            control={control}
            name="seniority_levels"
            render={({ field }) => (
              <ChipPicker
                options={SENIORITY_LEVELS}
                selected={field.value}
                onChange={field.onChange}
                columns={4}
              />
            )}
          />
          {errors.seniority_levels && (
            <p className="mt-2 text-xs text-red-500">{errors.seniority_levels.message}</p>
          )}
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
