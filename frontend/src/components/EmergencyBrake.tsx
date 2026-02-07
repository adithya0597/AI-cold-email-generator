/**
 * EmergencyBrake -- always-visible brake button in the app header.
 *
 * Shows current agent state (Active / Pausing / Paused) with a
 * colored indicator dot.  Clicking the button immediately activates
 * or deactivates the emergency brake (no confirmation dialog --
 * speed is critical per Story 3-6 AC).
 *
 * State updates arrive via:
 *   1. WebSocket events (instant)
 *   2. Polling GET /agents/brake/status every 5 s while in "pausing" state
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth, useUser } from '../providers/ClerkProvider';
import { createReconnect, type ReconnectController } from '../lib/ws-reconnect';
import { useApiClient } from '../services/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');

type BrakeState = 'running' | 'pausing' | 'paused' | 'partial' | 'resuming';

interface BrakeStatus {
  state: BrakeState;
  activated_at: string | null;
  paused_tasks_count: number;
}

const STATE_CONFIG: Record<
  BrakeState,
  { dot: string; label: string; animate?: boolean }
> = {
  running: { dot: 'bg-green-500', label: 'Agents Active' },
  pausing: { dot: 'bg-yellow-400', label: 'Pausing...', animate: true },
  paused: { dot: 'bg-red-500', label: 'Agents Paused' },
  partial: { dot: 'bg-orange-500', label: 'Partially Paused' },
  resuming: { dot: 'bg-yellow-400', label: 'Resuming...', animate: true },
};

export default function EmergencyBrake() {
  const { getToken, isSignedIn } = useAuth();
  const { user } = useUser();
  const apiClient = useApiClient();

  const [brakeState, setBrakeState] = useState<BrakeState>('running');
  const [loading, setLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectRef = useRef<ReconnectController>(createReconnect());

  const userId = user?.id;

  // ------------------------------------------------------------------
  // Fetch initial brake status
  // ------------------------------------------------------------------
  const fetchStatus = useCallback(async () => {
    if (!userId) return;
    try {
      const res = await apiClient.get<BrakeStatus>(
        `/api/v1/agents/brake/status?user_id=${userId}`
      );
      setBrakeState(res.data.state);
    } catch {
      // Silently degrade -- assume running if API unreachable
    }
  }, [apiClient, userId]);

  // ------------------------------------------------------------------
  // WebSocket connection with auto-reconnect
  // ------------------------------------------------------------------
  const connectWebSocket = useCallback(async () => {
    if (!userId) return;

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    let token = '';
    try {
      token = (await getToken()) || '';
    } catch {
      // Fall back to polling only
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
        if (data.type === 'system.brake.activated') {
          setBrakeState('pausing');
        } else if (data.type === 'system.brake.resumed') {
          setBrakeState('running');
        } else if (data.type === 'system.brake.paused') {
          setBrakeState('paused');
        } else if (data.type === 'system.brake.partial') {
          setBrakeState('partial');
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
  // Poll while in transitional states (pausing / resuming)
  // ------------------------------------------------------------------
  useEffect(() => {
    if (brakeState === 'pausing' || brakeState === 'resuming') {
      pollTimerRef.current = setInterval(fetchStatus, 5000);
    } else if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [brakeState, fetchStatus]);

  // ------------------------------------------------------------------
  // Lifecycle: connect on mount, disconnect on unmount
  // ------------------------------------------------------------------
  useEffect(() => {
    if (isSignedIn && userId) {
      fetchStatus();
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
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, [isSignedIn, userId, fetchStatus, connectWebSocket]);

  // ------------------------------------------------------------------
  // Handlers
  // ------------------------------------------------------------------
  const handleActivateBrake = async () => {
    if (!userId || loading) return;
    setLoading(true);
    try {
      const res = await apiClient.post<{ state: string }>(
        `/api/v1/agents/brake?user_id=${userId}`
      );
      setBrakeState(res.data.state as BrakeState);
    } catch {
      // Silently fail -- WebSocket / poll will update state
    } finally {
      setLoading(false);
    }
  };

  const handleResume = async () => {
    if (!userId || loading) return;
    setLoading(true);
    try {
      const res = await apiClient.post<{ state: string }>(
        `/api/v1/agents/resume?user_id=${userId}`
      );
      setBrakeState(res.data.state as BrakeState);
    } catch {
      // Silently fail
    } finally {
      setLoading(false);
    }
  };

  // ------------------------------------------------------------------
  // Don't render if not signed in
  // ------------------------------------------------------------------
  if (!isSignedIn || !userId) return null;

  const config = STATE_CONFIG[brakeState] || STATE_CONFIG.running;
  const isBraked = brakeState === 'paused' || brakeState === 'partial';
  const isPausing = brakeState === 'pausing';
  const isResuming = brakeState === 'resuming';
  const isTransitioning = isPausing || isResuming;

  return (
    <div className="flex items-center gap-2">
      {/* State indicator */}
      <div className="flex items-center gap-1.5">
        <span
          className={`inline-block h-2 w-2 rounded-full ${config.dot} ${
            config.animate ? 'animate-pulse' : ''
          }`}
        />
        <span className="text-xs text-gray-500 hidden lg:inline">
          {config.label}
        </span>
      </div>

      {/* Brake / Resume button */}
      {isBraked ? (
        <button
          onClick={handleResume}
          disabled={loading || isTransitioning}
          className="inline-flex items-center gap-1 px-3 py-1 text-xs font-semibold rounded-md bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Resume
        </button>
      ) : (
        <button
          onClick={handleActivateBrake}
          disabled={loading || isTransitioning}
          className="inline-flex items-center gap-1 px-3 py-1 text-xs font-semibold rounded-md bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isPausing ? 'Pausing...' : 'Stop Agents'}
        </button>
      )}
    </div>
  );
}
