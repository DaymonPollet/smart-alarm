/**
 * API Service Layer
 * Centralizes all HTTP communication with the backend.
 * Implements Separation of Concerns (SoC) principle.
 */
import axios from 'axios';

// For Kubernetes: REACT_APP_API_URL should be empty to use relative paths via nginx proxy
// For local dev: REACT_APP_API_URL defaults to localhost:8080
const API_URL = process.env.REACT_APP_API_URL !== undefined 
  ? process.env.REACT_APP_API_URL 
  : 'http://localhost:8080';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_URL || '',  // Empty string = relative URLs
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Sleep Data Service
 * Handles all sleep-related API operations
 */
export const sleepService = {
  // Fetch sleep history data
  getData: (limit = 50) => api.get(`/api/data?limit=${limit}`),
  
  // Get system configuration
  getConfig: () => api.get('/api/config'),
  
  // Fetch historical sleep data from Fitbit
  fetchHistory: () => api.post('/api/fetch'),
  
  // Fetch current sleep data
  fetchCurrent: () => api.post('/api/fetch/current'),
};

/**
 * Auth Service
 * Handles Fitbit OAuth operations
 */
export const authService = {
  // Get Fitbit OAuth login URL
  getLoginUrl: () => api.get('/api/auth/login'),
};

/**
 * Monitoring Service
 * Handles real-time monitoring operations
 */
export const monitoringService = {
  // Start monitoring
  start: () => api.post('/api/monitoring/start'),
  
  // Stop monitoring
  stop: () => api.post('/api/monitoring/stop'),
};

/**
 * Alarm Service
 * Handles smart alarm operations
 */
export const alarmService = {
  // Set alarm with wake time and window
  setAlarm: (wakeTime, windowMinutes) => 
    api.post('/api/alarm', { wake_time: wakeTime, window_minutes: windowMinutes }),
  
  // Delete/disable alarm
  deleteAlarm: () => api.delete('/api/alarm'),
  
  // Dismiss triggered alarm
  dismissAlarm: () => api.post('/api/alarm/dismiss'),
  
  // Snooze alarm
  snoozeAlarm: (minutes = 9) => api.post('/api/alarm/snooze', { minutes }),
};

/**
 * Cloud Service
 * Handles cloud sync operations
 */
export const cloudService = {
  // Toggle cloud sync on/off
  toggleCloud: (enabled) => api.post('/api/cloud/toggle', { enabled }),
};

// Export the base API instance for advanced use cases
export default api;
