import { useUser, UserButton } from '@clerk/clerk-react';
import AgentActivityFeed from '../components/AgentActivityFeed';
import BriefingCard, {
  BriefingEmptyState,
} from '../components/briefing/BriefingCard';
import { useLatestBriefing } from '../services/briefings';

export default function Dashboard() {
  const { user, isLoaded } = useUser();
  const userId = user?.id;

  const {
    data: latestBriefing,
    isLoading: briefingLoading,
  } = useLatestBriefing(userId);

  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  const userName =
    user?.firstName ||
    user?.emailAddresses?.[0]?.emailAddress?.split('@')[0] ||
    undefined;

  return (
    <div className="max-w-4xl mx-auto">
      {/* Latest Briefing (hero) */}
      {briefingLoading ? (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6 animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/3 mb-3" />
          <div className="h-4 bg-gray-200 rounded w-2/3 mb-2" />
          <div className="h-4 bg-gray-200 rounded w-1/2" />
        </div>
      ) : latestBriefing ? (
        <BriefingCard
          briefing={latestBriefing}
          userName={userName}
          userId={userId!}
        />
      ) : (
        <BriefingEmptyState userName={userName} />
      )}

      {/* Stats overview */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-gray-600 mt-1">
              Welcome back, {user?.firstName || user?.emailAddresses?.[0]?.emailAddress || 'User'}
            </p>
          </div>
          <UserButton afterSignOutUrl="/" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-blue-50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-blue-800">Applications</h3>
            <p className="text-2xl font-bold text-blue-900 mt-1">0</p>
            <p className="text-xs text-blue-600 mt-1">Coming soon</p>
          </div>
          <div className="bg-green-50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-green-800">Interviews</h3>
            <p className="text-2xl font-bold text-green-900 mt-1">0</p>
            <p className="text-xs text-green-600 mt-1">Coming soon</p>
          </div>
          <div className="bg-purple-50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-purple-800">Agent Tasks</h3>
            <p className="text-2xl font-bold text-purple-900 mt-1">0</p>
            <p className="text-xs text-purple-600 mt-1">Coming soon</p>
          </div>
        </div>
      </div>

      {/* Agent Activity Feed */}
      <div className="mb-6">
        <AgentActivityFeed />
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Account Details</h2>
        <dl className="grid grid-cols-1 gap-3 text-sm">
          <div className="flex justify-between">
            <dt className="text-gray-500">Email</dt>
            <dd className="text-gray-900">{user?.emailAddresses?.[0]?.emailAddress}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">User ID</dt>
            <dd className="text-gray-900 font-mono text-xs">{user?.id}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Joined</dt>
            <dd className="text-gray-900">
              {user?.createdAt ? new Date(user.createdAt).toLocaleDateString() : 'N/A'}
            </dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
