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

export interface BlocklistEntry {
  id: string;
  company_name: string;
  note: string | null;
  created_at: string | null;
}

export interface BlocklistResponse {
  entries: BlocklistEntry[];
  total: number;
}

export interface AuditLogEntry {
  id: string;
  company_name: string;
  action_type: string;
  details: string | null;
  created_at: string | null;
}

export interface PrivacyProofEntry {
  company_name: string;
  note: string | null;
  last_checked: string;
  exposure_count: number;
  blocked_actions: AuditLogEntry[];
}

export interface PrivacyProofResponse {
  entries: PrivacyProofEntry[];
  total: number;
}

const privacyKeys = {
  all: ['privacy'] as const,
  stealth: () => [...privacyKeys.all, 'stealth'] as const,
  blocklist: () => [...privacyKeys.all, 'blocklist'] as const,
  proof: () => [...privacyKeys.all, 'proof'] as const,
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

export function useBlocklist() {
  const api = useApiClient();
  return useQuery({
    queryKey: privacyKeys.blocklist(),
    queryFn: async (): Promise<BlocklistResponse> => {
      const res = await api.get('/api/v1/privacy/blocklist');
      return res.data;
    },
  });
}

export function useAddToBlocklist() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ company_name, note }: { company_name: string; note?: string }) => {
      const res = await api.post('/api/v1/privacy/blocklist', { company_name, note });
      return res.data as BlocklistEntry;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: privacyKeys.blocklist() });
    },
  });
}

export function useRemoveFromBlocklist() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ entryId }: { entryId: string }) => {
      await api.delete(`/api/v1/privacy/blocklist/${entryId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: privacyKeys.blocklist() });
    },
  });
}

export function usePrivacyProof() {
  const api = useApiClient();
  return useQuery({
    queryKey: privacyKeys.proof(),
    queryFn: async (): Promise<PrivacyProofResponse> => {
      const res = await api.get('/api/v1/privacy/proof');
      return res.data;
    },
  });
}

export function useDownloadReport() {
  const api = useApiClient();
  return useMutation({
    mutationFn: async () => {
      const res = await api.get('/api/v1/privacy/proof/report');
      return res.data;
    },
  });
}
