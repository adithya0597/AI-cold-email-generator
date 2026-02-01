/**
 * Applications API service and TanStack Query hooks.
 *
 * Provides typed functions and hooks for:
 *   - Fetching paginated application history
 *   - Updating application status (drag & drop)
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { AxiosInstance } from 'axios';
import { useApiClient } from './api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ApplicationItem {
  id: string;
  job_id: string;
  job_title: string | null;
  company: string | null;
  status: string;
  applied_at: string;
  resume_version_id: string | null;
  updated_at?: string | null;
  last_updated_by?: string | null;
}

export interface ApplicationListResponse {
  applications: ApplicationItem[];
  total: number;
  has_more: boolean;
}

export interface UpdateStatusResponse {
  id: string;
  old_status: string;
  new_status: string;
}

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const applicationKeys = {
  all: ['applications'] as const,
  list: (status?: string) => ['applications', 'list', status] as const,
};

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

async function fetchApplications(
  api: AxiosInstance,
  status?: string,
  limit: number = 20,
  offset: number = 0,
): Promise<ApplicationListResponse> {
  const { data } = await api.get('/api/v1/applications/history', {
    params: { status, limit, offset },
  });
  return data;
}

async function updateApplicationStatus(
  api: AxiosInstance,
  applicationId: string,
  newStatus: string,
): Promise<UpdateStatusResponse> {
  const { data } = await api.patch(`/api/v1/applications/${applicationId}/status`, {
    status: newStatus,
  });
  return data;
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useApplications(status?: string) {
  const api = useApiClient();
  return useQuery({
    queryKey: applicationKeys.list(status),
    queryFn: () => fetchApplications(api, status),
  });
}

export function useUpdateApplicationStatus() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ applicationId, status }: { applicationId: string; status: string }) =>
      updateApplicationStatus(api, applicationId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: applicationKeys.all });
    },
  });
}
