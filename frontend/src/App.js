/**
 * Smart Sleep Quality Dashboard
 * Main Application Component
 * 
 * Architecture:
 * - Services Layer: API communication (services/api.js)
 * - Components Layer: Reusable UI components (components/)
 * - Hooks Layer: Stateful logic (hooks/)
 * - Utils Layer: Helper functions (utils/)
 * 
 * Design Principles:
 * - Separation of Concerns (SoC)
 * - Don't Repeat Yourself (DRY)
 * - Single Responsibility Principle (SRP)
 */
import React, { useState, useEffect, useCallback } from 'react';

// Services
import { 
  sleepService, 
  authService, 
  monitoringService, 
  alarmService, 
  cloudService 
} from './services/api';

// Components
import {
  StatusBadge,
  AlarmPopup,
  Card,
  SleepChart,
  DeepSleepChart,
  ProbabilityBars,
  SleepHistory,
  ArchitectureInfo,
} from './components';

// Utils
import { getQualityColor, formatNumber } from './utils/helpers';

// Styles
import './App.css';

// Initial configuration state
const INITIAL_CONFIG = {
  fitbit_connected: false,
  monitoring_active: false,
  azure_available: false,
  cloud_enabled: true,
  mqtt_connected: false,
  pending_sync_count: 0,
  alarm: null,
};

