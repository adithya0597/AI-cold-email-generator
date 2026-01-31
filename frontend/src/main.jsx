import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { AuthProvider } from './providers/ClerkProvider';
import { AnalyticsProvider } from './providers/AnalyticsProvider';
import { QueryProvider } from './providers/QueryProvider';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <AuthProvider>
      <AnalyticsProvider>
        <QueryProvider>
          <App />
        </QueryProvider>
      </AnalyticsProvider>
    </AuthProvider>
  </React.StrictMode>
);
