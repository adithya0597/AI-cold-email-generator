/**
 * AgentActivityFeed -- real-time agent activity feed component.
 *
 * Loads initial activities from GET /agents/activity and subscribes
 * to the WebSocket channel for real-time updates.  New events are
 * prepended to the list.  Supports "Load More" pagination.
 *
 * Event types are mapped to icons and severity colors:
 *   - agent.*.searching  -> spinner (blue)
 *   - agent.*.completed  -> check (green)
 *   - system.brake.*     -> warning (yellow)
 *   - system.briefing.*  -> bell (blue)
 *   - approval.new       -> attention (red)
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth, useUser } from '@clerk/clerk-react';
import { createReconnect, type ReconnectController } from '../lib/ws-reconnect';
import {
  FiSearch,
  FiCheckCircle,
  FiAlertTriangle,
  FiBell,
  FiAlertCircle,
  FiActivity,
  FiLoader,
} from 'react-icons/fi';
import { useApiClient } from '../services/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');

interface ActivityItem {
  id: string;
  event_type: string;
  agent_type: string | null;
  title: string;
  severity: string;
  data: Record<string, unknown>;
  created_at: string;
}

// ---------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------

function getEventIcon(eventType: string) {
  if (eventType.includes('searching')) return <FiSearch className="w-4 h-4" />;
  if (eventType.includes('completed'))
    return <FiCheckCircle className="w-4 h-4" />;
  if (eventType.startsWith('system.brake'))
    return <FiAlertTriangle className="w-4 h-4" />;
  if (eventType.startsWith('system.briefing'))
    return <FiBell className="w-4 h-4" />;
  if (eventType.startsWith('approval'))
    return <FiAlertCircle className="w-4 h-4" />;
  return <FiActivity className="w-4 h-4" />;
}

function getSeverityColor(severity: string) {
  switch (severity) {
    case 'warning':
      return 'text-yellow-600 bg-yellow-50';
    case 'action_required':
      return 'text-red-600 bg-red-50';
    default:
      return 'text-blue-600 bg-blue-50';
  }
}

function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;

  if (diffMs < 0) return 'just now';

  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 60) return 'just now';

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

// ---------------------------------------------------------------
// Component
// ---------------------------------------------------------------

export default function AgentActivityFeed() {
  const { getToken, isSignedIn } = useAuth();
  const { user } = useUser();
  const apiClient = useApiClient();

  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectRef = useRef<ReconnectController>(createReconnect());

  const userId = user?.id;

  // ------------------------------------------------------------------
  // Fetch activities from REST API
  // ------------------------------------------------------------------
  const fetchActivities = useCallback(
    async (offset = 0, append = false) => {
      if (!userId) return;
      if (append) setLoadingMore(true);
      else setLoading(true);

      try {
        const res = await apiClient.get<{
          activities: ActivityItem[];
          total: number;
          has_more: boolean;
        }>(`/api/v1/agents/activity?user_id=${userId}&limit=20&offset=${offset}`);

        if (append) {
          setActivities((prev) => [...prev, ...res.data.activities]);
        } else {
          setActivities(res.data.activities);
        }
        setTotal(res.data.total);
      } catch {
        // Silently degrade
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [apiClient, userId]
  );

  // ------------------------------------------------------------------
  // WebSocket connection for real-time updates
  // ------------------------------------------------------------------
  const connectWebSocket = useCallback(async () => {
    if (!userId) return;

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    let token = '';
    try {
      token = (await getToken()) || '';
    } catch {
      return;
    }

    const ws = new WebSocket(
      `${WS_BASE_URL}/api/v1/ws/agents/${userId}?token=${encodeURIComponent(token)}`
    );

    ws.onopen = () => {
      reconnectRef.current.reset();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // Only add agent.* and system.* events to the feed
        if (
          data.type &&
          (data.type.startsWith('agent.') ||
            data.type.startsWith('system.') ||
            data.type.startsWith('approval.'))
        ) {
          const newItem: ActivityItem = {
            id: data.event_id || `ws-${Date.now()}`,
            event_type: data.type,
            agent_type: data.agent_type || null,
            title: data.title || data.type,
            severity: data.severity || 'info',
            data: data,
            created_at: data.timestamp || new Date().toISOString(),
          };
          setActivities((prev) => [newItem, ...prev]);
          setTotal((prev) => prev + 1);
        }
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
      const delay = reconnectRef.current.nextDelay();
      reconnectTimerRef.current = setTimeout(() => {
        connectWebSocket();
      }, delay);
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [userId, getToken]);

  // ------------------------------------------------------------------
  // Lifecycle
  // ------------------------------------------------------------------
  useEffect(() => {
    if (isSignedIn && userId) {
      fetchActivities();
      connectWebSocket();
    }
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
    };
  }, [isSignedIn, userId, fetchActivities, connectWebSocket]);

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------
  if (!isSignedIn || !userId) return null;

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Agent Activity</h2>
        <div className="flex items-center justify-center py-8 text-gray-400">
          <FiLoader className="animate-spin mr-2" />
          Loading activity...
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Agent Activity</h2>

      {activities.length === 0 ? (
        <div className="text-center py-8">
          <FiActivity className="mx-auto h-8 w-8 text-gray-300 mb-3" />
          <p className="text-sm text-gray-500">
            No agent activity yet. Configure your preferences to get started!
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {activities.map((item) => (
            <div
              key={item.id}
              className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
            >
              {/* Icon */}
              <div
                className={`flex-shrink-0 p-2 rounded-full ${getSeverityColor(
                  item.severity
                )}`}
              >
                {getEventIcon(item.event_type)}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {item.title}
                </p>
                {item.agent_type && (
                  <p className="text-xs text-gray-400 mt-0.5">
                    {item.agent_type.replace('_', ' ')}
                  </p>
                )}
              </div>

              {/* Timestamp */}
              <span className="flex-shrink-0 text-xs text-gray-400">
                {timeAgo(item.created_at)}
              </span>
            </div>
          ))}

          {/* Load More */}
          {activities.length < total && (
            <button
              onClick={() => fetchActivities(activities.length, true)}
              disabled={loadingMore}
              className="w-full text-center py-2 text-sm text-primary-600 hover:text-primary-800 disabled:opacity-50"
            >
              {loadingMore ? 'Loading...' : 'Load More'}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
