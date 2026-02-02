/**
 * Network Dashboard — shows networking activity and opportunities.
 *
 * Displays five sections: target companies with warm path counts,
 * contacts by relationship temperature, pending outreach drafts,
 * recent engagement activity, and suggested weekly actions.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TargetCompany {
  name: string;
  warmPathCount: number;
}

interface TemperatureContact {
  name: string;
  company: string;
  temperature: "cold" | "warming" | "warm" | "hot";
  readyForOutreach: boolean;
}

interface PendingDraft {
  id: string;
  recipient: string;
  company: string;
  messagePreview: string;
}

interface EngagementEvent {
  contactName: string;
  type: string;
  description: string;
  date: string;
}

interface SuggestedAction {
  action: string;
  contact: string;
  reason: string;
}

export interface NetworkDashboardProps {
  targetCompanies?: TargetCompany[];
  contacts?: TemperatureContact[];
  pendingDrafts?: PendingDraft[];
  recentActivity?: EngagementEvent[];
  suggestedActions?: SuggestedAction[];
  onCompanyClick?: (company: string) => void;
  onContactClick?: (contact: string) => void;
  onDraftClick?: (draftId: string) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const temperatureColor: Record<string, string> = {
  cold: "bg-blue-100 text-blue-700",
  warming: "bg-yellow-100 text-yellow-700",
  warm: "bg-orange-100 text-orange-700",
  hot: "bg-red-100 text-red-700",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function NetworkDashboard({
  targetCompanies = [],
  contacts = [],
  pendingDrafts = [],
  recentActivity = [],
  suggestedActions = [],
  onCompanyClick,
  onContactClick,
  onDraftClick,
}: NetworkDashboardProps) {
  return (
    <div className="space-y-6">
      {/* Target Companies */}
      <section aria-label="Target Companies">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Target Companies
        </h3>
        {targetCompanies.length === 0 ? (
          <p className="text-sm text-gray-400">No target companies yet</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {targetCompanies.map((company) => (
              <button
                key={company.name}
                onClick={() => onCompanyClick?.(company.name)}
                className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3 text-left hover:border-indigo-300 hover:bg-indigo-50"
              >
                <span className="text-sm font-medium text-gray-900">
                  {company.name}
                </span>
                <span className="ml-2 rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700">
                  {company.warmPathCount} path{company.warmPathCount !== 1 ? "s" : ""}
                </span>
              </button>
            ))}
          </div>
        )}
      </section>

      {/* Contacts by Temperature */}
      <section aria-label="Contacts by Temperature">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Contacts by Temperature
        </h3>
        {contacts.length === 0 ? (
          <p className="text-sm text-gray-400">No contacts tracked yet</p>
        ) : (
          <div className="space-y-2">
            {contacts.map((contact) => (
              <button
                key={contact.name}
                onClick={() => onContactClick?.(contact.name)}
                className="flex w-full items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-2 text-left hover:border-indigo-300"
              >
                <div>
                  <span className="text-sm font-medium text-gray-900">
                    {contact.name}
                  </span>
                  <span className="ml-2 text-xs text-gray-500">
                    {contact.company}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      temperatureColor[contact.temperature] || "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {contact.temperature}
                  </span>
                  {contact.readyForOutreach && (
                    <span className="text-xs font-medium text-green-600">
                      Ready for outreach
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

      {/* Pending Outreach */}
      <section aria-label="Pending Outreach">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Pending Outreach
        </h3>
        {pendingDrafts.length === 0 ? (
          <p className="text-sm text-gray-400">No pending outreach drafts</p>
        ) : (
          <div className="space-y-2">
            {pendingDrafts.map((draft) => (
              <button
                key={draft.id}
                onClick={() => onDraftClick?.(draft.id)}
                className="block w-full rounded-lg border border-gray-200 bg-white px-4 py-3 text-left hover:border-indigo-300"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-900">
                    {draft.recipient}
                  </span>
                  <span className="text-xs text-gray-500">{draft.company}</span>
                </div>
                <p className="mt-1 truncate text-xs text-gray-600">
                  {draft.messagePreview}
                </p>
              </button>
            ))}
          </div>
        )}
      </section>

      {/* Recent Activity */}
      <section aria-label="Recent Activity">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Recent Activity
        </h3>
        {recentActivity.length === 0 ? (
          <p className="text-sm text-gray-400">No recent engagement activity</p>
        ) : (
          <ul className="space-y-2">
            {recentActivity.map((event, i) => (
              <li
                key={`${event.contactName}-${i}`}
                className="rounded-lg border border-gray-200 bg-white px-4 py-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-900">
                    {event.contactName}
                  </span>
                  <span className="text-xs text-gray-500">{event.date}</span>
                </div>
                <p className="text-xs text-gray-600">{event.description}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Suggested Actions */}
      <section aria-label="Suggested Actions">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Suggested Actions This Week
        </h3>
        {suggestedActions.length === 0 ? (
          <p className="text-sm text-gray-400">No suggested actions right now</p>
        ) : (
          <ul className="space-y-2">
            {suggestedActions.map((action, i) => (
              <li
                key={`${action.contact}-${i}`}
                className="flex items-start gap-3 rounded-lg border border-gray-200 bg-white px-4 py-3"
              >
                <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-medium text-indigo-700">
                  {i + 1}
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {action.action}
                  </p>
                  <p className="text-xs text-gray-500">
                    {action.contact} — {action.reason}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
