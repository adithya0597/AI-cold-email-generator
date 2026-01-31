import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from './App';

// Mock Clerk to avoid needing a real publishable key in tests
vi.mock('@clerk/clerk-react', () => ({
  ClerkProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  SignedIn: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  SignedOut: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  RedirectToSignIn: () => null,
  UserButton: () => null,
  useAuth: () => ({ getToken: vi.fn(), isSignedIn: false }),
  useUser: () => ({ user: null, isLoaded: true }),
}));

// Mock the API service to prevent real HTTP calls
vi.mock('./services/api', () => ({
  utilityService: {
    checkHealth: vi.fn().mockResolvedValue({ status: 'healthy' }),
  },
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('App', () => {
  it('renders the JobPilot heading', () => {
    render(<App />);
    expect(screen.getByText('JobPilot')).toBeInTheDocument();
  });

  it('renders navigation links', () => {
    render(<App />);
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Cold Email')).toBeInTheDocument();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });
});
