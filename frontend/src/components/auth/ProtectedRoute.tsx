/**
 * ProtectedRoute -- requires Clerk authentication and syncs user record.
 *
 * If the user is not signed in, redirects to /sign-in.
 * On mount (when authenticated), calls POST /api/v1/auth/sync to ensure
 * a local user record exists. Uses the is_new flag to navigate new users
 * to /onboarding and returning users to /dashboard.
 */

import { useEffect, useRef, useState } from 'react';
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@clerk/clerk-react';
import { useApiClient } from '../../services/api';

export default function ProtectedRoute() {
  const { isSignedIn, isLoaded } = useAuth();
  const apiClient = useApiClient();
  const navigate = useNavigate();
  const location = useLocation();
  const syncCalled = useRef(false);
  const [syncDone, setSyncDone] = useState(false);

  useEffect(() => {
    if (!isLoaded || !isSignedIn || syncCalled.current) return;
    syncCalled.current = true;

    apiClient
      .post('/api/v1/auth/sync')
      .then((res) => {
        const { is_new } = res.data;
        if (is_new && location.pathname !== '/onboarding') {
          navigate('/onboarding', { replace: true });
        }
      })
      .catch((err) => {
        // Sync failure is non-blocking -- user can still use the app.
        // Auth interceptor handles 401 redirects.
        console.error('User sync failed:', err);
      })
      .finally(() => {
        setSyncDone(true);
      });
  }, [isLoaded, isSignedIn, apiClient, navigate, location.pathname]);

  // Wait for Clerk to load before making any routing decisions
  if (!isLoaded) {
    return null;
  }

  if (!isSignedIn) {
    return <Navigate to="/sign-in" replace />;
  }

  // Render children immediately; sync runs in the background
  return <Outlet />;
}
