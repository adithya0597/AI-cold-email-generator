/**
 * Privacy/Stealth Mode service hooks.
 *
 * TanStack Query hooks for managing stealth mode status and toggling.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useApiClient } from './api';

export interface StealthStatus {
  stealth_enabled: boolean;
  tier: string | null;
  eligible: boolean;
}

const privacyKeys = {
  all: ['privacy'] as const,
  stealth: () => [...privacyKeys.all, 'stealth'] as const,
};

export function useStealthStatus() {
  const api = useApiClient();
  return useQuery({
    queryKey: privacyKeys.stealth(),
    queryFn: async (): Promise<StealthStatus> => {
      const res = await api.get('/api/v1/privacy/stealth');
      return res.data;
    },
  });
}

export function useToggleStealth() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ enabled }: { enabled: boolean }) => {
      const res = await api.post('/api/v1/privacy/stealth', { enabled });
      return res.data as StealthStatus;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: privacyKeys.stealth() });
    },
  });
}
