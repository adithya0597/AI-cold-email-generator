import React from 'react';
import { Link } from 'react-router-dom';
import { FiMail, FiLinkedin, FiTrendingUp, FiZap, FiTarget, FiClock } from 'react-icons/fi';

const LandingPage = () => {
  const features = [
    {
      icon: FiMail,
      title: 'Personalized Cold Emails',
      description: 'Generate highly targeted emails using AI-powered resume analysis and company research',
      link: '/email',
      color: 'text-blue-600'
    },
    {
      icon: FiLinkedin,
      title: 'LinkedIn Post Generator',
      description: 'Create engaging posts in various influencer styles with goal-oriented CTAs',
      link: '/linkedin',
      color: 'text-blue-700'
    },
    {
      icon: FiTarget,
      title: 'Value Proposition Synthesis',
      description: 'AI analyzes and creates compelling value propositions that resonate',
      link: '/email',
      color: 'text-green-600'
    },
    {
      icon: FiTrendingUp,
      title: 'Performance Tracking',
      description: 'Monitor email open rates and LinkedIn engagement metrics in real-time',
      link: '/dashboard',
      color: 'text-purple-600'
    },
    {
      icon: FiZap,
      title: 'Multi-LLM Support',
      description: 'Powered by OpenAI GPT-4 and Anthropic Claude with automatic fallback',
      link: '/settings',
      color: 'text-yellow-600'
    },
    {
      icon: FiClock,
      title: 'Save Hours Weekly',
      description: 'Reduce content creation time by 80% while improving quality and conversion',
      link: '/email',
      color: 'text-red-600'
    }
  ];

  const stats = [
    { value: '150%', label: 'Higher Open Rates' },
    { value: '3x', label: 'More Engagement' },
    { value: '80%', label: 'Time Saved' },
    { value: '24/7', label: 'AI Availability' }
  ];

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="text-center py-12">
        <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">
          AI Content Generation Suite
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
          Transform your outreach with AI-powered cold emails and LinkedIn posts that convert.
          Built with advanced context engineering for maximum personalization.
        </p>
        <div className="flex justify-center space-x-4">
          <Link to="/email" className="btn-primary">
            Generate Cold Email
          </Link>
          <Link to="/linkedin" className="btn-secondary">
            Create LinkedIn Post
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
        <h2 className="text-3xl font-bold text-center mb-8">Powerful Features</h2>
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
            <h3 className="font-semibold mb-2">Upload & Input</h3>
            <p className="text-gray-600 text-sm">
              Upload your resume and provide target company details or LinkedIn post requirements
            </p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-primary-100 rounded-full flex items-center justify-center">
              <span className="text-2xl font-bold text-primary-600">2</span>
            </div>
            <h3 className="font-semibold mb-2">AI Processing</h3>
            <p className="text-gray-600 text-sm">
              Our AI analyzes data, synthesizes value propositions, and generates personalized content
            </p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-primary-100 rounded-full flex items-center justify-center">
              <span className="text-2xl font-bold text-primary-600">3</span>
            </div>
            <h3 className="font-semibold mb-2">Track & Optimize</h3>
            <p className="text-gray-600 text-sm">
              Monitor performance metrics and continuously improve your outreach strategy
            </p>
          </div>
        </div>
      </section>

      {/* Technology Stack */}
      <section className="text-center">
        <h2 className="text-3xl font-bold mb-8">Powered By Advanced Technology</h2>
        <div className="flex flex-wrap justify-center gap-4">
          {['FastAPI', 'React', 'OpenAI GPT-4', 'Anthropic Claude', 'BeautifulSoup', 'TailwindCSS'].map((tech) => (
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
        <h2 className="text-3xl font-bold mb-4">Ready to Transform Your Outreach?</h2>
        <p className="text-xl mb-8 opacity-90">
          Start generating high-converting content in minutes
        </p>
        <Link to="/email" className="bg-white text-primary-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition-colors">
          Get Started Free
        </Link>
      </section>
    </div>
  );
};

export default LandingPage;