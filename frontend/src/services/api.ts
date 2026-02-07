import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';
import { useMemo } from 'react';
import { useAuth, isDevAuthMode } from '../providers/ClerkProvider';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ----------------------------------------------------------------
// Public (unauthenticated) axios instance
// Used for health checks and other public endpoints.
// ----------------------------------------------------------------
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling (shared behavior)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clerk handles auth redirects; just clear any stale local state
      // and redirect to sign-in
      window.location.href = '/sign-in';
    }
    return Promise.reject(error);
  }
);

// ----------------------------------------------------------------
// useApiClient -- React hook that returns an axios instance with
// Clerk JWT automatically attached to every request.
//
// Usage:
//   const apiClient = useApiClient();
//   const data = await apiClient.get('/api/v1/users/me');
// ----------------------------------------------------------------
// Dev mode: simple axios instance without Clerk auth (module-level singleton)
const devApiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
});

function useDevApiClient(): AxiosInstance {
  return devApiClient;
}

function useClerkApiClient(): AxiosInstance {
  const { getToken } = useAuth();

  const authenticatedApi = useMemo(() => {
    const instance = axios.create({
      baseURL: API_BASE_URL,
      timeout: 60000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor: attach Clerk JWT as Bearer token
    instance.interceptors.request.use(
      async (config: InternalAxiosRequestConfig) => {
        try {
          const token = await getToken();
          if (token) {
            config.headers.Authorization = `Bearer ${token}`;
          }
        } catch (_error) {
          // If token fetch fails, proceed without auth header.
          // The server will return 401 and the response interceptor handles it.
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    instance.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          window.location.href = '/sign-in';
        }
        return Promise.reject(error);
      }
    );

    return instance;
  }, [getToken]);

  return authenticatedApi;
}

export const useApiClient: () => AxiosInstance = isDevAuthMode
  ? useDevApiClient
  : useClerkApiClient;

// ----------------------------------------------------------------
// Legacy service wrappers (preserved for backward compatibility)
// These use the public api instance. Migrate callers to useApiClient
// for authenticated endpoints.
// ----------------------------------------------------------------

export const emailService = {
  generateEmail: async (data: Record<string, unknown>) => {
    const response = await api.post('/api/generate-email', data);
    return response.data;
  },

  parseResume: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/api/parse-resume', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getEmailStats: async (emailId: string) => {
    const response = await api.get(`/api/email/${emailId}/stats`);
    return response.data;
  },

  getTrackingPixelUrl: (emailId: string): string => {
    return `${API_BASE_URL}/api/track/email/${emailId}/pixel.gif`;
  },
};

export const linkedInService = {
  generatePost: async (data: Record<string, unknown>) => {
    const response = await api.post('/api/generate-post', data);
    return response.data;
  },
};

export const utilityService = {
  scrapeUrl: async (url: string) => {
    const response = await api.post('/api/scrape-url', { url });
    return response.data;
  },

  checkHealth: async () => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;
