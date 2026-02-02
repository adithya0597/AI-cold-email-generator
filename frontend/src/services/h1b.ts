/**
 * H1B sponsor API service and TanStack Query hooks.
 *
 * Provides typed functions and hooks for:
 *   - Fetching individual sponsor data
 *   - Searching sponsors by name
 */

import { useQuery } from '@tanstack/react-query';
import type { AxiosInstance } from 'axios';
import { useApiClient } from './api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SponsorFreshness {
  h1bgrader: string | null;
  myvisajobs: string | null;
  uscis: string | null;
}

export interface SponsorData {
  company_name: string;
  company_name_normalized: string;
  domain: string | null;
  total_petitions: number;
  approval_rate: number | null;
  avg_wage: number | null;
  wage_source: string | null;
  freshness: SponsorFreshness;
  updated_at: string | null;
}

export interface SponsorSearchResult {
  total: number;
  sponsors: SponsorData[];
}

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const h1bKeys = {
  all: ['h1b'] as const,
  sponsor: (company: string) => ['h1b', 'sponsor', company] as const,
  search: (query: string) => ['h1b', 'search', query] as const,
};

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

async function fetchSponsor(
  api: AxiosInstance,
  company: string,
): Promise<SponsorData> {
  const { data } = await api.get(`/api/v1/h1b/sponsors/${encodeURIComponent(company)}`);
  return data;
}

async function searchSponsors(
  api: AxiosInstance,
  query: string,
): Promise<SponsorSearchResult> {
  const { data } = await api.get('/api/v1/h1b/sponsors', {
    params: { q: query },
  });
  return data;
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useSponsorData(company: string) {
  const api = useApiClient();
  return useQuery({
    queryKey: h1bKeys.sponsor(company),
    queryFn: () => fetchSponsor(api, company),
    enabled: !!company,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useSponsorSearch(query: string) {
  const api = useApiClient();
  return useQuery({
    queryKey: h1bKeys.search(query),
    queryFn: () => searchSponsors(api, query),
    enabled: query.length >= 2,
    staleTime: 5 * 60 * 1000,
  });
}
