/**
 * Follow-up suggestions API service and TanStack Query hooks.
 *
 * Provides typed functions and hooks for:
 *   - Fetching pending follow-up suggestions
 *   - Updating draft subject/body
 *   - Sending a follow-up (marks as sent)
 *   - Copying to clipboard (marks as sent)
 *   - Dismissing a suggestion
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { AxiosInstance } from 'axios';
import { useApiClient } from './api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface FollowupSuggestion {
  id: string;
  application_id: string;
  company: string | null;
  job_title: string | null;
  status: string | null;
  followup_date: string | null;
  draft_subject: string | null;
  draft_body: string | null;
  created_at: string | null;
}

export interface FollowupListResponse {
  suggestions: FollowupSuggestion[];
  total: number;
}

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const followupKeys = {
  all: ['followups'] as const,
  list: () => ['followups', 'list'] as const,
};

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

async function fetchFollowups(api: AxiosInstance): Promise<FollowupListResponse> {
  const { data } = await api.get('/api/v1/applications/followups');
  return data;
}

async function updateDraft(
  api: AxiosInstance,
  suggestionId: string,
  updates: { draft_subject?: string; draft_body?: string },
): Promise<{ status: string; suggestion_id: string }> {
  const { data } = await api.patch(
    `/api/v1/applications/followups/${suggestionId}/draft`,
    updates,
  );
  return data;
}

async function sendFollowup(
  api: AxiosInstance,
  suggestionId: string,
): Promise<{ status: string; suggestion_id: string }> {
  const { data } = await api.post(
    `/api/v1/applications/followups/${suggestionId}/send`,
  );
  return data;
}

async function dismissFollowup(
  api: AxiosInstance,
  suggestionId: string,
): Promise<{ status: string; suggestion_id: string }> {
  const { data } = await api.patch(
    `/api/v1/applications/followups/${suggestionId}/dismiss`,
  );
  return data;
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useFollowups() {
  const api = useApiClient();
  return useQuery({
    queryKey: followupKeys.list(),
    queryFn: () => fetchFollowups(api),
  });
}

export function useUpdateDraft() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      suggestionId,
      updates,
    }: {
      suggestionId: string;
      updates: { draft_subject?: string; draft_body?: string };
    }) => updateDraft(api, suggestionId, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: followupKeys.all });
    },
  });
}

export function useSendFollowup() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ suggestionId }: { suggestionId: string }) =>
      sendFollowup(api, suggestionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: followupKeys.all });
    },
  });
}

export function useDismissFollowup() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ suggestionId }: { suggestionId: string }) =>
      dismissFollowup(api, suggestionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: followupKeys.all });
    },
  });
}

export function useCopyFollowup() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ suggestionId, subject, body }: {
      suggestionId: string;
      subject: string;
      body: string;
    }) => {
      await navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`);
      return sendFollowup(api, suggestionId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: followupKeys.all });
    },
  });
}
