/**
 * Matches API service and TanStack Query hooks.
 *
 * Provides typed functions and hooks for:
 *   - Fetching paginated matches filtered by status
 *   - Updating match status (save/dismiss)
 *   - Optimistic cache updates on status change
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { AxiosInstance } from 'axios';
import { useApiClient } from './api';
import type { MatchData, MatchListResponse } from '../types/matches';

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const matchKeys = {
  all: ['matches'] as const,
  list: (status: string) => ['matches', 'list', status] as const,
};

// ---------------------------------------------------------------------------
// API functions (require authenticated axios instance)
// ---------------------------------------------------------------------------

async function fetchMatches(
  api: AxiosInstance,
  status: string = 'new',
  page: number = 1,
  perPage: number = 20,
): Promise<MatchListResponse> {
  const { data } = await api.get('/api/v1/matches', {
    params: { status, page, per_page: perPage },
  });
  return data;
}

async function updateMatchStatus(
  api: AxiosInstance,
  matchId: string,
  status: 'saved' | 'dismissed',
): Promise<MatchData> {
  const { data } = await api.patch(`/api/v1/matches/${matchId}`, { status });
  return data;
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useMatches(status: string = 'new', page: number = 1, perPage: number = 20) {
  const api = useApiClient();
  return useQuery({
    queryKey: matchKeys.list(status),
    queryFn: () => fetchMatches(api, status, page, perPage),
  });
}

export function useUpdateMatchStatus() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ matchId, status }: { matchId: string; status: 'saved' | 'dismissed' }) =>
      updateMatchStatus(api, matchId, status),
    onMutate: async ({ matchId, status }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: matchKeys.list('new') });

      // Snapshot previous value
      const previous = queryClient.getQueryData<MatchListResponse>(matchKeys.list('new'));

      // Optimistically remove match from the "new" list
      if (previous) {
        queryClient.setQueryData<MatchListResponse>(matchKeys.list('new'), {
          ...previous,
          data: previous.data.filter((m) => m.id !== matchId),
          meta: {
            ...previous.meta,
            pagination: {
              ...previous.meta.pagination,
              total: Math.max(0, previous.meta.pagination.total - 1),
            },
          },
        });
      }

      return { previous };
    },
    onError: (_err, _vars, context) => {
      // Roll back on error
      if (context?.previous) {
        queryClient.setQueryData(matchKeys.list('new'), context.previous);
      }
    },
    onSettled: () => {
      // Invalidate to refetch
      queryClient.invalidateQueries({ queryKey: matchKeys.all });
    },
  });
}
