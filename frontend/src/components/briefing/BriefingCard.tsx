/**
 * BriefingCard -- hero component displayed at top of Dashboard.
 *
 * Shows the latest briefing with:
 *   - Time-aware personalized greeting
 *   - Key metrics summary cards
 *   - Expandable sections (Summary, Actions Needed, New Matches, Activity Log)
 *   - "Mark as Read" button
 *   - Lite briefing rendering with softer messaging
 *   - Empty state for new users with no briefings yet
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FiChevronDown,
  FiChevronUp,
  FiCheck,
  FiAlertCircle,
  FiBriefcase,
  FiActivity,
  FiClock,
  FiStar,
  FiArrowRight,
} from 'react-icons/fi';
import type { Briefing } from '../../services/briefings';
import { useMarkBriefingRead } from '../../services/briefings';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHrs = Math.floor(diffMins / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  const diffDays = Math.floor(diffHrs / 24);
  if (diffDays === 1) return 'Yesterday';
  return `${diffDays} days ago`;
}

// ---------------------------------------------------------------------------
// Empty State (no briefings yet)
// ---------------------------------------------------------------------------

export function BriefingEmptyState({ userName }: { userName?: string }) {
  return (
    <div className="bg-white rounded-lg shadow-md p-8 mb-6 border border-dashed border-indigo-200">
      <div className="text-center max-w-md mx-auto">
        <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-indigo-50 mb-4">
          <FiStar className="h-8 w-8 text-indigo-500" />
        </div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          {getGreeting()}{userName ? `, ${userName}` : ''}!
        </h2>
        <p className="text-gray-600 mb-4">
          Your first daily briefing is being prepared. Each morning, you will
          receive a personalized summary of new job matches, application updates,
          and agent activity.
        </p>
        <div className="bg-indigo-50 rounded-lg p-4 text-left text-sm text-indigo-800 space-y-2">
          <p className="font-medium">While you wait, try these tips:</p>
          <ul className="list-disc list-inside space-y-1 text-indigo-700">
            <li>Add more skills to your profile for better matches</li>
            <li>Fine-tune your deal-breakers in Preferences</li>
            <li>Set your preferred briefing time in Settings</li>
          </ul>
        </div>
        <div className="mt-4 flex justify-center gap-3">
          <Link
            to="/preferences"
            className="inline-flex items-center px-4 py-2 text-sm font-medium rounded-md text-indigo-600 bg-indigo-50 hover:bg-indigo-100"
          >
            Update Preferences
            <FiArrowRight className="ml-1.5" />
          </Link>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Metric Card
// ---------------------------------------------------------------------------

function MetricCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: number | string;
  icon: React.ComponentType<{ className?: string }>;
  color: 'blue' | 'green' | 'purple' | 'amber';
}) {
  const colorMap = {
    blue: 'bg-blue-50 text-blue-800',
    green: 'bg-green-50 text-green-800',
    purple: 'bg-purple-50 text-purple-800',
    amber: 'bg-amber-50 text-amber-800',
  };
  const valueColorMap = {
    blue: 'text-blue-900',
    green: 'text-green-900',
    purple: 'text-purple-900',
    amber: 'text-amber-900',
  };
  return (
    <div className={`rounded-lg p-4 ${colorMap[color]}`}>
      <div className="flex items-center gap-2 mb-1">
        <Icon className="h-4 w-4" />
        <span className="text-sm font-medium">{label}</span>
      </div>
      <p className={`text-2xl font-bold ${valueColorMap[color]}`}>{value}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Expandable Section
// ---------------------------------------------------------------------------

function ExpandableSection({
  title,
  icon: Icon,
  children,
  defaultOpen = false,
  badge,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  defaultOpen?: boolean;
  badge?: number;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  return (
    <div className="border border-gray-100 rounded-lg">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 rounded-lg transition-colors"
      >
        <div className="flex items-center gap-2">
          <Icon className="h-5 w-5 text-gray-500" />
          <span className="font-medium text-gray-900">{title}</span>
          {badge !== undefined && badge > 0 && (
            <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
              {badge}
            </span>
          )}
        </div>
        {isOpen ? (
          <FiChevronUp className="h-5 w-5 text-gray-400" />
        ) : (
          <FiChevronDown className="h-5 w-5 text-gray-400" />
        )}
      </button>
      {isOpen && <div className="px-4 pb-4">{children}</div>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// BriefingCard
// ---------------------------------------------------------------------------

interface BriefingCardProps {
  briefing: Briefing;
  userName?: string;
  userId: string;
}

export default function BriefingCard({
  briefing,
  userName,
  userId,
}: BriefingCardProps) {
  const markRead = useMarkBriefingRead(userId);
  const content = briefing.content;
  const metrics = content.metrics;
  const isLite = briefing.briefing_type === 'lite';
  const isUnread = !briefing.read_at;

  const handleMarkRead = () => {
    markRead.mutate(briefing.id);
  };

  return (
    <div
      className={`bg-white rounded-lg shadow-md mb-6 overflow-hidden ${
        isUnread ? 'ring-2 ring-indigo-300' : ''
      }`}
    >
      {/* Header */}
      <div
        className={`px-6 py-5 ${
          isLite
            ? 'bg-gradient-to-r from-amber-50 to-yellow-50'
            : 'bg-gradient-to-r from-indigo-50 to-blue-50'
        }`}
      >
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              {getGreeting()}{userName ? `, ${userName}` : ''}!
            </h2>
            {isLite && (
              <p className="text-sm text-amber-700 mt-1">
                We had some trouble generating your full briefing today. Here is
                a summary from cached data.
              </p>
            )}
            {!isLite && content.summary && (
              <p className="text-gray-600 mt-1 text-sm">{content.summary}</p>
            )}
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <span className="text-xs text-gray-500">
              {formatRelativeDate(briefing.generated_at)}
            </span>
            {isUnread && (
              <button
                onClick={handleMarkRead}
                disabled={markRead.isPending}
                className="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md text-indigo-700 bg-indigo-100 hover:bg-indigo-200 transition-colors disabled:opacity-50"
              >
                <FiCheck className="mr-1" />
                {markRead.isPending ? 'Marking...' : 'Mark as Read'}
              </button>
            )}
          </div>
        </div>

        {/* Metrics */}
        {metrics && (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-4">
            {metrics.total_matches !== undefined && (
              <MetricCard
                label="New Matches"
                value={metrics.total_matches}
                icon={FiBriefcase}
                color="blue"
              />
            )}
            {metrics.pending_approvals !== undefined && (
              <MetricCard
                label="Pending Approvals"
                value={metrics.pending_approvals}
                icon={FiAlertCircle}
                color="amber"
              />
            )}
            {metrics.applications_sent !== undefined && (
              <MetricCard
                label="Applications Sent"
                value={metrics.applications_sent}
                icon={FiCheck}
                color="green"
              />
            )}
          </div>
        )}
      </div>

      {/* Expandable Sections */}
      <div className="px-6 py-4 space-y-2">
        {content.actions_needed && content.actions_needed.length > 0 && (
          <ExpandableSection
            title="Actions Needed"
            icon={FiAlertCircle}
            defaultOpen={true}
            badge={content.actions_needed.length}
          >
            <ul className="space-y-2">
              {content.actions_needed.map((action, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-sm text-gray-700"
                >
                  <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-amber-400 shrink-0" />
                  {action}
                </li>
              ))}
            </ul>
          </ExpandableSection>
        )}

        {content.new_matches && content.new_matches.length > 0 && (
          <ExpandableSection
            title="New Matches"
            icon={FiBriefcase}
            badge={content.new_matches.length}
          >
            <div className="space-y-3">
              {content.new_matches.map((match, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {match.title}
                    </p>
                    <p className="text-xs text-gray-500">{match.company}</p>
                  </div>
                  {match.match_score !== undefined && (
                    <span className="text-xs font-medium text-green-700 bg-green-100 px-2 py-1 rounded-full">
                      {match.match_score}% match
                    </span>
                  )}
                </div>
              ))}
            </div>
          </ExpandableSection>
        )}

        {content.activity_log && content.activity_log.length > 0 && (
          <ExpandableSection title="Activity Log" icon={FiActivity}>
            <div className="space-y-2">
              {content.activity_log.map((entry, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-gray-700">{entry.event}</span>
                  <span className="text-xs text-gray-400">
                    {entry.agent_type && (
                      <span className="mr-2 text-gray-500">
                        {entry.agent_type}
                      </span>
                    )}
                    {formatRelativeDate(entry.timestamp)}
                  </span>
                </div>
              ))}
            </div>
          </ExpandableSection>
        )}

        {/* Tips (empty state content or onboarding tips) */}
        {content.tips && content.tips.length > 0 && (
          <ExpandableSection title="Tips" icon={FiStar} defaultOpen={true}>
            <ul className="space-y-1.5">
              {content.tips.map((tip, i) => (
                <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                  <FiStar className="h-3.5 w-3.5 text-indigo-400 mt-0.5 shrink-0" />
                  {tip}
                </li>
              ))}
            </ul>
          </ExpandableSection>
        )}
      </div>

      {/* Footer */}
      <div className="px-6 py-3 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
        <Link
          to={`/briefings`}
          className="text-sm text-indigo-600 hover:text-indigo-800 font-medium inline-flex items-center"
        >
          View Briefing History
          <FiArrowRight className="ml-1" />
        </Link>
        <div className="flex items-center gap-1.5 text-xs text-gray-400">
          <FiClock className="h-3.5 w-3.5" />
          Generated {new Date(briefing.generated_at).toLocaleString()}
        </div>
      </div>
    </div>
  );
}
