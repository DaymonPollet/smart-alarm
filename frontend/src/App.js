/**
 * Smart Sleep Quality Dashboard
 * Main Application Component (Refactored)
 * 
 * Architecture:
 * - Hooks: useSleepDashboard handles all state & logic
 * - Components: Reusable UI components
 * - Services: API communication
 */
import React from 'react';
import { useSleepDashboard } from './hooks';
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
import { getQualityColor, formatNumber } from './utils/helpers';
import './App.css';

// Sub-components for better organization
const SystemStatus = ({ config }) => (
  <Card title="System Status" variant="status">
    <div className="status-grid">
      <StatusBadge label="Fitbit" isActive={config.fitbit_connected} activeText="Connected" inactiveText="Disconnected" />
      <StatusBadge label="Local Model" isActive={true} activeText="Active" />
      <StatusBadge label="Azure Cloud" isActive={config.azure_available} activeText="Online" inactiveText="Offline" />
      <StatusBadge label="MQTT" isActive={config.mqtt_connected} activeText="Connected" inactiveText="Disconnected" />
      <StatusBadge label="IoT Hub" isActive={config.iothub_connected} activeText="Connected" inactiveText="Disconnected" />
    </div>
  </Card>
);

const FitbitConnection = ({ config, fetching, monitoring, message, onConnect, onFetch, onToggleMonitoring }) => (
  <Card title="Fitbit Connection">
    {!config.fitbit_connected ? (
      <>
        <button onClick={onConnect} className="btn btn-primary">Connect Fitbit</button>
        <p className="note">Click to authorize access to your Fitbit sleep data</p>
      </>
    ) : (
      <>
        <button onClick={onFetch} className="btn btn-primary" disabled={fetching}>
          {fetching ? 'Fetching...' : 'Fetch Sleep History'}
        </button>
        <button onClick={onToggleMonitoring} className={monitoring ? 'btn btn-danger' : 'btn btn-success'} disabled={fetching}>
          {monitoring ? 'Stop Monitoring' : 'Start Monitoring'}
        </button>
        {message && <p className="message">{message}</p>}
        <p className="note">
          {monitoring ? 'Monitoring active - Checking every 60 seconds' : 'Fetch History: Get recent sessions | Start Monitoring: Check every 60s'}
        </p>
      </>
    )}
  </Card>
);

const AlarmConfig = ({ config, alarmTime, alarmWindow, setAlarmTime, setAlarmWindow, onSet, onDisable }) => (
  <Card title="⏰ Smart Alarm" variant="alarm">
    {config.alarm?.enabled ? (
      <div className="alarm-active">
        <div className="alarm-status">
          <span className="alarm-badge active">Alarm Active</span>
          <p>Wake time: <strong>{config.alarm.wake_time}</strong></p>
          <p>Smart window: <strong>{config.alarm.window_minutes} minutes</strong></p>
          {config.alarm.triggered && <p className="alarm-triggered-text">🔔 Triggered: {config.alarm.trigger_reason}</p>}
        </div>
        <button onClick={onDisable} className="btn btn-danger">Disable Alarm</button>
      </div>
    ) : (
      <div className="alarm-config">
        <div className="config-row">
          <label>Wake Time:</label>
          <input type="time" value={alarmTime} onChange={(e) => setAlarmTime(e.target.value)} className="time-input" />
        </div>
        <div className="config-row">
          <label>Smart Window:</label>
          <select value={alarmWindow} onChange={(e) => setAlarmWindow(Number(e.target.value))} className="select-input">
            <option value={15}>15 minutes</option>
            <option value={30}>30 minutes</option>
            <option value={45}>45 minutes</option>
            <option value={60}>60 minutes</option>
          </select>
        </div>
        <p className="note">The alarm will try to wake you during light sleep within the window.</p>
        <button onClick={onSet} className="btn btn-success">Set Alarm</button>
      </div>
    )}
  </Card>
);

const CloudConfig = ({ config, onToggle }) => (
  <Card title="☁️ Cloud Configuration" variant="cloud">
    <div className="cloud-status">
      <div className="cloud-toggle-row">
        <span>Cloud Sync:</span>
        <button onClick={onToggle} className={`toggle-btn ${config.cloud_enabled ? 'enabled' : 'disabled'}`}>
          {config.cloud_enabled ? 'Enabled' : 'Disabled'}
        </button>
      </div>
      {!config.cloud_enabled && config.pending_sync_count > 0 && (
        <p className="pending-sync">⏳ {config.pending_sync_count} predictions queued for sync</p>
      )}
      <p className="note">
        {config.cloud_enabled 
          ? 'Predictions are sent to Azure ML and Application Insights in real-time.'
          : 'Predictions are stored locally and will sync when cloud is re-enabled.'}
      </p>
    </div>
  </Card>
);

