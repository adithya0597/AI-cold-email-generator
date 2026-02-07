/**
 * BriefingSettings page -- configure briefing time, timezone, and delivery channels.
 *
 * Features:
 *   - Hour picker (1-12 AM/PM format, converted to 24h for API)
 *   - Timezone display (auto-detected from browser, editable)
 *   - Delivery channel checkboxes (In-App, Email -- at least one required)
 *   - Save calls PUT /api/v1/briefings/settings
 *   - "Changes take effect from tomorrow" note
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useUser } from '../providers/ClerkProvider';
import { toast } from 'react-toastify';
import {
  FiArrowLeft,
  FiClock,
  FiGlobe,
  FiMail,
  FiMonitor,
  FiSave,
  FiInfo,
} from 'react-icons/fi';
import {
  useBriefingSettings,
  useUpdateBriefingSettings,
} from '../services/briefings';
import type { BriefingSettings as BriefingSettingsType } from '../services/briefings';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const COMMON_TIMEZONES = [
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Anchorage',
  'Pacific/Honolulu',
  'America/Phoenix',
  'America/Toronto',
  'America/Vancouver',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Europe/Amsterdam',
  'Europe/Zurich',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Asia/Kolkata',
  'Asia/Dubai',
  'Asia/Singapore',
  'Australia/Sydney',
  'Australia/Melbourne',
  'Pacific/Auckland',
  'UTC',
];

function getDetectedTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch {
    return 'UTC';
  }
}

function to12Hour(hour24: number): { hour: number; period: 'AM' | 'PM' } {
  if (hour24 === 0) return { hour: 12, period: 'AM' };
  if (hour24 < 12) return { hour: hour24, period: 'AM' };
  if (hour24 === 12) return { hour: 12, period: 'PM' };
  return { hour: hour24 - 12, period: 'PM' };
}

function to24Hour(hour12: number, period: 'AM' | 'PM'): number {
  if (period === 'AM') {
    return hour12 === 12 ? 0 : hour12;
  }
  return hour12 === 12 ? 12 : hour12 + 12;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function BriefingSettings() {
  const { user, isLoaded } = useUser();
  const userId = user?.id;

  const { data: settings, isLoading } = useBriefingSettings(userId);
  const updateSettings = useUpdateBriefingSettings(userId);

  // Local form state
  const [hour12, setHour12] = useState(8);
  const [minute, setMinute] = useState(0);
  const [period, setPeriod] = useState<'AM' | 'PM'>('AM');
  const [timezone, setTimezone] = useState(getDetectedTimezone());
  const [channels, setChannels] = useState<Set<string>>(
    new Set(['in_app', 'email']),
  );
  const [hasChanges, setHasChanges] = useState(false);

  // Initialize form from API data
  useEffect(() => {
    if (settings) {
      const { hour, period: p } = to12Hour(settings.briefing_hour);
      setHour12(hour);
      setPeriod(p);
      setMinute(settings.briefing_minute);
      setTimezone(settings.briefing_timezone || getDetectedTimezone());
      setChannels(new Set(settings.briefing_channels));
      setHasChanges(false);
    }
  }, [settings]);

  const handleChannelToggle = (channel: string) => {
    setChannels((prev) => {
      const next = new Set(prev);
      if (next.has(channel)) {
        // Don't allow removing the last channel
        if (next.size <= 1) return prev;
        next.delete(channel);
      } else {
        next.add(channel);
      }
      return next;
    });
    setHasChanges(true);
  };

  const handleSave = () => {
    if (!userId) return;

    const payload: BriefingSettingsType = {
      briefing_hour: to24Hour(hour12, period),
      briefing_minute: minute,
      briefing_timezone: timezone,
      briefing_channels: Array.from(channels),
    };

    updateSettings.mutate(payload, {
      onSuccess: () => {
        toast.success('Briefing settings saved. Changes take effect from tomorrow.');
        setHasChanges(false);
      },
      onError: () => {
        toast.error('Failed to save settings. Please try again.');
      },
    });
  };

  if (!isLoaded || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <div className="text-gray-500">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/briefings"
          className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-3"
        >
          <FiArrowLeft className="mr-1" />
          Back to Briefing History
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">
          Briefing Settings
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Configure when and how you receive your daily briefing
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-md divide-y divide-gray-100">
        {/* Briefing Time */}
        <div className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <FiClock className="h-5 w-5 text-indigo-500" />
            <h2 className="text-lg font-semibold text-gray-900">
              Briefing Time
            </h2>
          </div>
          <p className="text-sm text-gray-500 mb-4">
            Choose when you want to receive your daily briefing.
          </p>

          <div className="flex items-center gap-3">
            {/* Hour */}
            <div>
              <label
                htmlFor="briefing-hour"
                className="block text-xs font-medium text-gray-500 mb-1"
              >
                Hour
              </label>
              <select
                id="briefing-hour"
                value={hour12}
                onChange={(e) => {
                  setHour12(parseInt(e.target.value, 10));
                  setHasChanges(true);
                }}
                className="block w-20 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
              >
                {Array.from({ length: 12 }, (_, i) => i + 1).map((h) => (
                  <option key={h} value={h}>
                    {h}
                  </option>
                ))}
              </select>
            </div>

            <span className="mt-5 text-gray-400 font-bold">:</span>

            {/* Minute */}
            <div>
              <label
                htmlFor="briefing-minute"
                className="block text-xs font-medium text-gray-500 mb-1"
              >
                Minute
              </label>
              <select
                id="briefing-minute"
                value={minute}
                onChange={(e) => {
                  setMinute(parseInt(e.target.value, 10));
                  setHasChanges(true);
                }}
                className="block w-20 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
              >
                {[0, 15, 30, 45].map((m) => (
                  <option key={m} value={m}>
                    {m.toString().padStart(2, '0')}
                  </option>
                ))}
              </select>
            </div>

            {/* AM/PM */}
            <div>
              <label
                htmlFor="briefing-period"
                className="block text-xs font-medium text-gray-500 mb-1"
              >
                Period
              </label>
              <select
                id="briefing-period"
                value={period}
                onChange={(e) => {
                  setPeriod(e.target.value as 'AM' | 'PM');
                  setHasChanges(true);
                }}
                className="block w-20 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
              >
                <option value="AM">AM</option>
                <option value="PM">PM</option>
              </select>
            </div>
          </div>
        </div>

        {/* Timezone */}
        <div className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <FiGlobe className="h-5 w-5 text-indigo-500" />
            <h2 className="text-lg font-semibold text-gray-900">Timezone</h2>
          </div>
          <p className="text-sm text-gray-500 mb-4">
            We detected your timezone as{' '}
            <span className="font-medium text-gray-700">
              {getDetectedTimezone()}
            </span>
            . You can change it below.
          </p>

          <select
            id="briefing-timezone"
            value={timezone}
            onChange={(e) => {
              setTimezone(e.target.value);
              setHasChanges(true);
            }}
            className="block w-full max-w-sm rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
          >
            {COMMON_TIMEZONES.map((tz) => (
              <option key={tz} value={tz}>
                {tz.replace(/_/g, ' ')}
              </option>
            ))}
            {/* If current value not in list, add it */}
            {!COMMON_TIMEZONES.includes(timezone) && (
              <option value={timezone}>
                {timezone.replace(/_/g, ' ')} (current)
              </option>
            )}
          </select>
        </div>

        {/* Delivery Channels */}
        <div className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <FiMail className="h-5 w-5 text-indigo-500" />
            <h2 className="text-lg font-semibold text-gray-900">
              Delivery Channels
            </h2>
          </div>
          <p className="text-sm text-gray-500 mb-4">
            Choose how you want to receive your briefing. At least one channel
            is required.
          </p>

          <div className="space-y-3">
            <label className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
              <input
                type="checkbox"
                checked={channels.has('in_app')}
                onChange={() => handleChannelToggle('in_app')}
                className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              <FiMonitor className="h-5 w-5 text-gray-400" />
              <div>
                <p className="text-sm font-medium text-gray-900">In-App</p>
                <p className="text-xs text-gray-500">
                  View your briefing on the Dashboard
                </p>
              </div>
            </label>

            <label className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
              <input
                type="checkbox"
                checked={channels.has('email')}
                onChange={() => handleChannelToggle('email')}
                className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              <FiMail className="h-5 w-5 text-gray-400" />
              <div>
                <p className="text-sm font-medium text-gray-900">Email</p>
                <p className="text-xs text-gray-500">
                  Receive a briefing email at{' '}
                  {user?.emailAddresses?.[0]?.emailAddress || 'your email'}
                </p>
              </div>
            </label>
          </div>
        </div>

        {/* Save button */}
        <div className="p-6 bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <FiInfo className="h-4 w-4" />
              <span>Changes take effect from your next scheduled briefing.</span>
            </div>
            <button
              onClick={handleSave}
              disabled={!hasChanges || updateSettings.isPending}
              className="inline-flex items-center px-4 py-2 text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <FiSave className="mr-1.5" />
              {updateSettings.isPending ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
