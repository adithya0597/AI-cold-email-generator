import React from 'react';
import { Link } from 'react-router-dom';
import { FiActivity, FiTarget, FiTrello, FiFileText, FiGlobe, FiShield } from 'react-icons/fi';

const LandingPage = () => {
  const features = [
    {
      icon: FiActivity,
      title: 'Daily Briefings',
      description: 'Wake up to a personalized briefing with curated jobs matched to your skills and preferences',
      link: '/dashboard',
      color: 'text-blue-600'
    },
    {
      icon: FiTarget,
      title: 'Smart Job Matching',
      description: 'Swipe through AI-scored matches with transparent reasoning on why each job fits you',
      link: '/matches',
      color: 'text-green-600'
    },
    {
      icon: FiTrello,
      title: 'Pipeline Tracking',
      description: 'Kanban-style board to manage every application from discovery through offer',
      link: '/pipeline',
      color: 'text-purple-600'
    },
    {
      icon: FiFileText,
      title: 'Resume Tailoring',
      description: 'Automatically tailor your resume for each role, highlighting the most relevant experience',
      link: '/dashboard',
      color: 'text-indigo-600'
    },
    {
      icon: FiGlobe,
      title: 'H1B Sponsor Intelligence',
      description: 'Check company sponsorship history, approval rates, and wage data before you apply',
      link: '/h1b',
      color: 'text-teal-600'
    },
    {
      icon: FiShield,
      title: 'Privacy Controls',
      description: 'Block companies, go stealth, and control exactly what data your AI agent can access',
      link: '/privacy',
      color: 'text-red-600'
    }
  ];

  const stats = [
    { value: '100+', label: 'Jobs Scanned Daily' },
    { value: 'L0-L3', label: 'Autonomy Tiers' },
    { value: '7-Step', label: 'Preference Engine' },
    { value: '24/7', label: 'Agent Availability' }
  ];

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="text-center py-12">
        <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">
          Your AI Career Agent
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
          Automated job discovery, intelligent matching, and application tracking —
          powered by a multi-agent system that works while you sleep.
        </p>
        <div className="flex justify-center space-x-4">
          <Link to="/sign-up" className="btn-primary">
            Get Started
          </Link>
          <Link to="/dashboard" className="btn-secondary">
            Explore Dashboard
          </Link>
        </div>
      </section>

      {/* Stats Section */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <div key={index} className="text-center">
            <div className="text-3xl font-bold text-primary-600">{stat.value}</div>
            <div className="text-gray-600">{stat.label}</div>
          </div>
        ))}
      </section>

      {/* Features Grid */}
      <section>
        <h2 className="text-3xl font-bold text-center mb-8">Everything You Need to Land Your Next Role</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <Link
                key={index}
                to={feature.link}
                className="card hover:scale-105 transition-transform duration-200"
              >
                <div className="flex items-start">
                  <div className={`p-3 rounded-lg bg-gray-50 ${feature.color}`}>
                    <Icon className="text-2xl" />
                  </div>
                  <div className="ml-4">
                    <h3 className="font-semibold text-lg mb-2">{feature.title}</h3>
                    <p className="text-gray-600 text-sm">{feature.description}</p>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* How It Works */}
      <section className="bg-white rounded-xl shadow-lg p-8">
        <h2 className="text-3xl font-bold text-center mb-8">How It Works</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-primary-100 rounded-full flex items-center justify-center">
              <span className="text-2xl font-bold text-primary-600">1</span>
            </div>
            <h3 className="font-semibold mb-2">Upload Your Resume</h3>
            <p className="text-gray-600 text-sm">
              Our AI parses your experience, skills, and goals to build your career profile
            </p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-primary-100 rounded-full flex items-center justify-center">
              <span className="text-2xl font-bold text-primary-600">2</span>
            </div>
            <h3 className="font-semibold mb-2">Get Daily Matches</h3>
            <p className="text-gray-600 text-sm">
              Every morning, receive a curated briefing with jobs scored and ranked for your profile
            </p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-primary-100 rounded-full flex items-center justify-center">
              <span className="text-2xl font-bold text-primary-600">3</span>
            </div>
            <h3 className="font-semibold mb-2">Track & Apply</h3>
            <p className="text-gray-600 text-sm">
              Manage your pipeline, get tailored resumes, and let AI handle follow-ups
            </p>
          </div>
        </div>
      </section>

      {/* Technology Stack */}
      <section className="text-center">
        <h2 className="text-3xl font-bold mb-8">Powered By Advanced Technology</h2>
        <div className="flex flex-wrap justify-center gap-4">
          {['FastAPI', 'React', 'TypeScript', 'OpenAI GPT-4', 'Anthropic Claude', 'Supabase', 'TailwindCSS'].map((tech) => (
            <span
              key={tech}
              className="px-4 py-2 bg-gray-100 rounded-full text-gray-700 font-medium"
            >
              {tech}
            </span>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="text-center bg-gradient-to-r from-primary-600 to-secondary-600 rounded-xl p-12 text-white">
        <h2 className="text-3xl font-bold mb-4">Ready to Automate Your Job Search?</h2>
        <p className="text-xl mb-8 opacity-90">
          Join JobPilot and let AI agents find, match, and track opportunities for you
        </p>
        <Link to="/sign-up" className="bg-white text-primary-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition-colors">
          Get Started Free
        </Link>
      </section>
    </div>
  );
};

export default LandingPage;
