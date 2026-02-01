import * as Sentry from "@sentry/react";

/**
 * Initialise the Sentry browser SDK.
 *
 * Call once at module level (e.g. in App.tsx) before the React tree renders.
 * When `VITE_SENTRY_DSN` is not set the function is a no-op so that local
 * development works without any Sentry configuration.
 */
export function initSentry(): void {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!dsn) {
    console.info("Sentry DSN not set -- error tracking disabled");
    return;
  }

  Sentry.init({
    dsn,
    environment: import.meta.env.VITE_APP_ENV || "development",
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration(),
    ],
    tracesSampleRate:
      import.meta.env.VITE_APP_ENV === "production" ? 0.1 : 1.0,
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
  });
}
