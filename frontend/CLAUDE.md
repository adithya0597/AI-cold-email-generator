# CLAUDE.md - Frontend Reference

> For project overview and tech stack, see root `/CLAUDE.md`

## Overview

React 18 + TypeScript single-page application. Built with Vite 6, styled with Tailwind CSS. State management via Zustand (local) and TanStack Query (server).

## Directory Structure

```
frontend/
├── src/
│   ├── main.jsx              # React entry point
│   ├── App.tsx               # Root component with routing
│   ├── App.test.tsx
│   │
│   ├── components/           # UI components by domain
│   │   ├── auth/
│   │   │   └── ProtectedRoute.tsx
│   │   ├── onboarding/
│   │   │   ├── ResumeUpload.tsx
│   │   │   ├── ProfileReview.tsx
│   │   │   └── BriefingPreview.tsx
│   │   ├── preferences/
│   │   │   ├── JobTypeStep.tsx
│   │   │   ├── LocationStep.tsx
│   │   │   ├── SalaryStep.tsx
│   │   │   └── ...
│   │   ├── briefing/
│   │   │   ├── BriefingCard.tsx
│   │   │   └── BriefingDetail.tsx
│   │   ├── matches/
│   │   │   ├── SwipeCard.tsx
│   │   │   ├── TopPickCard.tsx
│   │   │   ├── MatchDetail.tsx
│   │   │   └── __tests__/
│   │   ├── pipeline/
│   │   │   ├── KanbanCard.tsx
│   │   │   ├── PipelineListView.tsx
│   │   │   └── CardDetailPanel.tsx
│   │   ├── followups/
│   │   │   ├── FollowUpEditor.tsx
│   │   │   ├── FollowUpList.tsx
│   │   │   └── FollowUpHistory.tsx
│   │   ├── privacy/
│   │   │   ├── BlocklistManager.tsx
│   │   │   ├── PrivacyProof.tsx
│   │   │   └── PassiveModeSettings.tsx
│   │   ├── h1b/
│   │   │   ├── SponsorBadge.tsx
│   │   │   ├── SponsorScorecard.tsx
│   │   │   └── H1BFilter.tsx
│   │   ├── shared/
│   │   │   ├── StepIndicator.tsx
│   │   │   ├── EmptyState.tsx
│   │   │   └── WizardShell.tsx
│   │   │
│   │   └── [legacy JSX components]
│   │       ├── ColdEmailGenerator.jsx
│   │       ├── LinkedInPostGenerator.jsx
│   │       └── ...
│   │
│   ├── pages/                # Route-level components
│   │   ├── SignIn.tsx
│   │   ├── SignUp.tsx
│   │   ├── Onboarding.tsx
│   │   ├── Preferences.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Matches.tsx
│   │   ├── Pipeline.tsx
│   │   ├── Applications.tsx
│   │   ├── FollowUps.tsx
│   │   ├── BriefingHistory.tsx
│   │   ├── BriefingSettings.tsx
│   │   └── Privacy.tsx
│   │
│   ├── services/             # API clients
│   │   ├── api.ts            # Base Axios instance + auth interceptor
│   │   ├── matches.ts
│   │   ├── briefings.ts
│   │   ├── applications.ts
│   │   ├── followups.ts
│   │   ├── learnedPreferences.ts
│   │   ├── privacy.ts
│   │   └── h1b.ts
│   │
│   ├── providers/            # React context providers
│   │   ├── ClerkProvider.tsx
│   │   ├── QueryProvider.tsx
│   │   ├── AnalyticsProvider.tsx
│   │   └── OnboardingGuard.tsx
│   │
│   ├── hooks/                # Custom hooks
│   │   ├── useOnboarding.ts
│   │   └── useAnalytics.ts
│   │
│   ├── types/                # TypeScript type definitions
│   │   ├── onboarding.ts
│   │   ├── preferences.ts
│   │   └── matches.ts
│   │
│   ├── lib/                  # Third-party integrations
│   │   ├── sentry.ts
│   │   └── ws-reconnect.ts
│   │
│   ├── utils/                # Utility functions
│   │   └── sessionCache.js
│   │
│   ├── __tests__/            # Page-level tests
│   │
│   ├── test-setup.ts         # Vitest setup (mocks, matchers)
│   └── vite-env.d.ts
│
├── public/                   # Static assets
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

## Commands

```bash
npm run dev      # Start Vite dev server (http://localhost:3000)
npm test         # Run Vitest tests
npm run build    # Production build to dist/
npm run lint     # ESLint
npx prettier --check src/  # Check formatting
```

## Key Patterns

### Clerk Authentication
```tsx
// ProtectedRoute wraps authenticated pages
<Route element={<ProtectedRoute />}>
  <Route path="/dashboard" element={<Dashboard />} />
