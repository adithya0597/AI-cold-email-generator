/**
 * OnboardingGuard -- redirects users who haven't completed onboarding.
 *
 * Wraps protected routes (e.g., /dashboard). Checks onboarding_status
 * via the backend API and redirects accordingly:
 *   - not_started / profile_pending -> /onboarding
 *   - profile_complete / preferences_pending -> /preferences
 *   - complete -> render children
 *
 * Shows a loading spinner while checking status.
 */

import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useApiClient } from '../services/api';
import type { OnboardingStatusResponse } from '../types/onboarding';

interface OnboardingGuardProps {
  children: React.ReactNode;
}

export default function OnboardingGuard({ children }: OnboardingGuardProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const apiClient = useApiClient();
  const [isChecking, setIsChecking] = useState(true);
  const [isAllowed, setIsAllowed] = useState(false);

  // Skip guard for onboarding/preferences paths (shouldn't wrap them, but safety check)
  const skipPaths = ['/onboarding', '/preferences'];
  const shouldSkip = skipPaths.some((p) => location.pathname.startsWith(p));

  useEffect(() => {
    if (shouldSkip) {
      setIsChecking(false);
      setIsAllowed(true);
      return;
    }

    let cancelled = false;

    const checkStatus = async () => {
      try {
        const res = await apiClient.get<OnboardingStatusResponse>('/api/v1/onboarding/status');
        if (cancelled) return;

        const status = res.data.onboarding_status;

        if (status === 'complete') {
          setIsAllowed(true);
        } else if (status === 'not_started' || status === 'profile_pending') {
          navigate('/onboarding', { replace: true });
        } else if (status === 'profile_complete' || status === 'preferences_pending') {
          navigate('/preferences', { replace: true });
        } else {
          // Unknown status -- allow through
          setIsAllowed(true);
        }
      } catch {
        // If API fails, allow through to avoid blocking users
        setIsAllowed(true);
      } finally {
        if (!cancelled) setIsChecking(false);
      }
    };

    checkStatus();

    return () => {
      cancelled = true;
    };
  }, [apiClient, navigate, location.pathname, shouldSkip]);

  if (isChecking) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center">
          <svg
            className="h-8 w-8 animate-spin text-indigo-500"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          <p className="mt-3 text-sm text-gray-500">Checking your account...</p>
        </div>
      </div>
    );
  }

  if (!isAllowed) {
    return null; // Redirect is happening
  }

  return <>{children}</>;
}
