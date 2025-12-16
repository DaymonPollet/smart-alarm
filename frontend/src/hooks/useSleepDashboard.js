/**
 * Custom Hook for Sleep Dashboard State Management
 * Handles all data fetching, state management, and event handlers
 */
import { useState, useEffect, useCallback } from 'react';
import { 
  sleepService, 
  authService, 
  monitoringService, 
  alarmService, 
  cloudService 
} from '../services/api';

const INITIAL_CONFIG = {
  fitbit_connected: false,
  monitoring_active: false,
  azure_available: false,
  cloud_enabled: true,
  mqtt_connected: false,
  iothub_connected: false,
  pending_sync_count: 0,
  alarm: null,
};

export function useSleepDashboard() {
  // Core State
  const [data, setData] = useState([]);
  const [config, setConfig] = useState(INITIAL_CONFIG);
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState(false);
  const [monitoring, setMonitoring] = useState(false);
  const [monitoringInterval, setMonitoringInterval] = useState(null);
  const [message, setMessage] = useState('');
  
  // Alarm State
  const [alarmTime, setAlarmTime] = useState('07:00');
  const [alarmWindow, setAlarmWindow] = useState(30);
  const [showAlarmPopup, setShowAlarmPopup] = useState(false);
  const [alarmTriggerReason, setAlarmTriggerReason] = useState('');

  // Message Helper
  const showMessage = useCallback((msg, duration = 5000) => {
    setMessage(msg);
    setTimeout(() => setMessage(''), duration);
  }, []);

  // Data Fetching
  const fetchData = useCallback(async () => {
    try {
      const response = await sleepService.getData();
      setData(response.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchConfig = useCallback(async () => {
    try {
      const response = await sleepService.getConfig();
      setConfig(response.data);
      
      if (response.data.alarm?.triggered && !showAlarmPopup) {
        setShowAlarmPopup(true);
        setAlarmTriggerReason(response.data.alarm.trigger_reason || 'Wake time reached');
      }
    } catch (error) {
      console.error('Error fetching config:', error);
    }
  }, [showAlarmPopup]);

  // Initial Load & Alarm Polling
  useEffect(() => {
    fetchData();
    fetchConfig();
    
    let alarmCheckInterval = null;
    if (config.alarm?.enabled && !config.alarm?.triggered) {
      alarmCheckInterval = setInterval(fetchConfig, 60000);
    }
    
    return () => {
      if (alarmCheckInterval) clearInterval(alarmCheckInterval);
      if (monitoringInterval) clearInterval(monitoringInterval);
    };
  }, [fetchData, fetchConfig, monitoringInterval, config.alarm?.enabled, config.alarm?.triggered]);

  // Event Handlers
  const handleManualRefresh = useCallback(async () => {
    setMessage('Refreshing...');
    await Promise.all([fetchData(), fetchConfig()]);
    setMessage('');
  }, [fetchData, fetchConfig]);

  const handleConnectFitbit = useCallback(async () => {
    try {
      const response = await authService.getLoginUrl();
      window.open(response.data.auth_url, '_blank', 'width=600,height=700');
      const checkInterval = setInterval(fetchConfig, 2000);
      setTimeout(() => clearInterval(checkInterval), 60000);
    } catch (error) {
      alert('Error starting OAuth: ' + error.message);
    }
  }, [fetchConfig]);

  const handleFetchHistory = useCallback(async () => {
    setFetching(true);
    setMessage('Fetching sleep history from Fitbit...');
    
    try {
      const response = await sleepService.fetchHistory();
      if (response.data) {
        const cloudStatus = response.data.cloud_available 
          ? ' (Cloud model active)' 
          : ' (Local model only)';
        showMessage(response.data.message + cloudStatus);
        await Promise.all([fetchData(), fetchConfig()]);
      }
    } catch (error) {
      showMessage(`Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setFetching(false);
    }
  }, [fetchData, fetchConfig, showMessage]);

  const handleToggleMonitoring = useCallback(async () => {
    if (monitoring) {
      try {
        await monitoringService.stop();
        if (monitoringInterval) {
          clearInterval(monitoringInterval);
          setMonitoringInterval(null);
        }
        setMonitoring(false);
        showMessage('Monitoring stopped');
      } catch (error) {
        alert('Error stopping monitoring: ' + error.message);
      }
    } else {
      try {
        await monitoringService.start();
        setMonitoring(true);
        showMessage('Monitoring started - checking every 60 seconds');
        
        const fetchCurrent = async () => {
          try {
            const response = await sleepService.fetchCurrent();
            if (response.data) {
              console.log(`[${new Date().toLocaleTimeString()}] Quality: ${response.data.quality}`);
              fetchData();
            }
          } catch (error) {
            console.error('Monitoring fetch error:', error);
          }
        };
        
        fetchCurrent();
        const interval = setInterval(fetchCurrent, 60000);
        setMonitoringInterval(interval);
      } catch (error) {
        alert('Error starting monitoring: ' + error.message);
      }
    }
  }, [monitoring, monitoringInterval, showMessage, fetchData]);

  const handleSetAlarm = useCallback(async () => {
    setConfig(prev => ({
      ...prev,
      alarm: { ...prev.alarm, enabled: true, wake_time: alarmTime, window_minutes: alarmWindow }
    }));
    showMessage(`Alarm set for ${alarmTime} (${alarmWindow}min window)`);
    
    try {
      await alarmService.setAlarm(alarmTime, alarmWindow);
      fetchConfig();
    } catch (error) {
      showMessage('Error setting alarm: ' + error.message);
      fetchConfig();
    }
  }, [alarmTime, alarmWindow, showMessage, fetchConfig]);

  const handleDisableAlarm = useCallback(async () => {
    setConfig(prev => ({
      ...prev,
      alarm: { ...prev.alarm, enabled: false, triggered: false }
    }));
    showMessage('Alarm disabled');
    
    try {
      await alarmService.deleteAlarm();
    } catch (error) {
      showMessage('Error disabling alarm: ' + error.message);
      fetchConfig();
    }
  }, [showMessage, fetchConfig]);

  const handleSnoozeAlarm = useCallback(async () => {
    setShowAlarmPopup(false);
    showMessage('Snoozing...');
    
    try {
      const response = await alarmService.snoozeAlarm();
      showMessage(`Snoozed until ${response.data.new_wake_time}`);
      fetchConfig();
    } catch (error) {
      console.error('Snooze error:', error);
    }
  }, [showMessage, fetchConfig]);

  const handleDismissAlarm = useCallback(async () => {
    setShowAlarmPopup(false);
    setConfig(prev => ({
      ...prev,
      alarm: { ...prev.alarm, triggered: false }
    }));
    showMessage('Alarm dismissed');
    
    try {
      await alarmService.dismissAlarm();
    } catch (error) {
      console.error('Dismiss error:', error);
    }
  }, [showMessage]);

  const handleToggleCloud = useCallback(async () => {
    const newCloudEnabled = !config.cloud_enabled;
    
    setConfig(prev => ({ ...prev, cloud_enabled: newCloudEnabled }));
    showMessage(newCloudEnabled ? 'Enabling cloud...' : 'Cloud disabled');
    
    try {
      const response = await cloudService.toggleCloud(newCloudEnabled);
      if (response.data.synced > 0) {
        showMessage(`Cloud enabled - synced ${response.data.synced} pending predictions`);
        fetchData();
      } else {
        showMessage(newCloudEnabled 
          ? 'Cloud enabled' 
          : 'Cloud disabled - predictions will queue locally'
        );
      }
      fetchConfig();
    } catch (error) {
      showMessage('Error toggling cloud: ' + error.message);
      fetchConfig();
    }
  }, [config.cloud_enabled, showMessage, fetchData, fetchConfig]);

  // Computed Values
  const chartData = data.slice(0, 20).reverse().map((d, idx) => ({
    index: idx + 1,
    score: d.overall_score || d.local_score || 0,
    efficiency: d.efficiency || 0,
    deepSleep: d.deep_sleep_minutes || 0,
    date: d.timestamp ? new Date(d.timestamp).toLocaleDateString() : '',
  }));

  const latestData = data[0] || {};

  return {
    // State
    data,
    config,
    loading,
    fetching,
    monitoring,
    message,
    alarmTime,
    alarmWindow,
    showAlarmPopup,
    alarmTriggerReason,
    chartData,
    latestData,
    
    // Setters
    setAlarmTime,
    setAlarmWindow,
    
    // Handlers
    handleManualRefresh,
    handleConnectFitbit,
    handleFetchHistory,
    handleToggleMonitoring,
    handleSetAlarm,
    handleDisableAlarm,
    handleSnoozeAlarm,
    handleDismissAlarm,
    handleToggleCloud,
  };
}
