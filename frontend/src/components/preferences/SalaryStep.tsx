/**
 * SalaryStep -- Step 3 of the preference wizard.
 *
 * Captures minimum salary, target salary, flexibility, and comp preference.
 * Story 2-3: Salary Preferences
 */

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { salarySchema, type SalaryFormData } from '../../types/preferences';

interface SalaryStepProps {
  defaultValues?: Partial<SalaryFormData>;
  onSubmit: (data: SalaryFormData) => void;
  onBack?: () => void;
  onSkip?: () => void;
}

function formatDollar(value: number | null | undefined): string {
  if (value == null) return '';
  return value.toLocaleString('en-US');
}

function parseDollar(value: string): number | null {
  const cleaned = value.replace(/[^0-9]/g, '');
  if (!cleaned) return null;
  return parseInt(cleaned, 10);
}

export default function SalaryStep({
  defaultValues,
  onSubmit,
  onBack,
  onSkip,
}: SalaryStepProps) {
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<SalaryFormData>({
    resolver: zodResolver(salarySchema),
    defaultValues: {
      minimum: defaultValues?.minimum ?? null,
      target: defaultValues?.target ?? null,
      flexibility: defaultValues?.flexibility ?? null,
      comp_preference: defaultValues?.comp_preference ?? null,
    },
  });

  const flexibility = watch('flexibility');
  const compPreference = watch('comp_preference');

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900">What's your salary range?</h2>
        <p className="mt-2 text-gray-600">
          This helps your agent filter out roles that don't meet your expectations.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Salary Range */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-base font-semibold text-gray-900">Annual Salary (USD)</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700">Minimum</label>
              <div className="relative mt-1">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                  <span className="text-gray-500 sm:text-sm">$</span>
                </div>
                <input
                  type="text"
                  value={formatDollar(watch('minimum'))}
                  onChange={(e) => setValue('minimum', parseDollar(e.target.value))}
                  placeholder="80,000"
                  className="block w-full rounded-lg border border-gray-300 py-2 pl-7 pr-3 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Target</label>
              <div className="relative mt-1">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                  <span className="text-gray-500 sm:text-sm">$</span>
                </div>
                <input
                  type="text"
                  value={formatDollar(watch('target'))}
                  onChange={(e) => setValue('target', parseDollar(e.target.value))}
                  placeholder="120,000"
                  className="block w-full rounded-lg border border-gray-300 py-2 pl-7 pr-3 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Flexibility */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-3 text-base font-semibold text-gray-900">Flexibility</h3>
          <div className="grid grid-cols-2 gap-3">
            {[
              { value: 'firm', label: 'Firm minimum' },
              { value: 'negotiable', label: 'Negotiable' },
            ].map((option) => (
              <label
                key={option.value}
                className={`flex cursor-pointer items-center justify-center rounded-lg border px-4 py-3 text-sm font-medium transition-colors ${
                  flexibility === option.value
                    ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  {...register('flexibility')}
                  value={option.value}
                  className="sr-only"
                />
                {option.label}
              </label>
            ))}
          </div>
        </div>

        {/* Comp Preference */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-3 text-base font-semibold text-gray-900">Compensation Type</h3>
          <div className="grid grid-cols-2 gap-3">
            {[
              { value: 'base', label: 'Base salary only' },
              { value: 'total', label: 'Total comp (equity/bonus)' },
            ].map((option) => (
              <label
                key={option.value}
                className={`flex cursor-pointer items-center justify-center rounded-lg border px-4 py-3 text-sm font-medium transition-colors ${
                  compPreference === option.value
                    ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  {...register('comp_preference')}
                  value={option.value}
                  className="sr-only"
                />
                {option.label}
              </label>
            ))}
          </div>
        </div>

        {/* Privacy note */}
        <div className="rounded-lg border border-blue-100 bg-blue-50 px-4 py-3">
          <div className="flex items-start gap-2">
            <svg className="mt-0.5 h-4 w-4 flex-shrink-0 text-blue-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
            </svg>
            <p className="text-sm text-blue-700">
              Your salary info is private and never shared with employers.
            </p>
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
