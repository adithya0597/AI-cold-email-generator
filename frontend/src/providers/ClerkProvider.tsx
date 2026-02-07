import { ClerkProvider, useAuth as clerkUseAuth, useUser as clerkUseUser } from '@clerk/clerk-react';
import type { ReactNode } from 'react';

const CLERK_PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

export const isDevAuthMode = !CLERK_PUBLISHABLE_KEY;

if (isDevAuthMode) {
  console.warn(
    'Missing VITE_CLERK_PUBLISHABLE_KEY environment variable. ' +
    'Running in dev auth mode (all Clerk components are stubbed). ' +
    'See .env.example for setup instructions.'
  );
}

export function AuthProvider({ children }: { children: ReactNode }) {
  if (isDevAuthMode) {
    return <>{children}</>;
  }

  return (
    <ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY}>
      {children}
    </ClerkProvider>
  );
}

/**
 * Dev-safe Clerk component stubs.
 * When Clerk is not configured, SignedIn always renders its children
 * and SignedOut never renders (simulates an authenticated user).
 */
export function DevSignedIn({ children }: { children: ReactNode }) {
  return <>{children}</>;
}

export function DevSignedOut({ children }: { children: ReactNode }) {
  return null;
}

export function DevUserButton() {
  return (
    <div
      className="h-8 w-8 rounded-full bg-indigo-500 flex items-center justify-center text-white text-xs font-bold"
      title="Dev User (no Clerk)"
    >
      D
    </div>
  );
}

/**
 * Dev-safe hook stubs.
 * Components should import useAuth/useUser from this file instead of
 * directly from @clerk/clerk-react to avoid crashes in dev mode.
 */
const DEV_USER_ID = 'dev_user_00000000-0000-0000-0000-000000000001';

function useDevAuth() {
  return {
    isLoaded: true,
    isSignedIn: true,
    userId: DEV_USER_ID,
    getToken: async () => null,
    signOut: async () => {},
  };
}

function useDevUser() {
  return {
    isLoaded: true,
    isSignedIn: true,
    user: {
      id: DEV_USER_ID,
      fullName: 'Dev User',
      primaryEmailAddress: { emailAddress: 'dev@localhost' },
    },
  };
}

// eslint-disable-next-line react-hooks/rules-of-hooks
export const useAuth: typeof clerkUseAuth = isDevAuthMode ? useDevAuth as any : clerkUseAuth;
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useUser: typeof clerkUseUser = isDevAuthMode ? useDevUser as any : clerkUseUser;
