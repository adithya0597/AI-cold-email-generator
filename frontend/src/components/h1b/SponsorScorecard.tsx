/**
 * Sponsor Scorecard — displays H1B sponsorship data for a company.
 *
 * Shows: grade, approval rate, petition count, avg wage, data freshness.
 */

import { useSponsorData } from '../../services/h1b';

// ---------------------------------------------------------------------------
// Grade calculation
// ---------------------------------------------------------------------------

export function calculateGrade(approvalRate: number | null | undefined): string {
  if (approvalRate == null) return 'F';
  if (approvalRate >= 0.95) return 'A+';
  if (approvalRate >= 0.90) return 'A';
  if (approvalRate >= 0.85) return 'B+';
  if (approvalRate >= 0.80) return 'B';
  if (approvalRate >= 0.70) return 'C';
  if (approvalRate >= 0.50) return 'D';
  return 'F';
}

function gradeColor(grade: string): string {
  if (grade.startsWith('A')) return 'text-green-600 bg-green-50 border-green-200';
  if (grade.startsWith('B')) return 'text-blue-600 bg-blue-50 border-blue-200';
  if (grade === 'C') return 'text-yellow-600 bg-yellow-50 border-yellow-200';
  if (grade === 'D') return 'text-orange-600 bg-orange-50 border-orange-200';
  return 'text-red-600 bg-red-50 border-red-200';
}

function formatWage(wage: number | null): string {
  if (wage == null) return 'N/A';
  return `$${wage.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'Unknown';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return 'Unknown';
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface SponsorScorecardProps {
  company: string;
}

export function SponsorScorecard({ company }: SponsorScorecardProps) {
  const { data, isLoading, isError, refetch } = useSponsorData(company);

  if (isLoading) {
    return (
      <div data-testid="scorecard-skeleton" className="animate-pulse rounded-lg border border-gray-200 bg-white p-6">
        <div className="mb-4 h-6 w-1/3 rounded bg-gray-200" />
        <div className="space-y-3">
          <div className="h-4 w-2/3 rounded bg-gray-200" />
          <div className="h-4 w-1/2 rounded bg-gray-200" />
          <div className="h-4 w-3/4 rounded bg-gray-200" />
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
        <p className="mb-2 text-sm text-red-700">Failed to load sponsor data</p>
        <button
          onClick={() => refetch()}
          className="rounded-md bg-red-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!data) return null;

  const grade = calculateGrade(data.approval_rate);
  const approvalPct = data.approval_rate != null ? Math.round(data.approval_rate * 100) : 'N/A';

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-base font-semibold text-gray-900">H1B Sponsor Scorecard</h3>
        <span
          data-testid="sponsor-grade"
          className={`inline-flex items-center rounded-full border px-3 py-1 text-lg font-bold ${gradeColor(grade)}`}
        >
          {grade}
        </span>
      </div>

      <dl className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <dt className="text-gray-500">Approval Rate</dt>
          <dd data-testid="approval-rate" className="text-lg font-semibold text-gray-900">
            {approvalPct !== 'N/A' ? `${approvalPct}%` : 'N/A'}
          </dd>
        </div>
        <div>
          <dt className="text-gray-500">Total Petitions</dt>
          <dd data-testid="petition-count" className="text-lg font-semibold text-gray-900">
            {data.total_petitions.toLocaleString()}
          </dd>
        </div>
        <div>
          <dt className="text-gray-500">Average Wage</dt>
          <dd data-testid="avg-wage" className="text-lg font-semibold text-gray-900">
            {formatWage(data.avg_wage)}
          </dd>
        </div>
        <div>
          <dt className="text-gray-500">Company</dt>
          <dd className="text-sm font-medium text-gray-900">{data.company_name}</dd>
        </div>
      </dl>

      {data.updated_at && (
        <p className="mt-4 text-xs text-gray-400">
          Data last updated: {formatDate(data.updated_at)}
        </p>
      )}

      <details className="mt-4">
        <summary className="cursor-pointer text-xs font-medium text-indigo-600 hover:text-indigo-700">
          Scoring Methodology
        </summary>
        <div className="mt-2 text-xs text-gray-500">
          <p className="mb-1">Grades are based on H1B petition approval rate:</p>
          <ul className="list-inside list-disc space-y-0.5">
            <li>A+ = 95%+, A = 90%+, B+ = 85%+</li>
            <li>B = 80%+, C = 70%+, D = 50%+, F = below 50%</li>
          </ul>
          <p className="mt-1">Data sourced from DOL LCA disclosures and USCIS Employer Data Hub.</p>
        </div>
      </details>
    </div>
  );
}
