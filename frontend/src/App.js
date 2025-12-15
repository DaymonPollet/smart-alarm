import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

function App() {
  const [data, setData] = useState([]);
  const [config, setConfig] = useState({ fitbit_connected: false, monitoring_active: false });
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState(false);
  const [monitoring, setMonitoring] = useState(false);
  const [monitoringInterval, setMonitoringInterval] = useState(null);
  const [message, setMessage] = useState('');

  // Fetch stored data
  const fetchData = useCallback(async () => {
    try {
      const response = await axios.get(`${API_URL}/api/data?limit=50`);
      setData(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching data:', error);
      setLoading(false);
    }
  }, []);

  // Fetch config
  const fetchConfig = useCallback(async () => {
    try {
      const response = await axios.get(`${API_URL}/api/config`);
      setConfig(response.data);
    } catch (error) {
      console.error('Error fetching config:', error);
    }
  }, []);

  useEffect(() => {
    fetchData();
    fetchConfig();
    // Only poll config, not data (to avoid confusion with manual fetch)
    const interval = setInterval(() => {
      fetchConfig();
    }, 10000);
    return () => {
      clearInterval(interval);
      if (monitoringInterval) clearInterval(monitoringInterval);
    };
  }, [fetchData, fetchConfig, monitoringInterval]);

  // Connect to Fitbit
  const connectFitbit = () => {
    axios.get(`${API_URL}/api/auth/login`)
      .then(response => {
        window.open(response.data.auth_url, '_blank', 'width=600,height=700');
        const checkInterval = setInterval(() => {
          fetchConfig();
        }, 2000);
        setTimeout(() => clearInterval(checkInterval), 60000);
      })
      .catch(error => {
        alert('Error starting OAuth: ' + error.message);
      });
  };

  // Fetch historical sleep data (main fetch button)
  const fetchHistoricalData = async () => {
    setFetching(true);
    setMessage('Fetching sleep history from Fitbit...');
    try {
      const response = await axios.post(`${API_URL}/api/fetch`);
      if (response.data) {
        setMessage(`✓ ${response.data.message}`);
        fetchData(); // Refresh display
        
        if (response.data.latest) {
          const latest = response.data.latest;
          console.log('Latest sleep data:', latest);
        }
      }
    } catch (error) {
      setMessage(`Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setFetching(false);
      setTimeout(() => setMessage(''), 5000);
    }
  };

  // Toggle monitoring mode (periodic current-reading fetch)
  const toggleMonitoring = async () => {
    if (monitoring) {
      try {
        await axios.post(`${API_URL}/api/monitoring/stop`);
        if (monitoringInterval) {
          clearInterval(monitoringInterval);
          setMonitoringInterval(null);
        }
        setMonitoring(false);
        setMessage('Monitoring stopped');
      } catch (error) {
        alert('Error stopping monitoring: ' + error.message);
      }
    } else {
      try {
        await axios.post(`${API_URL}/api/monitoring/start`);
        setMonitoring(true);
        setMessage('Monitoring started - checking every 60 seconds');
        
        // Use the current endpoint for monitoring
        const fetchCurrent = async () => {
          try {
            const response = await axios.post(`${API_URL}/api/fetch/current`);
            if (response.data) {
              console.log(`[${new Date().toLocaleTimeString()}] Quality: ${response.data.quality}, Score: ${response.data.overall_score}`);
              fetchData();
            }
          } catch (error) {
            console.error('Monitoring fetch error:', error);
          }
        };
        
        // Initial fetch
        fetchCurrent();
        
        // Set up interval
        const interval = setInterval(fetchCurrent, 60000);
        setMonitoringInterval(interval);
      } catch (error) {
        alert('Error starting monitoring: ' + error.message);
      }
    }
  };

  // Chart data - sleep quality over time
  const chartData = data.slice(0, 20).reverse().map((d, idx) => ({
    index: idx + 1,
    score: d.overall_score || 0,
    efficiency: d.efficiency || 0,
    deepSleep: d.deep_sleep_minutes || 0,
    date: d.timestamp ? new Date(d.timestamp).toLocaleDateString() : ''
  }));

  // Get quality color based on score
  const getQualityColor = (quality) => {
    switch(quality?.toLowerCase()) {
      case 'excellent': return '#28a745';
      case 'good': return '#5cb85c';
      case 'fair': return '#f0ad4e';
      case 'poor': return '#d9534f';
      default: return '#6c757d';
    }
  };

  const latestData = data[0] || {};

  return (
    <div className="App">
      <header className="App-header">
        <h1>🛏️ Smart Sleep Quality Dashboard</h1>
        <p className="subtitle">AI-Powered Sleep Quality Predictions</p>
      </header>

      <div className="container">
        {/* Connection Card */}
        <div className="card">
          <h2>Fitbit Connection</h2>
          <div className="config-item">
            <span>Status:</span>
            <span className={config.fitbit_connected ? 'status-enabled' : 'status-disabled'}>
              {config.fitbit_connected ? '✓ CONNECTED' : '✗ NOT CONNECTED'}
            </span>
          </div>
          {!config.fitbit_connected ? (
            <>
              <button onClick={connectFitbit} className="btn btn-primary">
                Connect Fitbit
              </button>
              <p className="note">Click to authorize access to your Fitbit sleep data</p>
            </>
          ) : (
            <>
              <button 
                onClick={fetchHistoricalData} 
                className="btn btn-primary"
                disabled={fetching}
              >
                {fetching ? '⏳ Fetching...' : '📊 Fetch Sleep History'}
              </button>
              <button 
                onClick={toggleMonitoring} 
                className={monitoring ? 'btn btn-danger' : 'btn btn-success'}
                disabled={fetching}
              >
                {monitoring ? '⏹️ Stop Monitoring' : '▶️ Start Monitoring'}
              </button>
              {message && <p className="message">{message}</p>}
              <p className="note">
                {monitoring 
                  ? '🔄 Monitoring active - Checking every 60 seconds' 
                  : 'Fetch History: Get all recent sleep sessions | Start Monitoring: Check every 60 seconds'}
              </p>
            </>
          )}
        </div>

        {/* Latest Reading Card */}
        <div className="card">
          <h2>Latest Sleep Analysis</h2>
          {loading ? (
            <p>Loading...</p>
          ) : latestData.timestamp ? (
            <div className="data-grid">
              <div className="data-item highlight">
                <span className="label">Sleep Quality:</span>
                <span 
                  className="value quality-badge" 
                  style={{ backgroundColor: getQualityColor(latestData.quality), color: 'white', padding: '5px 15px', borderRadius: '20px' }}
                >
                  {latestData.quality?.toUpperCase() || 'N/A'}
                </span>
              </div>
              <div className="data-item highlight">
                <span className="label">Overall Score:</span>
                <span className="value score">{latestData.overall_score?.toFixed(1) || 0}/100</span>
              </div>
              <div className="data-item">
                <span className="label">Sleep Date:</span>
                <span className="value">{latestData.timestamp ? new Date(latestData.timestamp).toLocaleDateString() : 'N/A'}</span>
              </div>
              <div className="data-item">
                <span className="label">Duration:</span>
                <span className="value">{latestData.duration_hours?.toFixed(1) || 'N/A'} hours</span>
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
                <span className="label">Minutes Asleep:</span>
                <span className="value">{latestData.minutes_asleep || 'N/A'}</span>
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
        </div>

        {/* Sleep Quality Trend Chart */}
        {chartData.length > 0 && (
          <div className="card chart-card">
            <h2>📈 Sleep Quality Trend</h2>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis domain={[0, 100]} label={{ value: 'Score', angle: -90, position: 'insideLeft' }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="score" stroke="#8884d8" strokeWidth={2} name="Quality Score" dot={{ r: 4 }} />
                <Line type="monotone" dataKey="efficiency" stroke="#82ca9d" strokeWidth={2} name="Efficiency %" dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Deep Sleep Chart */}
        {chartData.length > 0 && (
          <div className="card chart-card">
            <h2>🌙 Deep Sleep Minutes</h2>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis label={{ value: 'Minutes', angle: -90, position: 'insideLeft' }} />
                <Tooltip />
                <Bar dataKey="deepSleep" fill="#6366f1" name="Deep Sleep" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Sleep History Table */}
        <div className="card">
          <h2>📋 Sleep History</h2>
          <div className="history-table">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Duration</th>
                  <th>Efficiency</th>
                  <th>Deep Sleep</th>
                  <th>Score</th>
                  <th>Quality</th>
                </tr>
              </thead>
              <tbody>
                {data.length > 0 ? data.slice(0, 15).map((d, idx) => (
                  <tr key={idx} className={d.is_main_sleep ? 'main-sleep' : ''}>
                    <td>{d.timestamp ? new Date(d.timestamp).toLocaleDateString() : 'N/A'}</td>
                    <td>{d.duration_hours?.toFixed(1) || '-'} hrs</td>
                    <td>{d.efficiency || '-'}%</td>
                    <td>{d.deep_sleep_minutes || '-'} min</td>
                    <td><strong>{d.overall_score?.toFixed(0) || '-'}</strong></td>
                    <td>
                      <span 
                        className="quality-badge-small"
                        style={{ 
                          backgroundColor: getQualityColor(d.quality), 
                          color: 'white', 
                          padding: '2px 8px', 
                          borderRadius: '10px',
                          fontSize: '0.85em'
                        }}
                      >
                        {d.quality?.toUpperCase() || 'N/A'}
                      </span>
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan="6" style={{ textAlign: 'center', padding: '20px' }}>
                      No sleep data available. Connect Fitbit and fetch your sleep history.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* How It Works */}
        <div className="card">
          <h2>ℹ️ How It Works</h2>
          <ol>
            <li><strong>Connect Fitbit:</strong> Authorize access to your sleep and heart rate data</li>
            <li><strong>Fetch Sleep History:</strong> Loads your recent sleep sessions (up to 30 days)</li>
            <li><strong>AI Prediction:</strong> Our ML model analyzes each session and predicts sleep quality</li>
            <li><strong>Start Monitoring:</strong> (Optional) Auto-check current data every 60 seconds</li>
          </ol>
          <div className="quality-legend">
            <p><strong>Quality Scores:</strong></p>
            <span style={{ backgroundColor: '#28a745', color: 'white', padding: '3px 10px', borderRadius: '10px', margin: '0 5px' }}>Excellent (85+)</span>
            <span style={{ backgroundColor: '#5cb85c', color: 'white', padding: '3px 10px', borderRadius: '10px', margin: '0 5px' }}>Good (70-84)</span>
            <span style={{ backgroundColor: '#f0ad4e', color: 'white', padding: '3px 10px', borderRadius: '10px', margin: '0 5px' }}>Fair (55-69)</span>
            <span style={{ backgroundColor: '#d9534f', color: 'white', padding: '3px 10px', borderRadius: '10px', margin: '0 5px' }}>Poor (&lt;55)</span>
          </div>
          <p className="note" style={{ marginTop: '15px' }}>
            <strong>Model Features:</strong> Revitalization score, Deep sleep duration, Resting heart rate, 
            Restlessness, Day of week, Weekend indicator, Wakeup hour, and lagged features.
          </p>
        </div>
      </div>
    </div>
  );
}

export default App;
