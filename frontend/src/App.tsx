import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import * as Sentry from '@sentry/react';
import { SignedIn as ClerkSignedIn, SignedOut as ClerkSignedOut, UserButton as ClerkUserButton } from '@clerk/clerk-react';
import { isDevAuthMode, DevSignedIn, DevSignedOut, DevUserButton } from './providers/ClerkProvider';

const SignedIn = isDevAuthMode ? DevSignedIn : ClerkSignedIn;
const SignedOut = isDevAuthMode ? DevSignedOut : ClerkSignedOut;
const UserButton = isDevAuthMode ? DevUserButton : ClerkUserButton;
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { FiActivity, FiSettings, FiHome, FiLogIn, FiTarget, FiTrello, FiClock, FiShield } from 'react-icons/fi';

import { initSentry } from './lib/sentry';

import EmergencyBrake from './components/EmergencyBrake';
import ProtectedRoute from './components/auth/ProtectedRoute';
import ColdEmailGenerator from './components/ColdEmailGenerator';
import LinkedInPostGenerator from './components/LinkedInPostGenerator';
import AuthorStylesManager from './components/AuthorStylesManager';
import LegacyDashboard from './components/Dashboard';
import Settings from './components/Settings';
import LandingPage from './components/LandingPage';
import SignIn from './pages/SignIn';
import SignUp from './pages/SignUp';
import Dashboard from './pages/Dashboard';
import Onboarding from './pages/Onboarding';
import Preferences from './pages/Preferences';
import BriefingHistory from './pages/BriefingHistory';
import BriefingDetail from './components/briefing/BriefingDetail';
import BriefingSettingsPage from './pages/BriefingSettings';
import Matches from './pages/Matches';
import Applications from './pages/Applications';
import Pipeline from './pages/Pipeline';
import FollowUps from './pages/FollowUps';
import Privacy from './pages/Privacy';
import H1B from './pages/H1B';
import OnboardingGuard from './providers/OnboardingGuard';
import { utilityService } from './services/api';
import { useStealthStatus } from './services/privacy';

// Initialise Sentry before the React tree renders.
initSentry();

/** Renders the stealth badge only when signed in (hook is called conditionally inside SignedIn). */
function StealthBadge() {
  const { data: stealthData } = useStealthStatus();
  if (!stealthData?.stealth_enabled) return null;
  return (
    <span
      data-testid="stealth-badge"
      className="inline-flex items-center rounded-full bg-gray-900 px-2 py-0.5 text-xs font-medium text-green-400"
    >
      Stealth
    </span>
  );
}

