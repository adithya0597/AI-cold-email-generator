import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Email Service APIs
export const emailService = {
  generateEmail: async (data) => {
    const response = await api.post('/api/generate-email', data);
    return response.data;
  },

  parseResume: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/api/parse-resume', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getEmailStats: async (emailId) => {
    const response = await api.get(`/api/email/${emailId}/stats`);
    return response.data;
  },

  getTrackingPixelUrl: (emailId) => {
    return `${API_BASE_URL}/api/track/email/${emailId}/pixel.gif`;
  },
};

// LinkedIn Service APIs
export const linkedInService = {
  generatePost: async (data) => {
    const response = await api.post('/api/generate-post', data);
    return response.data;
  },

};

// Utility APIs
export const utilityService = {
  scrapeUrl: async (url) => {
    const response = await api.post('/api/scrape-url', { url });
    return response.data;
  },

  checkHealth: async () => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;