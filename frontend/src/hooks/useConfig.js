/**
 * Custom Hook: useConfig
 * Manages system configuration state and polling.
 */
import { useState, useEffect, useCallback } from 'react';
import { sleepService } from '../services/api';

const INITIAL_CONFIG = {
  fitbit_connected: false,
  monitoring_active: false,
  azure_available: false,
  cloud_enabled: true,
  mqtt_connected: false,
  pending_sync_count: 0,
  alarm: null,
};

export const useConfig = (pollInterval = 5000) => {
  const [config, setConfig] = useState(INITIAL_CONFIG);
  const [error, setError] = useState(null);

  const fetchConfig = useCallback(async () => {
    try {
      setError(null);
      const response = await sleepService.getConfig();
      setConfig(response.data);
      return response.data;
    } catch (err) {
      setError(err.message);
      console.error('Error fetching config:', err);
      return null;
    }
  }, []);

  useEffect(() => {
    fetchConfig();
    const interval = setInterval(fetchConfig, pollInterval);
    return () => clearInterval(interval);
  }, [fetchConfig, pollInterval]);

  return {
    config,
    error,
    refetch: fetchConfig,
  };
};

export default useConfig;
