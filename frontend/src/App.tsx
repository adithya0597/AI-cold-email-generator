import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import { SignedIn, SignedOut, RedirectToSignIn, UserButton } from '@clerk/clerk-react';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { FiMail, FiLinkedin, FiActivity, FiSettings, FiHome, FiUsers, FiLogIn } from 'react-icons/fi';

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
import { utilityService } from './services/api';

/**
 * ProtectedRoute -- requires Clerk authentication.
 * Renders children if signed in, otherwise redirects to sign-in.
 */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  return (
    <>
      <SignedIn>{children}</SignedIn>
      <SignedOut>
        <RedirectToSignIn />
      </SignedOut>
    </>
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
                    to="/email"
                    className={({ isActive }) =>
                      `inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                        isActive
                          ? 'border-primary-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      }`
                    }
                  >
                    <FiMail className="mr-2" />
                    Cold Email
                  </NavLink>
                  <NavLink
                    to="/linkedin"
                    className={({ isActive }) =>
                      `inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                        isActive
                          ? 'border-primary-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      }`
                    }
                  >
                    <FiLinkedin className="mr-2" />
                    LinkedIn Post
                  </NavLink>
                  <NavLink
                    to="/author-styles"
                    className={({ isActive }) =>
                      `inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                        isActive
                          ? 'border-primary-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      }`
                    }
                  >
                    <FiUsers className="mr-2" />
                    Author Styles
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
                to="/email"
                className={({ isActive }) =>
                  `block pl-3 pr-4 py-2 border-l-4 text-base font-medium ${
                    isActive
                      ? 'bg-indigo-50 border-primary-500 text-primary-700'
                      : 'border-transparent text-gray-500 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-700'
                  }`
                }
              >
                <FiMail className="inline mr-2" />
                Cold Email
              </NavLink>
              <NavLink
                to="/linkedin"
                className={({ isActive }) =>
                  `block pl-3 pr-4 py-2 border-l-4 text-base font-medium ${
                    isActive
                      ? 'bg-indigo-50 border-primary-500 text-primary-700'
                      : 'border-transparent text-gray-500 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-700'
                  }`
                }
              >
                <FiLinkedin className="inline mr-2" />
                LinkedIn Post
              </NavLink>
              <NavLink
                to="/author-styles"
                className={({ isActive }) =>
                  `block pl-3 pr-4 py-2 border-l-4 text-base font-medium ${
                    isActive
                      ? 'bg-indigo-50 border-primary-500 text-primary-700'
                      : 'border-transparent text-gray-500 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-700'
                  }`
                }
              >
                <FiUsers className="inline mr-2" />
                Author Styles
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

            {/* Protected routes */}
            <Route
              path="/onboarding"
              element={
                <ProtectedRoute>
                  <Onboarding />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
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
  );
}

export default App;
