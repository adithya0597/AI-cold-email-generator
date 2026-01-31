/**
 * SummaryStep -- Step 7 (final) of the preference wizard.
 *
 * Displays all preferences in read-only card layout with edit links.
 * Skipped sections show "Not specified" empty state.
 * "Start My Agent" button triggers full preference save and onboarding completion.
 *
 * Story 2-7: Preference Summary & Confirmation
 * Story 2-8: Empty state handling for skipped steps
 */

import type { FullPreferences } from '../../types/preferences';
import { AUTONOMY_LEVELS, WORK_ARRANGEMENTS } from '../../types/preferences';

interface SummaryStepProps {
  preferences: Partial<FullPreferences>;
  completedSteps: number[];
  onEdit: (stepIndex: number) => void;
  onConfirm: () => void;
  onBack?: () => void;
  isSubmitting?: boolean;
}

function SectionCard({
  title,
  stepIndex,
  isCompleted,
  onEdit,
  children,
}: {
  title: string;
  stepIndex: number;
  isCompleted: boolean;
  onEdit: (step: number) => void;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-base font-semibold text-gray-900">{title}</h3>
        <button
          type="button"
          onClick={() => onEdit(stepIndex)}
          className="text-sm font-medium text-indigo-600 hover:text-indigo-500"
        >
          Edit
        </button>
      </div>
      {isCompleted ? (
        children
      ) : (
        <p className="text-sm italic text-gray-400">
          Not specified -- agent will consider all options
        </p>
      )}
    </div>
  );
}

