import posthog from 'posthog-js';

const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY || '';

/**
 * Hook for tracking analytics events throughout the app.
 * Returns a `track` function that silently no-ops when PostHog is not configured.
 *
 * Usage:
 *   const { track } = useAnalytics();
 *   track('onboarding_started', { source: 'resume' });
 */
export function useAnalytics() {
  return {
    track: (event: string, properties?: Record<string, unknown>) => {
      try {
        if (POSTHOG_KEY) {
          posthog.capture(event, properties);
        }
      } catch {
        // Analytics must never break user flow
      }
    },
  };
}
