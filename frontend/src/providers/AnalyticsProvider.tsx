import posthog from 'posthog-js';
import { useEffect } from 'react';

const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY || '';
const POSTHOG_HOST =
  import.meta.env.VITE_POSTHOG_HOST || 'https://us.i.posthog.com';

let initialized = false;

/**
 * Initialize PostHog analytics. No-ops gracefully when VITE_POSTHOG_KEY is not set.
 *
 * Place inside AuthProvider so Clerk context is available for user identification.
 * User identification is handled separately via identifyUser() calls after auth.
 */
export function AnalyticsProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  useEffect(() => {
    if (!initialized && POSTHOG_KEY) {
      posthog.init(POSTHOG_KEY, {
        api_host: POSTHOG_HOST,
        loaded: (ph) => {
          if (import.meta.env.DEV) ph.debug();
        },
      });
      initialized = true;
    }
  }, []);

  return <>{children}</>;
}

/**
 * Identify the current user in PostHog. Call after authentication.
 * Safe to call when PostHog is not configured -- silently no-ops.
 */
export function identifyUser(
  userId: string,
  properties?: Record<string, unknown>
) {
  try {
    if (POSTHOG_KEY && initialized) {
      posthog.identify(userId, properties);
    }
  } catch {
    // Analytics must never break user flow
  }
}