function TagList({ items, emptyText }: { items: string[]; emptyText?: string }) {
  if (items.length === 0) {
    return <span className="text-sm text-gray-400">{emptyText || 'None'}</span>;
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <span
          key={item}
          className="inline-flex rounded-full bg-gray-100 px-2.5 py-0.5 text-xs text-gray-700"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

function LabelValue({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-xs font-medium text-gray-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-gray-900">{value || '--'}</dd>
    </div>
  );
}

export default function SummaryStep({
  preferences,
  completedSteps,
  onEdit,
  onConfirm,
  onBack,
  isSubmitting = false,
}: SummaryStepProps) {
  const jobType = preferences.job_type;
  const location = preferences.location;
  const salary = preferences.salary;
  const dealBreakers = preferences.deal_breakers;
  const h1b = preferences.h1b;
  const autonomy = preferences.autonomy;

  const arrangementLabel =
    WORK_ARRANGEMENTS.find((w) => w.value === location?.work_arrangement)?.label ||
    location?.work_arrangement;

  const autonomyInfo = AUTONOMY_LEVELS.find((a) => a.value === autonomy?.level);

  const formatSalary = (val: number | null | undefined) => {
    if (val == null) return '--';
    return '$' + val.toLocaleString('en-US');
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900">Review your preferences</h2>
        <p className="mt-2 text-gray-600">
          Make sure everything looks right before activating your agent.
        </p>
      </div>

      {/* Tip banner */}
      <div className="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3">
        <div className="flex items-start gap-2">
          <svg className="mt-0.5 h-4 w-4 flex-shrink-0 text-indigo-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
          </svg>
          <p className="text-sm text-indigo-700">
            The more you tell your agent, the better your matches.
          </p>
        </div>
      </div>

      {/* Section Cards */}
      <div className="space-y-4">
        {/* Job Type */}
        <SectionCard
          title="Job Type"
          stepIndex={0}
          isCompleted={completedSteps.includes(0)}
          onEdit={onEdit}
        >
          <div className="space-y-3">
            <div>
              <span className="text-xs font-medium text-gray-500">Categories</span>
              <div className="mt-1">
                <TagList items={jobType?.categories || []} />
              </div>
            </div>
            <div>
              <span className="text-xs font-medium text-gray-500">Target Titles</span>
              <div className="mt-1">
                <TagList items={jobType?.target_titles || []} />
              </div>
            </div>
            <div>
              <span className="text-xs font-medium text-gray-500">Seniority</span>
              <div className="mt-1">
                <TagList items={jobType?.seniority_levels || []} />
              </div>
            </div>
          </div>
        </SectionCard>

        {/* Location */}
        <SectionCard
          title="Location"
          stepIndex={1}
          isCompleted={completedSteps.includes(1)}
          onEdit={onEdit}
        >
          <dl className="grid gap-3 sm:grid-cols-2">
            <LabelValue label="Arrangement" value={arrangementLabel || null} />
            <LabelValue
              label="Relocate"
              value={location?.willing_to_relocate ? 'Yes' : 'No'}
            />
            <div className="sm:col-span-2">
              <span className="text-xs font-medium text-gray-500">Target Locations</span>
              <div className="mt-1">
                <TagList items={location?.target_locations || []} emptyText="Any" />
              </div>
            </div>
          </dl>
        </SectionCard>

        {/* Salary */}
        <SectionCard
          title="Salary"
          stepIndex={2}
          isCompleted={completedSteps.includes(2)}
          onEdit={onEdit}
        >
          <dl className="grid gap-3 sm:grid-cols-2">
            <LabelValue label="Minimum" value={formatSalary(salary?.minimum)} />
            <LabelValue label="Target" value={formatSalary(salary?.target)} />
            <LabelValue
              label="Flexibility"
              value={salary?.flexibility === 'firm' ? 'Firm minimum' : salary?.flexibility === 'negotiable' ? 'Negotiable' : null}
            />
            <LabelValue
              label="Comp Type"
              value={salary?.comp_preference === 'base' ? 'Base salary' : salary?.comp_preference === 'total' ? 'Total comp' : null}
            />
          </dl>
        </SectionCard>

        {/* Deal-Breakers */}
        <SectionCard
          title="Deal-Breakers"
          stepIndex={3}
          isCompleted={completedSteps.includes(3)}
          onEdit={onEdit}
        >
          <div className="space-y-3">
            {dealBreakers?.must_have_benefits && dealBreakers.must_have_benefits.length > 0 && (
              <div>
                <span className="text-xs font-medium text-green-600">Required Benefits</span>
                <div className="mt-1">
                  <TagList items={dealBreakers.must_have_benefits} />
                </div>
              </div>
            )}
            {dealBreakers?.excluded_companies && dealBreakers.excluded_companies.length > 0 && (
              <div>
                <span className="text-xs font-medium text-red-600">Excluded Companies</span>
                <div className="mt-1">
                  <TagList items={dealBreakers.excluded_companies} />
                </div>
              </div>
            )}
            {dealBreakers?.excluded_industries && dealBreakers.excluded_industries.length > 0 && (
              <div>
                <span className="text-xs font-medium text-red-600">Excluded Industries</span>
                <div className="mt-1">
                  <TagList items={dealBreakers.excluded_industries} />
                </div>
              </div>
            )}
            <dl className="grid gap-2 sm:grid-cols-3">
              {dealBreakers?.min_company_size != null && (
                <LabelValue label="Min Company Size" value={`${dealBreakers.min_company_size}+`} />
              )}
              {dealBreakers?.max_travel_percent != null && (
                <LabelValue label="Max Travel" value={`${dealBreakers.max_travel_percent}%`} />
              )}
              {dealBreakers?.no_oncall && (
                <LabelValue label="On-Call" value="No on-call" />
              )}
            </dl>
          </div>
        </SectionCard>

        {/* Visa */}
        <SectionCard
          title="Visa & Sponsorship"
          stepIndex={4}
          isCompleted={completedSteps.includes(4)}
          onEdit={onEdit}
        >
          <dl className="grid gap-3 sm:grid-cols-2">
            <LabelValue
              label="H1B Sponsorship"
              value={h1b?.requires_h1b ? 'Required' : 'Not needed'}
            />
            <LabelValue
              label="Green Card"
              value={h1b?.requires_greencard ? 'Required' : 'Not needed'}
            />
            {h1b?.current_visa_type && (
              <LabelValue label="Current Visa" value={h1b.current_visa_type} />
            )}
            {h1b?.visa_expiration && (
              <LabelValue label="Expires" value={h1b.visa_expiration} />
            )}
          </dl>
        </SectionCard>

        {/* Autonomy */}
        <SectionCard
          title="Agent Autonomy"
          stepIndex={5}
          isCompleted={completedSteps.includes(5)}
          onEdit={onEdit}
        >
          {autonomyInfo ? (
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-100 text-indigo-600">
                <span className="text-sm font-bold">L{autonomyInfo.value.charAt(1)}</span>
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900">{autonomyInfo.title}</p>
                <p className="text-xs text-gray-500">{autonomyInfo.description}</p>
              </div>
            </div>
          ) : (
            <p className="text-sm italic text-gray-400">
              Not specified -- agent will consider all options
            </p>
          )}
        </SectionCard>
      </div>

      {/* Action buttons */}
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
        <button
          type="button"
          onClick={onConfirm}
          disabled={isSubmitting}
          className={`inline-flex items-center rounded-lg px-8 py-3 text-base font-medium text-white shadow-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 ${
            isSubmitting
              ? 'cursor-not-allowed bg-indigo-300'
              : 'bg-indigo-600 hover:bg-indigo-700'
          }`}
        >
          {isSubmitting ? (
            <>
              <svg className="mr-2 h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Activating...
            </>
          ) : (
            <>
              Start My Agent
              <svg className="ml-2 h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
              </svg>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
