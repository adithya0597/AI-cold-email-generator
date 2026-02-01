/**
 * Learned Preferences API service and TanStack Query hooks.
 *
 * Provides typed functions and hooks for:
 *   - Fetching learned preferences
 *   - Updating learned preference status (acknowledge/reject)
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { AxiosInstance } from 'axios';
import { useApiClient } from './api';
import type { LearnedPreference, LearnedPreferenceListResponse } from '../types/matches';

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const learnedPrefKeys = {
  all: ['learned-preferences'] as const,
  list: () => ['learned-preferences', 'list'] as const,
};

// ---------------------------------------------------------------------------
// API functions (require authenticated axios instance)
// ---------------------------------------------------------------------------

export async function fetchLearnedPreferences(
  api: AxiosInstance,
): Promise<LearnedPreferenceListResponse> {
  const { data } = await api.get('/api/v1/preferences/learned');
  return data;
}

export async function updateLearnedPreference(
  api: AxiosInstance,
  id: string,
  status: 'acknowledged' | 'rejected',
): Promise<LearnedPreference> {
  const { data } = await api.patch(`/api/v1/preferences/learned/${id}`, { status });
  return data;
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useLearnedPreferences() {
  const api = useApiClient();
  return useQuery({
    queryKey: learnedPrefKeys.list(),
    queryFn: () => fetchLearnedPreferences(api),
    select: (response) => response.data.filter((p) => p.status === 'pending'),
  });
}

export function useUpdateLearnedPreference() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'acknowledged' | 'rejected' }) =>
      updateLearnedPreference(api, id, status),
    onMutate: async ({ id }) => {
      await queryClient.cancelQueries({ queryKey: learnedPrefKeys.list() });

      const previous = queryClient.getQueryData<LearnedPreferenceListResponse>(
        learnedPrefKeys.list(),
      );

      if (previous) {
        queryClient.setQueryData<LearnedPreferenceListResponse>(learnedPrefKeys.list(), {
          ...previous,
          data: previous.data.filter((p) => p.id !== id),
        });
      }

      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(learnedPrefKeys.list(), context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: learnedPrefKeys.all });
    },
  });
}
