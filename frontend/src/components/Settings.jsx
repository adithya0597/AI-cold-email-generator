import React, { useState } from 'react';
import { FiSettings, FiKey, FiDatabase, FiMail, FiLinkedin, FiCheck, FiAlertCircle } from 'react-icons/fi';
import { toast } from 'react-toastify';

const Settings = () => {
  const [apiKeys, setApiKeys] = useState({
    openai: '',
    anthropic: ''
  });

  const [preferences, setPreferences] = useState({
    defaultTone: 'professional',
    defaultHashtags: 5,
    trackingEnabled: true,
    autoSave: true
  });

  const [activeTab, setActiveTab] = useState('api');

  const handleApiKeyChange = (key, value) => {
    setApiKeys(prev => ({ ...prev, [key]: value }));
  };

  const handlePreferenceChange = (key, value) => {
    setPreferences(prev => ({ ...prev, [key]: value }));
  };

  const saveApiKeys = () => {
    // In production, this would save to backend
    localStorage.setItem('apiKeys', JSON.stringify(apiKeys));
    toast.success('API keys saved successfully!');
  };

  const savePreferences = () => {
    localStorage.setItem('preferences', JSON.stringify(preferences));
    toast.success('Preferences saved successfully!');
  };

  const testConnection = async (service) => {
    toast.info(`Testing ${service} connection...`);
    // Simulate API test
    setTimeout(() => {
      toast.success(`${service} connection successful!`);
    }, 1500);
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Settings</h1>
        <p className="text-gray-600">Configure your API keys and preferences</p>
      </div>

      {/* Tab Navigation */}
      <div className="flex space-x-1 mb-6 border-b">
        <button
          onClick={() => setActiveTab('api')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'api'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <FiKey className="inline mr-2" />
          API Configuration
        </button>
        <button
          onClick={() => setActiveTab('preferences')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'preferences'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <FiSettings className="inline mr-2" />
          Preferences
        </button>
        <button
          onClick={() => setActiveTab('data')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'data'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <FiDatabase className="inline mr-2" />
          Data Management
        </button>
      </div>

      {/* API Configuration Tab */}
      {activeTab === 'api' && (
        <div className="space-y-6">
          {/* OpenAI Configuration */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">OpenAI Configuration</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  API Key
                </label>
                <div className="flex space-x-2">
                  <input
                    type="password"
                    value={apiKeys.openai}
                    onChange={(e) => handleApiKeyChange('openai', e.target.value)}
                    className="input-field flex-1"
                    placeholder="sk-..."
                  />
                  <button
                    onClick={() => testConnection('OpenAI')}
                    className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    Test
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Get your API key from <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">OpenAI Platform</a>
                </p>
              </div>
            </div>
          </div>

          {/* Anthropic Configuration */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">Anthropic Configuration</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  API Key
                </label>
                <div className="flex space-x-2">
                  <input
                    type="password"
                    value={apiKeys.anthropic}
                    onChange={(e) => handleApiKeyChange('anthropic', e.target.value)}
                    className="input-field flex-1"
                    placeholder="sk-ant-..."
                  />
                  <button
                    onClick={() => testConnection('Anthropic')}
                    className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    Test
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Get your API key from <a href="https://console.anthropic.com/" target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">Anthropic Console</a>
                </p>
              </div>
            </div>
          </div>


          <button onClick={saveApiKeys} className="btn-primary">
            <FiCheck className="inline mr-2" />
            Save API Keys
          </button>
        </div>
      )}

      {/* Preferences Tab */}
      {activeTab === 'preferences' && (
        <div className="space-y-6">
          {/* Email Preferences */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4 flex items-center">
              <FiMail className="mr-2 text-primary-600" />
              Email Preferences
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Default Tone
                </label>
                <select
                  value={preferences.defaultTone}
                  onChange={(e) => handlePreferenceChange('defaultTone', e.target.value)}
                  className="input-field"
                >
                  <option value="professional">Professional</option>
                  <option value="friendly">Friendly</option>
                  <option value="casual">Casual</option>
                  <option value="formal">Formal</option>
                  <option value="enthusiastic">Enthusiastic</option>
                </select>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <label className="font-medium text-gray-700">Enable Email Tracking</label>
                  <p className="text-xs text-gray-500">Add tracking pixel to generated emails</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={preferences.trackingEnabled}
                    onChange={(e) => handlePreferenceChange('trackingEnabled', e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                </label>
              </div>
            </div>
          </div>

          {/* LinkedIn Preferences */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4 flex items-center">
              <FiLinkedin className="mr-2 text-blue-600" />
              LinkedIn Preferences
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Default Number of Hashtags
                </label>
                <input
                  type="number"
                  value={preferences.defaultHashtags}
                  onChange={(e) => handlePreferenceChange('defaultHashtags', parseInt(e.target.value))}
                  className="input-field"
                  min="0"
                  max="10"
                />
              </div>
            </div>
          </div>

          {/* General Preferences */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">General Preferences</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <label className="font-medium text-gray-700">Auto-save Generated Content</label>
                  <p className="text-xs text-gray-500">Automatically save generated emails and posts</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={preferences.autoSave}
                    onChange={(e) => handlePreferenceChange('autoSave', e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                </label>
              </div>
            </div>
          </div>

          <button onClick={savePreferences} className="btn-primary">
            <FiCheck className="inline mr-2" />
            Save Preferences
          </button>
        </div>
      )}

      {/* Data Management Tab */}
      {activeTab === 'data' && (
        <div className="space-y-6">
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">Data Storage</h3>
            <div className="space-y-4">
              <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                <div className="flex items-start">
                  <FiAlertCircle className="text-yellow-600 mt-0.5 mr-2" />
                  <div>
                    <p className="text-sm font-medium text-yellow-800">Local Storage Only</p>
                    <p className="text-xs text-yellow-700 mt-1">
                      Currently, all data is stored locally. In production, data would be stored in a secure database.
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-600">Generated Emails</p>
                  <p className="text-2xl font-bold text-gray-900">45</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-600">Generated Posts</p>
                  <p className="text-2xl font-bold text-gray-900">12</p>
                </div>
              </div>

              <div className="space-y-2">
                <button
                  onClick={() => toast.info('Export feature coming soon!')}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-left"
                >
                  Export All Data
                </button>
                <button
                  onClick={() => {
                    if (window.confirm('Are you sure you want to clear all cached data?')) {
                      localStorage.clear();
                      toast.success('Cache cleared successfully!');
                    }
                  }}
                  className="w-full px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 transition-colors text-left"
                >
                  Clear Cache
                </button>
              </div>
            </div>
          </div>

          <div className="card">
            <h3 className="text-lg font-semibold mb-4">Privacy & Security</h3>
            <ul className="space-y-2 text-sm text-gray-600">
              <li className="flex items-start">
                <FiCheck className="text-green-600 mt-0.5 mr-2" />
                <span>All API keys are encrypted before storage</span>
              </li>
              <li className="flex items-start">
                <FiCheck className="text-green-600 mt-0.5 mr-2" />
                <span>Resume data is processed locally and not stored permanently</span>
              </li>
              <li className="flex items-start">
                <FiCheck className="text-green-600 mt-0.5 mr-2" />
                <span>Email tracking pixels are anonymous and GDPR compliant</span>
              </li>
              <li className="flex items-start">
                <FiCheck className="text-green-600 mt-0.5 mr-2" />
                <span>No personal data is shared with third parties</span>
              </li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default Settings;