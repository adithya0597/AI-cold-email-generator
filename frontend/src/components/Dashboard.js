import React, { useState } from 'react';
import { FiMail, FiTrendingUp, FiEye, FiThumbsUp, FiMessageCircle } from 'react-icons/fi';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const Dashboard = () => {
  const [emailStats] = useState({
    totalSent: 45,
    totalOpened: 28,
    openRate: 62.2,
    avgResponseTime: '2.3 hours'
  });

  const [linkedInStats] = useState({
    totalPosts: 12,
    totalViews: 3420,
    totalLikes: 234,
    totalComments: 45,
    avgEngagement: 8.2
  });

  // Mock data for charts
  const emailPerformance = [
    { date: 'Mon', sent: 8, opened: 5 },
    { date: 'Tue', sent: 12, opened: 8 },
    { date: 'Wed', sent: 6, opened: 4 },
    { date: 'Thu', sent: 10, opened: 7 },
    { date: 'Fri', sent: 9, opened: 4 },
  ];

  const linkedInEngagement = [
    { metric: 'Views', value: 3420, color: '#3B82F6' },
    { metric: 'Likes', value: 234, color: '#10B981' },
    { metric: 'Comments', value: 45, color: '#F59E0B' },
    { metric: 'Shares', value: 18, color: '#EF4444' },
  ];

  const recentEmails = [
    { id: 1, recipient: 'john.smith@techcorp.com', subject: 'Partnership Opportunity', status: 'opened', time: '2 hours ago' },
    { id: 2, recipient: 'sarah.jones@startup.io', subject: 'Quick Question About Your Product', status: 'sent', time: '4 hours ago' },
    { id: 3, recipient: 'mike.wilson@enterprise.com', subject: 'Following Up on Our Discussion', status: 'opened', time: '1 day ago' },
  ];

  const recentPosts = [
    { id: 1, title: 'The Future of AI in Business', views: 542, likes: 43, engagement: 7.9, time: '2 days ago' },
    { id: 2, title: '5 Lessons from Building a Startup', views: 1203, likes: 89, engagement: 7.4, time: '4 days ago' },
    { id: 3, title: 'Why Remote Work is Here to Stay', views: 892, likes: 67, engagement: 7.5, time: '1 week ago' },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Performance Dashboard</h1>
        <p className="text-gray-600">Track your email and LinkedIn post performance</p>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Email Open Rate</p>
              <p className="text-2xl font-bold text-primary-600">{emailStats.openRate}%</p>
            </div>
            <FiMail className="text-3xl text-primary-200" />
          </div>
          <div className="mt-2 text-xs text-gray-500">
            {emailStats.totalOpened} of {emailStats.totalSent} opened
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">LinkedIn Views</p>
              <p className="text-2xl font-bold text-blue-600">{linkedInStats.totalViews.toLocaleString()}</p>
            </div>
            <FiEye className="text-3xl text-blue-200" />
          </div>
          <div className="mt-2 text-xs text-gray-500">
            Across {linkedInStats.totalPosts} posts
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Engagement Rate</p>
              <p className="text-2xl font-bold text-green-600">{linkedInStats.avgEngagement}%</p>
            </div>
            <FiTrendingUp className="text-3xl text-green-200" />
          </div>
          <div className="mt-2 text-xs text-gray-500">
            Average across all posts
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Response Time</p>
              <p className="text-2xl font-bold text-purple-600">{emailStats.avgResponseTime}</p>
            </div>
            <FiMessageCircle className="text-3xl text-purple-200" />
          </div>
          <div className="mt-2 text-xs text-gray-500">
            Average email response
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Email Performance Chart */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Email Performance (This Week)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={emailPerformance}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="sent" stroke="#3B82F6" strokeWidth={2} name="Sent" />
              <Line type="monotone" dataKey="opened" stroke="#10B981" strokeWidth={2} name="Opened" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* LinkedIn Engagement Chart */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">LinkedIn Engagement Breakdown</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={linkedInEngagement}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ metric, value }) => `${metric}: ${value}`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {linkedInEngagement.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Emails */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Recent Emails</h3>
          <div className="space-y-3">
            {recentEmails.map((email) => (
              <div key={email.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex-1">
                  <p className="font-medium text-sm">{email.subject}</p>
                  <p className="text-xs text-gray-500">{email.recipient}</p>
                </div>
                <div className="text-right">
                  <span className={`inline-block px-2 py-1 rounded-full text-xs ${
                    email.status === 'opened' 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-blue-100 text-blue-800'
                  }`}>
                    {email.status}
                  </span>
                  <p className="text-xs text-gray-500 mt-1">{email.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Posts */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Recent LinkedIn Posts</h3>
          <div className="space-y-3">
            {recentPosts.map((post) => (
              <div key={post.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex-1">
                  <p className="font-medium text-sm">{post.title}</p>
                  <div className="flex items-center space-x-3 mt-1">
                    <span className="text-xs text-gray-500 flex items-center">
                      <FiEye className="mr-1" /> {post.views}
                    </span>
                    <span className="text-xs text-gray-500 flex items-center">
                      <FiThumbsUp className="mr-1" /> {post.likes}
                    </span>
                    <span className="text-xs text-gray-500">
                      {post.engagement}% engagement
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-500">{post.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Tips Section */}
      <div className="bg-gradient-to-r from-primary-50 to-secondary-50 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-3">Performance Tips</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex items-start">
            <div className="w-2 h-2 rounded-full bg-primary-600 mt-1.5 mr-3"></div>
            <p className="text-sm text-gray-700">
              Your email open rate is above average! Consider A/B testing subject lines to push it even higher.
            </p>
          </div>
          <div className="flex items-start">
            <div className="w-2 h-2 rounded-full bg-secondary-600 mt-1.5 mr-3"></div>
            <p className="text-sm text-gray-700">
              LinkedIn posts with questions get 50% more engagement. Try ending with a thought-provoking question.
            </p>
          </div>
          <div className="flex items-start">
            <div className="w-2 h-2 rounded-full bg-primary-600 mt-1.5 mr-3"></div>
            <p className="text-sm text-gray-700">
              Best time to send emails: Tuesday-Thursday, 10-11 AM in recipient's timezone.
            </p>
          </div>
          <div className="flex items-start">
            <div className="w-2 h-2 rounded-full bg-secondary-600 mt-1.5 mr-3"></div>
            <p className="text-sm text-gray-700">
              Posts with 3-5 hashtags perform 20% better than those with more or fewer.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;