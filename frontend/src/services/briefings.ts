/**
 * Briefing API service and TanStack Query hooks.
 *
 * Provides typed functions and hooks for:
 *   - Fetching the latest briefing
 *   - Fetching briefing history (paginated)
 *   - Fetching a single briefing by ID
 *   - Marking a briefing as read
 *   - Reading and updating briefing settings
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { AxiosInstance } from 'axios';
import { useApiClient } from './api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface BriefingContent {
  summary?: string;
  actions_needed?: string[];
  new_matches?: Array<{
    title: string;
    company: string;
    match_score?: number;
    url?: string;
  }>;
  activity_log?: Array<{
    event: string;
    timestamp: string;
    agent_type?: string;
  }>;
  metrics?: {
    total_matches?: number;
    pending_approvals?: number;
    applications_sent?: number;
  };
  tips?: string[];
  message?: string;
}

export interface Briefing {
  id: string;
  user_id: string;
  content: BriefingContent;
  briefing_type: 'full' | 'lite';
  generated_at: string;
  delivered_at: string | null;
  delivery_channels: string[];
  read_at: string | null;
  schema_version: number;
}

export interface BriefingHistoryResponse {
  briefings: Briefing[];
  total: number;
  has_more: boolean;
}

export interface BriefingSettings {
  briefing_hour: number;
  briefing_minute: number;
  briefing_timezone: string;
  briefing_channels: string[];
}

// ---------------------------------------------------------------------------
// API functions (require authenticated axios instance)
// ---------------------------------------------------------------------------

async function fetchLatestBriefing(
  api: AxiosInstance,
  userId: string,
): Promise<Briefing | null> {
  const { data } = await api.get('/api/v1/briefings/latest', {
    params: { user_id: userId },
  });
  return data;
}

async function fetchBriefingHistory(
  api: AxiosInstance,
  userId: string,
  limit: number,
  offset: number,
): Promise<BriefingHistoryResponse> {
  const { data } = await api.get('/api/v1/briefings', {
    params: { user_id: userId, limit, offset },
  });
  return data;
}

async function fetchBriefingById(
  api: AxiosInstance,
  userId: string,
  briefingId: string,
): Promise<Briefing> {
  const { data } = await api.get(`/api/v1/briefings/${briefingId}`, {
    params: { user_id: userId },
  });
  return data;
}

async function markBriefingRead(
  api: AxiosInstance,
  userId: string,
  briefingId: string,
): Promise<void> {
  await api.post(`/api/v1/briefings/${briefingId}/read`, null, {
    params: { user_id: userId },
  });
}

async function fetchBriefingSettings(
  api: AxiosInstance,
  userId: string,
): Promise<BriefingSettings> {
  const { data } = await api.get('/api/v1/briefings/settings', {
    params: { user_id: userId },
  });
  return data;
}

async function updateBriefingSettings(
  api: AxiosInstance,
  userId: string,
  settings: BriefingSettings,
): Promise<BriefingSettings> {
  const { data } = await api.put('/api/v1/briefings/settings', settings, {
    params: { user_id: userId },
  });
  return data;
}

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const briefingKeys = {
  all: ['briefings'] as const,
  latest: (userId: string) => ['briefings', 'latest', userId] as const,
  history: (userId: string, offset: number) =>
    ['briefings', 'history', userId, offset] as const,
  detail: (userId: string, id: string) =>
    ['briefings', 'detail', userId, id] as const,
  settings: (userId: string) => ['briefings', 'settings', userId] as const,
};

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useLatestBriefing(userId: string | undefined) {
  const api = useApiClient();
  return useQuery({
    queryKey: briefingKeys.latest(userId ?? ''),
    queryFn: () => fetchLatestBriefing(api, userId!),
    enabled: !!userId,
  });
}

export function useBriefingHistory(
  userId: string | undefined,
  limit = 20,
  offset = 0,
) {
  const api = useApiClient();
  return useQuery({
    queryKey: briefingKeys.history(userId ?? '', offset),
    queryFn: () => fetchBriefingHistory(api, userId!, limit, offset),
    enabled: !!userId,
  });
}

export function useBriefing(
  userId: string | undefined,
  briefingId: string | undefined,
) {
  const api = useApiClient();
  return useQuery({
    queryKey: briefingKeys.detail(userId ?? '', briefingId ?? ''),
    queryFn: () => fetchBriefingById(api, userId!, briefingId!),
    enabled: !!userId && !!briefingId,
  });
}

export function useMarkBriefingRead(userId: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (briefingId: string) =>
      markBriefingRead(api, userId!, briefingId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: briefingKeys.latest(userId ?? ''),
      });
      queryClient.invalidateQueries({
        queryKey: briefingKeys.all,
      });
    },
  });
}

export function useBriefingSettings(userId: string | undefined) {
  const api = useApiClient();
  return useQuery({
    queryKey: briefingKeys.settings(userId ?? ''),
    queryFn: () => fetchBriefingSettings(api, userId!),
    enabled: !!userId,
  });
}

export function useUpdateBriefingSettings(userId: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (settings: BriefingSettings) =>
      updateBriefingSettings(api, userId!, settings),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: briefingKeys.settings(userId ?? ''),
      });
    },
  });
}