</Route>

// OnboardingGuard ensures onboarding is complete
<Route element={<OnboardingGuard />}>
  <Route path="/matches" element={<Matches />} />
</Route>

// useApiClient hook provides authenticated Axios instance
import { useApiClient } from '@/services/api';
const api = useApiClient();
const data = await api.get('/api/v1/matches');
```

### State Management

**Zustand** for client state with persistence:
```tsx
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const usePreferencesStore = create(
  persist(
    (set) => ({
      preferences: null,
      setPreferences: (prefs) => set({ preferences: prefs }),
    }),
    { name: 'preferences-storage' }
  )
);
```

**TanStack Query** for server state:
```tsx
import { useQuery } from '@tanstack/react-query';
import { matchesApi } from '@/services/matches';

// Query key factories for cache invalidation
export const matchKeys = {
  all: ['matches'] as const,
  list: () => [...matchKeys.all, 'list'] as const,
  detail: (id: string) => [...matchKeys.all, 'detail', id] as const,
};

function useMatches() {
  return useQuery({
    queryKey: matchKeys.list(),
    queryFn: matchesApi.getMatches,
  });
}
```

### Forms with Validation
```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const schema = z.object({
  email: z.string().email(),
  salary: z.number().min(0),
});

function PreferencesForm() {
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
  });
  // ...
}
```

### Nested Route Guards
Routes are protected by composition:
```tsx
<Routes>
  {/* Public routes */}
  <Route path="/sign-in" element={<SignIn />} />

  {/* Auth required */}
  <Route element={<ProtectedRoute />}>
    <Route path="/onboarding" element={<Onboarding />} />

    {/* Auth + Onboarding required */}
    <Route element={<OnboardingGuard />}>
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/matches" element={<Matches />} />
    </Route>
  </Route>
</Routes>
```

### Error Handling
```tsx
// Sentry ErrorBoundary at root
import { ErrorBoundary } from '@sentry/react';
<ErrorBoundary fallback={<ErrorFallback />}>
  <App />
</ErrorBoundary>

// Toast notifications for user feedback
import { toast } from 'react-toastify';
toast.success('Application submitted!');
toast.error('Failed to load matches');
```

### Analytics (PostHog)
```tsx
import { useAnalytics } from '@/hooks/useAnalytics';

function SwipeCard({ match }) {
  const { track } = useAnalytics();

  const handleSwipe = (direction) => {
    track('match_swiped', { matchId: match.id, direction });
  };
}
```

## Adding a New Feature

1. **Define types** in `src/types/newFeature.ts`
2. **Create API service** in `src/services/newFeature.ts`
3. **Build components** in `src/components/newFeature/`
4. **Create page** in `src/pages/NewFeature.tsx`
5. **Add route** in `src/App.tsx`
6. **Write tests** in component `__tests__/` or `src/__tests__/`

## Testing

### Setup
- Vitest with jsdom environment
- `test-setup.ts` configures mocks and matchers
- Tests colocated in `__tests__/` directories

### Patterns
```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { SwipeCard } from '../SwipeCard';

// Mock API
vi.mock('@/services/matches', () => ({
  matchesApi: {
    swipe: vi.fn(),
  },
}));

// Render with providers
function renderWithProviders(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      {ui}
    </QueryClientProvider>
  );
}

test('swipe right submits feedback', async () => {
  renderWithProviders(<SwipeCard match={mockMatch} />);
  fireEvent.click(screen.getByRole('button', { name: /interested/i }));
  expect(matchesApi.swipe).toHaveBeenCalledWith(mockMatch.id, 'right');
});
```

## Environment Variables

All frontend env vars require `VITE_` prefix:

| Variable | Purpose |
|----------|---------|
| `VITE_API_URL` | Backend API base URL |
| `VITE_CLERK_PUBLISHABLE_KEY` | Clerk auth |
| `VITE_POSTHOG_KEY` | PostHog analytics |
| `VITE_POSTHOG_HOST` | PostHog host |
| `VITE_SENTRY_DSN` | Sentry error tracking |

Access via `import.meta.env.VITE_API_URL`.
