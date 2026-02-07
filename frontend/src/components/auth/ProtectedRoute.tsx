/**
 * ProtectedRoute -- requires authentication and syncs user record.
 *
 * If the user is not signed in, redirects to /sign-in.
 * On mount (when authenticated), calls POST /api/v1/auth/sync to ensure
 * a local user record exists. Uses the is_new flag to navigate new users
 * to /onboarding and returning users to /dashboard.
 *
 * In dev auth mode (no Clerk key), useAuth returns stub values so the
 * user is always treated as authenticated.
 */

import { useEffect, useRef } from 'react';
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../providers/ClerkProvider';
import { useApiClient } from '../../services/api';

export default function ProtectedRoute() {
  const { isSignedIn, isLoaded } = useAuth();
  const apiClient = useApiClient();
  const navigate = useNavigate();
  const location = useLocation();
  const syncCalled = useRef(false);

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
        console.error('User sync failed:', err);
      });
  }, [isLoaded, isSignedIn, apiClient, navigate, location.pathname]);

  if (!isLoaded) {
    return null;
  }

  if (!isSignedIn) {
    return <Navigate to="/sign-in" replace />;
  }

  return <Outlet />;
}
