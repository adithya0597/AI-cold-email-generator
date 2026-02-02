/**
 * Sponsor Badge — shows H1B sponsorship status on job cards.
 *
 * Color coded by approval rate:
 *   Green  = 80%+ approval rate
 *   Yellow = 50-79%
 *   Orange = <50%
 *   Gray   = Unknown (no data)
 */

interface SponsorBadgeProps {
  approvalRate?: number | null;
}

function badgeStyle(rate: number | null | undefined): string {
  if (rate == null) return 'bg-gray-100 text-gray-500 border-gray-200';
  if (rate >= 0.80) return 'bg-green-100 text-green-700 border-green-200';
  if (rate >= 0.50) return 'bg-yellow-100 text-yellow-700 border-yellow-200';
  return 'bg-orange-100 text-orange-700 border-orange-200';
}

export function SponsorBadge({ approvalRate }: SponsorBadgeProps) {
  const isKnown = approvalRate != null;

  return (
    <span
      data-testid="sponsor-badge"
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${badgeStyle(approvalRate)}`}
    >
      {isKnown ? (
        <>
          <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
              clipRule="evenodd"
            />
          </svg>
          Verified H1B Sponsor
        </>
      ) : (
        'Sponsorship Unknown'
      )}
    </span>
  );
}