function App() {
  // State Management
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

  // ============================================
  // Data Fetching Functions (using Service Layer)
  // ============================================
  
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
      
      // Check for triggered alarm
      if (response.data.alarm?.triggered && !showAlarmPopup) {
        setShowAlarmPopup(true);
        setAlarmTriggerReason(response.data.alarm.trigger_reason || 'Wake time reached');
      }
    } catch (error) {
      console.error('Error fetching config:', error);
    }
  }, [showAlarmPopup]);

  // ============================================
  // Lifecycle Effects
  // ============================================
  
  useEffect(() => {
    fetchData();
    fetchConfig();
    
    const interval = setInterval(fetchConfig, 5000);
    
    return () => {
      clearInterval(interval);
      if (monitoringInterval) clearInterval(monitoringInterval);
    };
  }, [fetchData, fetchConfig, monitoringInterval]);

  // ============================================
  // Event Handlers
  // ============================================
  
  const showMessage = (msg, duration = 5000) => {
    setMessage(msg);
    setTimeout(() => setMessage(''), duration);
  };

  const handleConnectFitbit = async () => {
    try {
      const response = await authService.getLoginUrl();
      window.open(response.data.auth_url, '_blank', 'width=600,height=700');
      
      // Poll for connection status
      const checkInterval = setInterval(fetchConfig, 2000);
      setTimeout(() => clearInterval(checkInterval), 60000);
    } catch (error) {
      alert('Error starting OAuth: ' + error.message);
    }
  };

  const handleFetchHistory = async () => {
    setFetching(true);
    setMessage('Fetching sleep history from Fitbit...');
    
    try {
      const response = await sleepService.fetchHistory();
      if (response.data) {
        const cloudStatus = response.data.cloud_available 
          ? ' (Cloud model active)' 
          : ' (Local model only)';
        showMessage(response.data.message + cloudStatus);
        fetchData();
        fetchConfig();
      }
    } catch (error) {
      showMessage(`Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setFetching(false);
    }
  };

  const handleToggleMonitoring = async () => {
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
              console.log(`[${new Date().toLocaleTimeString()}] Quality: ${response.data.quality}, Score: ${response.data.overall_score}`);
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
  };

  const handleSetAlarm = async () => {
    try {
      await alarmService.setAlarm(alarmTime, alarmWindow);
      showMessage(`Alarm set for ${alarmTime} (${alarmWindow}min window)`);
      fetchConfig();
    } catch (error) {
      showMessage('Error setting alarm: ' + error.message);
    }
  };

  const handleDisableAlarm = async () => {
    try {
      await alarmService.deleteAlarm();
      showMessage('Alarm disabled');
      fetchConfig();
    } catch (error) {
      showMessage('Error disabling alarm: ' + error.message);
    }
  };

  const handleSnoozeAlarm = async () => {
    try {
      const response = await alarmService.snoozeAlarm();
      setShowAlarmPopup(false);
      showMessage(`Snoozed until ${response.data.new_wake_time}`);
      fetchConfig();
    } catch (error) {
      console.error('Snooze error:', error);
    }
  };

  const handleDismissAlarm = async () => {
    try {
      await alarmService.dismissAlarm();
      setShowAlarmPopup(false);
      showMessage('Alarm dismissed');
      fetchConfig();
    } catch (error) {
      console.error('Dismiss error:', error);
    }
  };

  const handleToggleCloud = async () => {
    try {
      const response = await cloudService.toggleCloud(!config.cloud_enabled);
      if (response.data.synced > 0) {
        showMessage(`Cloud enabled - synced ${response.data.synced} pending predictions`);
      } else {
        showMessage(response.data.cloud_enabled 
          ? 'Cloud enabled' 
          : 'Cloud disabled - predictions will queue locally'
        );
      }
      fetchConfig();
    } catch (error) {
      showMessage('Error toggling cloud: ' + error.message);
    }
  };

  // ============================================
  // Computed Values
  // ============================================
  
  const chartData = data.slice(0, 20).reverse().map((d, idx) => ({
    index: idx + 1,
    score: d.overall_score || d.local_score || 0,
    efficiency: d.efficiency || 0,
    deepSleep: d.deep_sleep_minutes || 0,
    date: d.timestamp ? new Date(d.timestamp).toLocaleDateString() : '',
  }));

  const latestData = data[0] || {};

  // ============================================
  // Render
  // ============================================
  
  return (
    <div className="App">
      {/* Alarm Popup Overlay */}
      {showAlarmPopup && (
        <AlarmPopup
          triggerReason={alarmTriggerReason}
          onSnooze={handleSnoozeAlarm}
          onDismiss={handleDismissAlarm}
        />
      )}

      {/* Header */}
      <header className="App-header">
        <h1>Smart Sleep Quality Dashboard</h1>
        <p className="subtitle">AI-Powered Sleep Quality Predictions (Local + Cloud)</p>
      </header>

      <div className="container">
        {/* System Status Card */}
        <Card title="System Status" variant="status">
          <div className="status-grid">
            <StatusBadge 
              label="Fitbit" 
              isActive={config.fitbit_connected}
              activeText="Connected"
              inactiveText="Disconnected"
            />
            <StatusBadge 
              label="Local Model" 
              isActive={true}
              activeText="Active"
            />
            <StatusBadge 
              label="Azure Cloud" 
              isActive={config.azure_available}
              activeText="Online"
              inactiveText="Offline"
            />
            <StatusBadge 
              label="MQTT" 
              isActive={config.mqtt_connected}
              activeText="Connected"
              inactiveText="Disconnected"
            />
          </div>
        </Card>

        {/* Fitbit Connection Card */}
        <Card title="Fitbit Connection">
          {!config.fitbit_connected ? (
            <>
              <button onClick={handleConnectFitbit} className="btn btn-primary">
                Connect Fitbit
              </button>
              <p className="note">Click to authorize access to your Fitbit sleep data</p>
            </>
          ) : (
            <>
              <button 
                onClick={handleFetchHistory} 
                className="btn btn-primary"
                disabled={fetching}
              >
                {fetching ? 'Fetching...' : 'Fetch Sleep History'}
              </button>
              <button 
                onClick={handleToggleMonitoring} 
                className={monitoring ? 'btn btn-danger' : 'btn btn-success'}
                disabled={fetching}
              >
                {monitoring ? 'Stop Monitoring' : 'Start Monitoring'}
              </button>
              {message && <p className="message">{message}</p>}
              <p className="note">
                {monitoring 
                  ? 'Monitoring active - Checking every 60 seconds' 
                  : 'Fetch History: Get recent sleep sessions | Start Monitoring: Check every 60 seconds'}
              </p>
            </>
          )}
        </Card>

        {/* Alarm Configuration Card */}
        <Card title="⏰ Smart Alarm" variant="alarm">
          {config.alarm?.enabled ? (
            <div className="alarm-active">
              <div className="alarm-status">
                <span className="alarm-badge active">Alarm Active</span>
                <p>Wake time: <strong>{config.alarm.wake_time}</strong></p>
                <p>Smart window: <strong>{config.alarm.window_minutes} minutes</strong></p>
                {config.alarm.triggered && (
                  <p className="alarm-triggered-text">⚡ Triggered: {config.alarm.trigger_reason}</p>
                )}
              </div>
              <button onClick={handleDisableAlarm} className="btn btn-danger">
                Disable Alarm
              </button>
            </div>
          ) : (
            <div className="alarm-config">
              <div className="config-row">
                <label>Wake Time:</label>
                <input 
                  type="time" 
                  value={alarmTime} 
                  onChange={(e) => setAlarmTime(e.target.value)}
                  className="time-input"
                />
              </div>
              <div className="config-row">
                <label>Smart Window:</label>
                <select 
                  value={alarmWindow} 
                  onChange={(e) => setAlarmWindow(Number(e.target.value))}
                  className="select-input"
                >
                  <option value={15}>15 minutes</option>
                  <option value={30}>30 minutes</option>
                  <option value={45}>45 minutes</option>
                  <option value={60}>60 minutes</option>
                </select>
              </div>
              <p className="note">
                The alarm will try to wake you during light sleep within the window before your wake time.
              </p>
              <button onClick={handleSetAlarm} className="btn btn-success">
                Set Alarm
              </button>
            </div>
          )}
        </Card>

        {/* Cloud Configuration Card */}
        <Card title="☁️ Cloud Configuration" variant="cloud">
          <div className="cloud-status">
            <div className="cloud-toggle-row">
              <span>Cloud Sync:</span>
              <button 
                onClick={handleToggleCloud}
                className={`toggle-btn ${config.cloud_enabled ? 'enabled' : 'disabled'}`}
              >
                {config.cloud_enabled ? 'Enabled' : 'Disabled'}
              </button>
            </div>
            {!config.cloud_enabled && config.pending_sync_count > 0 && (
              <p className="pending-sync">
                📦 {config.pending_sync_count} predictions queued for sync
              </p>
            )}
            <p className="note">
              {config.cloud_enabled 
                ? 'Predictions are sent to Azure ML and Application Insights in real-time.'
                : 'Predictions are stored locally and will sync when cloud is re-enabled.'}
            </p>
          </div>
        </Card>

        {/* Latest Sleep Analysis Card */}
        <Card title="Latest Sleep Analysis">
          {loading ? (
            <p>Loading...</p>
          ) : latestData.timestamp ? (
            <div className="data-grid">
              {/* Primary Quality Display */}
              <div className="data-item highlight full-width">
                <span className="label">Final Quality (Best Available):</span>
                <span 
                  className="value quality-badge" 
                  style={{ 
                    backgroundColor: getQualityColor(latestData.quality), 
                    color: 'white', 
                    padding: '5px 15px', 
                    borderRadius: '20px' 
                  }}
                >
                  {latestData.quality?.toUpperCase() || 'N/A'}
                </span>
              </div>
              
              {/* Model Comparison */}
              <div className="data-item model-result">
                <span className="label">Local Model:</span>
                <span className="value">
                  <span style={{ 
                    backgroundColor: getQualityColor(latestData.local_quality), 
                    color: 'white', 
                    padding: '2px 8px', 
                    borderRadius: '10px', 
                    marginRight: '8px' 
                  }}>
                    {latestData.local_quality?.toUpperCase() || 'N/A'}
                  </span>
                  Score: {formatNumber(latestData.local_score)}
                </span>
              </div>
              
              <div className="data-item model-result">
                <span className="label">Cloud Model:</span>
                <span className="value">
                  {latestData.cloud_quality ? (
                    <>
                      <span style={{ 
                        backgroundColor: getQualityColor(latestData.cloud_quality), 
                        color: 'white', 
                        padding: '2px 8px', 
                        borderRadius: '10px', 
                        marginRight: '8px' 
                      }}>
                        {latestData.cloud_quality?.toUpperCase()}
                      </span>
                      Confidence: {((latestData.cloud_confidence || 0) * 100).toFixed(1)}%
                    </>
                  ) : (
                    <span style={{ color: '#999' }}>Not available (offline)</span>
                  )}
                </span>
              </div>

              <div className="data-item">
                <span className="label">Sleep Date:</span>
                <span className="value">
                  {latestData.timestamp ? new Date(latestData.timestamp).toLocaleDateString() : 'N/A'}
                </span>
              </div>
              <div className="data-item">
                <span className="label">Duration:</span>
                <span className="value">{formatNumber(latestData.duration_hours)} hours</span>
              </div>
              <div className="data-item">
                <span className="label">Sleep Efficiency:</span>
                <span className="value">{latestData.efficiency || 'N/A'}%</span>
              </div>
              <div className="data-item">
                <span className="label">Deep Sleep:</span>
                <span className="value">{latestData.deep_sleep_minutes || 0} min</span>
              </div>
              <div className="data-item">
                <span className="label">Restlessness:</span>
                <span className="value">{((latestData.restlessness || 0) * 100).toFixed(1)}%</span>
              </div>
              <div className="data-item">
                <span className="label">Resting HR:</span>
                <span className="value">{latestData.resting_heart_rate || 'N/A'} bpm</span>
              </div>
            </div>
          ) : (
            <p className="empty-state">
              No sleep data yet. Click "Fetch Sleep History" to load your recent sleep sessions.
            </p>
          )}
        </Card>

        {/* Cloud Probabilities */}
        <ProbabilityBars probabilities={latestData.cloud_probabilities} />

        {/* Charts */}
        <SleepChart data={chartData} />
        <DeepSleepChart data={chartData} />

        {/* Sleep History Table */}
        <SleepHistory data={data} />

        {/* Architecture Info */}
        <ArchitectureInfo />
      </div>
    </div>
  );
}

export default App;
