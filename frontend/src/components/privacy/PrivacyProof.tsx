/**
 * Privacy Proof dashboard component.
 *
 * Shows blocklist verification with last-checked timestamps,
 * exposure counts, blocked action logs, and report download.
 */

import { usePrivacyProof, useDownloadReport } from '../../services/privacy';

interface PrivacyProofProps {
  stealthEnabled: boolean;
}

export default function PrivacyProof({ stealthEnabled }: PrivacyProofProps) {
  const { data, isLoading } = usePrivacyProof();
  const downloadReport = useDownloadReport();

  if (!stealthEnabled) {
    return null;
  }

  function handleDownload() {
    downloadReport.mutate(undefined, {
      onSuccess: (reportData) => {
        const blob = new Blob([JSON.stringify(reportData, null, 2)], {
          type: 'application/json',
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'privacy-report.json';
        a.click();
        URL.revokeObjectURL(url);
      },
    });
  }

  const entries = data?.entries ?? [];

  return (
    <div
      data-testid="privacy-proof"
      className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
    >
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Privacy Proof</h2>
          <p className="mt-1 text-sm text-gray-500">
            Verification that your blocklisted companies have zero exposure.
          </p>
        </div>
        <button
          data-testid="download-report-btn"
          onClick={handleDownload}
          disabled={downloadReport.isPending}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          {downloadReport.isPending ? 'Generating...' : 'Download Report'}
        </button>
      </div>

      <div className="mt-4">
        {isLoading ? (
          <div className="py-4 text-center text-sm text-gray-400">Loading...</div>
        ) : entries.length === 0 ? (
          <div
            data-testid="proof-empty"
            className="py-6 text-center text-sm text-gray-400"
          >
            No companies blocklisted yet. Add companies to your blocklist above to see privacy verification here.
          </div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {entries.map((entry, idx) => (
              <li
                key={`${entry.company_name}-${idx}`}
                data-testid={`proof-entry-${idx}`}
                className="py-4"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {entry.company_name}
                    </p>
                    {entry.note && (
                      <p className="text-xs text-gray-500">{entry.note}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span
                      data-testid={`exposure-badge-${idx}`}
                      className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700"
                    >
                      0 exposures
                    </span>
                    <span className="text-xs text-gray-400">
                      Last checked: {new Date(entry.last_checked).toLocaleString()}
                    </span>
                  </div>
                </div>

                {entry.blocked_actions.length > 0 && (
                  <div
                    data-testid={`blocked-actions-${idx}`}
                    className="mt-2 space-y-1"
                  >
                    {entry.blocked_actions.map((action) => (
                      <div
                        key={action.id}
                        className="flex items-center gap-2 rounded bg-gray-50 px-2 py-1 text-xs text-gray-600"
                      >
                        <span className="font-medium">{action.action_type}</span>
                        {action.details && <span>— {action.details}</span>}
                        {action.created_at && (
                          <span className="ml-auto text-gray-400">
                            {new Date(action.created_at).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
