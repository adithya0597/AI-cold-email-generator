/**
 * Tests for the ProtectedRoute component.
 *
 * Verifies:
 * - Redirects to /sign-in when not authenticated
 * - Renders Outlet (child routes) when authenticated
 * - Calls /api/v1/auth/sync on mount when authenticated
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

// Mock @clerk/clerk-react
const mockUseAuth = vi.fn();
vi.mock('@clerk/clerk-react', () => ({
  useAuth: () => mockUseAuth(),
}));

// Mock the API client hook
const mockPost = vi.fn();
vi.mock('../../../services/api', () => ({
  useApiClient: () => ({
    post: mockPost,
  }),
}));

import ProtectedRoute from '../ProtectedRoute';

/**
 * Helper to render ProtectedRoute within a router context.
 * Uses MemoryRouter with initialEntries to control the current path.
 */
function renderProtectedRoute(initialPath = '/dashboard') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/sign-in" element={<div data-testid="sign-in-page">Sign In</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<div data-testid="dashboard-page">Dashboard</div>} />
          <Route path="/onboarding" element={<div data-testid="onboarding-page">Onboarding</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPost.mockResolvedValue({ data: { user: {}, is_new: false } });
  });

  it('renders nothing while Clerk is loading', () => {
    mockUseAuth.mockReturnValue({ isLoaded: false, isSignedIn: false });
    const { container } = renderProtectedRoute();
    // Should render nothing (null)
    expect(container.innerHTML).toBe('');
  });

  it('redirects to /sign-in when not signed in', () => {
    mockUseAuth.mockReturnValue({ isLoaded: true, isSignedIn: false });
    renderProtectedRoute();
    expect(screen.getByTestId('sign-in-page')).toBeDefined();
  });

  it('renders child route (Outlet) when signed in', async () => {
    mockUseAuth.mockReturnValue({ isLoaded: true, isSignedIn: true });
    renderProtectedRoute();
    expect(screen.getByTestId('dashboard-page')).toBeDefined();
  });

  it('calls /api/v1/auth/sync on mount when authenticated', async () => {
    mockUseAuth.mockReturnValue({ isLoaded: true, isSignedIn: true });
    renderProtectedRoute();

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/api/v1/auth/sync');
    });
  });

  it('does not call sync when not signed in', () => {
    mockUseAuth.mockReturnValue({ isLoaded: true, isSignedIn: false });
    renderProtectedRoute();
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('navigates new user to /onboarding after sync', async () => {
    mockUseAuth.mockReturnValue({ isLoaded: true, isSignedIn: true });
    mockPost.mockResolvedValue({ data: { user: {}, is_new: true } });
    renderProtectedRoute('/dashboard');

    await waitFor(() => {
      expect(screen.getByTestId('onboarding-page')).toBeDefined();
    });
  });
});