function App() {
  const [healthStatus, setHealthStatus] = useState<{ status: string } | null>(null);

  useEffect(() => {
    checkApiHealth();
  }, []);

  const checkApiHealth = async () => {
    try {
      const health = await utilityService.checkHealth();
      setHealthStatus(health);
      if (health.status !== 'healthy') {
        toast.warning('Some services may be degraded');
      }
    } catch (_error) {
      toast.error('Unable to connect to backend API');
      setHealthStatus({ status: 'error' });
    }
  };

  return (
    <Sentry.ErrorBoundary fallback={<p>Something went wrong</p>}>
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        {/* Navigation */}
        <nav className="bg-white shadow-lg sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex">
                <div className="flex-shrink-0 flex items-center">
                  <h1 className="text-2xl font-bold bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">
                    JobPilot
                  </h1>
                </div>
                <div className="hidden sm:ml-8 sm:flex sm:space-x-8">
                  <NavLink
                    to="/"
                    end
                    className={({ isActive }) =>
                      `inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                        isActive
                          ? 'border-primary-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      }`
                    }
                  >
                    <FiHome className="mr-2" />
                    Home
                  </NavLink>
                  <NavLink
                    to="/dashboard"
                    className={({ isActive }) =>
                      `inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                        isActive
                          ? 'border-primary-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      }`
                    }
                  >
                    <FiActivity className="mr-2" />
                    Dashboard
                  </NavLink>
                  <NavLink
                    to="/matches"
                    className={({ isActive }) =>
                      `inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                        isActive
                          ? 'border-primary-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      }`
                    }
                  >
                    <FiTarget className="mr-2" />
                    Matches
                  </NavLink>
                  <NavLink
                    to="/pipeline"
                    className={({ isActive }) =>
                      `inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                        isActive
                          ? 'border-primary-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      }`
                    }
                  >
                    <FiTrello className="mr-2" />
                    Pipeline
                  </NavLink>
                  <NavLink
                    to="/followups"
                    className={({ isActive }) =>
                      `inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                        isActive
                          ? 'border-primary-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      }`
                    }
                  >
                    <FiClock className="mr-2" />
                    Follow-ups
                  </NavLink>
                  <NavLink
                    to="/privacy"
                    className={({ isActive }) =>
                      `inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                        isActive
                          ? 'border-primary-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      }`
                    }
                  >
                    <FiShield className="mr-2" />
                    Privacy
                  </NavLink>
                  <NavLink
                    to="/settings"
                    className={({ isActive }) =>
                      `inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                        isActive
                          ? 'border-primary-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      }`
                    }
                  >
                    <FiSettings className="mr-2" />
                    Settings
                  </NavLink>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <div
                    className={`h-2 w-2 rounded-full ${
                      healthStatus?.status === 'healthy'
                        ? 'bg-green-500'
                        : healthStatus?.status === 'degraded'
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                    }`}
                  />
                  <span className="text-xs text-gray-500">
                    {healthStatus?.status || 'Checking...'}
                  </span>
                </div>
                <SignedIn>
                  <StealthBadge />
                  <EmergencyBrake />
                  <UserButton afterSignOutUrl="/" />
                </SignedIn>
                <SignedOut>
                  <NavLink
                    to="/sign-in"
                    className="inline-flex items-center px-3 py-1.5 border border-primary-500 text-sm font-medium rounded-md text-primary-600 hover:bg-primary-50"
                  >
                    <FiLogIn className="mr-1.5" />
                    Sign In
                  </NavLink>
                </SignedOut>
              </div>
            </div>
          </div>

          {/* Mobile menu */}
          <div className="sm:hidden">
            <div className="pt-2 pb-3 space-y-1">
              <NavLink
                to="/"
                end
                className={({ isActive }) =>
                  `block pl-3 pr-4 py-2 border-l-4 text-base font-medium ${
                    isActive
                      ? 'bg-indigo-50 border-primary-500 text-primary-700'
                      : 'border-transparent text-gray-500 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-700'
                  }`
                }
              >
                <FiHome className="inline mr-2" />
                Home
              </NavLink>
              <NavLink
                to="/dashboard"
                className={({ isActive }) =>
                  `block pl-3 pr-4 py-2 border-l-4 text-base font-medium ${
                    isActive
                      ? 'bg-indigo-50 border-primary-500 text-primary-700'
                      : 'border-transparent text-gray-500 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-700'
                  }`
                }
              >
                <FiActivity className="inline mr-2" />
                Dashboard
              </NavLink>
              <NavLink
                to="/matches"
                className={({ isActive }) =>
                  `block pl-3 pr-4 py-2 border-l-4 text-base font-medium ${
                    isActive
                      ? 'bg-indigo-50 border-primary-500 text-primary-700'
                      : 'border-transparent text-gray-500 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-700'
                  }`
                }
              >
                <FiTarget className="inline mr-2" />
                Matches
              </NavLink>
              <NavLink
                to="/pipeline"
                className={({ isActive }) =>
                  `block pl-3 pr-4 py-2 border-l-4 text-base font-medium ${
                    isActive
                      ? 'bg-indigo-50 border-primary-500 text-primary-700'
                      : 'border-transparent text-gray-500 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-700'
                  }`
                }
              >
                <FiTrello className="inline mr-2" />
                Pipeline
              </NavLink>
              <NavLink
                to="/followups"
                className={({ isActive }) =>
                  `block pl-3 pr-4 py-2 border-l-4 text-base font-medium ${
                    isActive
                      ? 'bg-indigo-50 border-primary-500 text-primary-700'
                      : 'border-transparent text-gray-500 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-700'
                  }`
                }
              >
                <FiClock className="inline mr-2" />
                Follow-ups
              </NavLink>
              <NavLink
                to="/privacy"
                className={({ isActive }) =>
                  `block pl-3 pr-4 py-2 border-l-4 text-base font-medium ${
                    isActive
                      ? 'bg-indigo-50 border-primary-500 text-primary-700'
                      : 'border-transparent text-gray-500 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-700'
                  }`
                }
              >
                <FiShield className="inline mr-2" />
                Privacy
              </NavLink>
              <NavLink
                to="/settings"
                className={({ isActive }) =>
                  `block pl-3 pr-4 py-2 border-l-4 text-base font-medium ${
                    isActive
                      ? 'bg-indigo-50 border-primary-500 text-primary-700'
                      : 'border-transparent text-gray-500 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-700'
                  }`
                }
              >
                <FiSettings className="inline mr-2" />
                Settings
              </NavLink>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/sign-in/*" element={<SignIn />} />
            <Route path="/sign-up/*" element={<SignUp />} />

            {/* Legacy public routes (existing features) */}
            <Route path="/email" element={<ColdEmailGenerator />} />
            <Route path="/linkedin" element={<LinkedInPostGenerator />} />
            <Route path="/author-styles" element={<AuthorStylesManager />} />
            <Route path="/settings" element={<Settings />} />

            {/* Protected routes -- ProtectedRoute syncs user record and redirects if unauthenticated */}
            <Route element={<ProtectedRoute />}>
              <Route path="/onboarding" element={<Onboarding />} />
              <Route path="/preferences" element={<Preferences />} />
              <Route
                path="/dashboard"
                element={
                  <OnboardingGuard>
                    <Dashboard />
                  </OnboardingGuard>
                }
              />
              <Route
                path="/matches"
                element={
                  <OnboardingGuard>
                    <Matches />
                  </OnboardingGuard>
                }
              />
              <Route
                path="/applications"
                element={
                  <OnboardingGuard>
                    <Applications />
                  </OnboardingGuard>
                }
              />
              <Route
                path="/pipeline"
                element={
                  <OnboardingGuard>
                    <Pipeline />
                  </OnboardingGuard>
                }
              />
              <Route
                path="/followups"
                element={
                  <OnboardingGuard>
                    <FollowUps />
                  </OnboardingGuard>
                }
              />
              <Route
                path="/privacy"
                element={
                  <OnboardingGuard>
                    <Privacy />
                  </OnboardingGuard>
                }
              />
              <Route
                path="/h1b"
                element={
                  <OnboardingGuard>
                    <H1B />
                  </OnboardingGuard>
                }
              />
              <Route path="/briefings" element={<BriefingHistory />} />
              <Route path="/briefings/settings" element={<BriefingSettingsPage />} />
              <Route path="/briefings/:briefingId" element={<BriefingDetail />} />
            </Route>
          </Routes>
        </main>

        {/* Toast Notifications */}
        <ToastContainer
          position="bottom-right"
          autoClose={5000}
          hideProgressBar={false}
          newestOnTop={false}
          closeOnClick
          rtl={false}
          pauseOnFocusLoss
          draggable
          pauseOnHover
          theme="light"
        />
      </div>
    </Router>
    </Sentry.ErrorBoundary>
  );
}

export default App;