const QualityBadge = ({ quality }) => (
  <span 
    className="value quality-badge" 
    style={{ backgroundColor: getQualityColor(quality), color: 'white', padding: '5px 15px', borderRadius: '20px' }}
  >
    {quality?.toUpperCase() || 'N/A'}
  </span>
);

const ModelResult = ({ label, quality, extra }) => (
  <div className="data-item model-result">
    <span className="label">{label}:</span>
    <span className="value">
      {quality ? (
        <>
          <span style={{ backgroundColor: getQualityColor(quality), color: 'white', padding: '2px 8px', borderRadius: '10px', marginRight: '8px' }}>
            {quality?.toUpperCase()}
          </span>
          {extra}
        </>
      ) : (
        <span style={{ color: '#999' }}>Not available (offline)</span>
      )}
    </span>
  </div>
);

const LatestAnalysis = ({ loading, latestData }) => (
  <Card title="Latest Sleep Analysis">
    {loading ? (
      <p>Loading...</p>
    ) : latestData.timestamp ? (
      <div className="data-grid">
        <div className="data-item highlight full-width">
          <span className="label">Final Quality (Best Available):</span>
          <QualityBadge quality={latestData.quality} />
        </div>
        
        <ModelResult label="Local Model" quality={latestData.local_quality} extra={`Score: ${formatNumber(latestData.local_score)}`} />
        <ModelResult 
          label="Cloud Model" 
          quality={latestData.cloud_quality} 
          extra={`Confidence: ${((latestData.cloud_confidence || 0) * 100).toFixed(1)}%`} 
        />

        <div className="data-item">
          <span className="label">Sleep Date:</span>
          <span className="value">{latestData.timestamp ? new Date(latestData.timestamp).toLocaleDateString() : 'N/A'}</span>
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
      <p className="empty-state">No sleep data yet. Click "Fetch Sleep History" to load your recent sleep sessions.</p>
    )}
  </Card>
);

function App() {
  const {
    data, config, loading, fetching, monitoring, message,
    alarmTime, alarmWindow, showAlarmPopup, alarmTriggerReason,
    chartData, latestData,
    setAlarmTime, setAlarmWindow,
    handleManualRefresh, handleConnectFitbit, handleFetchHistory,
    handleToggleMonitoring, handleSetAlarm, handleDisableAlarm,
    handleSnoozeAlarm, handleDismissAlarm, handleToggleCloud,
  } = useSleepDashboard();

  return (
    <div className="App">
      {showAlarmPopup && (
        <AlarmPopup triggerReason={alarmTriggerReason} onSnooze={handleSnoozeAlarm} onDismiss={handleDismissAlarm} />
      )}

      <header className="App-header">
        <div className="header-content">
          <div>
            <h1>Smart Sleep Quality Dashboard</h1>
            <p className="subtitle">AI-Powered Sleep Quality Predictions (Local + Cloud)</p>
          </div>
          <button onClick={handleManualRefresh} className="refresh-button" title="Manually refresh data">🔄 Refresh</button>
        </div>
      </header>

      <div className="container">
        <SystemStatus config={config} />
        <FitbitConnection 
          config={config} fetching={fetching} monitoring={monitoring} message={message}
          onConnect={handleConnectFitbit} onFetch={handleFetchHistory} onToggleMonitoring={handleToggleMonitoring}
        />
        <AlarmConfig 
          config={config} alarmTime={alarmTime} alarmWindow={alarmWindow}
          setAlarmTime={setAlarmTime} setAlarmWindow={setAlarmWindow}
          onSet={handleSetAlarm} onDisable={handleDisableAlarm}
        />
        <CloudConfig config={config} onToggle={handleToggleCloud} />
        <LatestAnalysis loading={loading} latestData={latestData} />
        <ProbabilityBars probabilities={latestData.cloud_probabilities} />
        <SleepChart data={chartData} />
        <DeepSleepChart data={chartData} />
        <SleepHistory data={data} />
        <ArchitectureInfo />
      </div>
    </div>
  );
}

export default App;
