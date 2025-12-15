import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

function App() {
  const [data, setData] = useState([]);
  const [config, setConfig] = useState({ fitbit_enabled: false });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    fetchConfig();
    const interval = setInterval(() => {
      fetchData();
      fetchConfig();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/data?limit=50`);
      setData(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching data:', error);
      setLoading(false);
    }
  };

  const fetchConfig = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/config`);
      setConfig(response.data);
    } catch (error) {
      console.error('Error fetching config:', error);
    }
  };

  const toggleFitbit = async () => {
    try {
      await axios.post(`${API_URL}/api/config`, {
        fitbit_enabled: !config.fitbit_enabled
      });
      fetchConfig();
    } catch (error) {
      console.error('Error updating config:', error);
    }
  };

  const chartData = data.slice(0, 20).reverse().map((d, idx) => ({
    index: idx,
    hr: d.mean_hr,
    hrv: d.hrv_rmssd,
    prediction: d.prediction
  }));

  const latestData = data[0] || {};

  return (
    <div className="App">
      <header className="App-header">
        <h1>Smart Alarm Dashboard</h1>
      </header>

      <div className="container">
        <div className="card">
          <h2>Configuration</h2>
          <div className="config-item">
            <span>Fitbit API Status:</span>
            <span className={config.fitbit_enabled ? 'status-enabled' : 'status-disabled'}>
              {config.fitbit_enabled ? 'ENABLED' : 'DISABLED'}
            </span>
          </div>
          <button onClick={toggleFitbit} className="btn">
            {config.fitbit_enabled ? 'Disable' : 'Enable'} Fitbit API
          </button>
          <p className="note">API only queries between 22:00 - 08:00 when enabled</p>
        </div>

        <div className="card">
          <h2>Latest Reading</h2>
          {loading ? (
            <p>Loading...</p>
          ) : latestData.timestamp ? (
            <div className="data-grid">
              <div className="data-item">
                <span className="label">Timestamp:</span>
                <span className="value">{new Date(latestData.timestamp).toLocaleString()}</span>
              </div>
              <div className="data-item">
                <span className="label">Heart Rate:</span>
                <span className="value">{latestData.mean_hr?.toFixed(1)} bpm</span>
              </div>
              <div className="data-item">
                <span className="label">HRV (RMSSD):</span>
                <span className="value">{latestData.hrv_rmssd?.toFixed(1)} ms</span>
              </div>
              <div className="data-item">
                <span className="label">Sleep Stage:</span>
                <span className={`prediction-badge ${latestData.prediction?.toLowerCase()}`}>
                  {latestData.prediction}
                </span>
              </div>
            </div>
          ) : (
            <p>No data available</p>
          )}
        </div>

        <div className="card chart-card">
          <h2>Heart Rate Trend</h2>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="index" label={{ value: 'Time', position: 'insideBottom', offset: -5 }} />
                <YAxis label={{ value: 'Heart Rate (bpm)', angle: -90, position: 'insideLeft' }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="hr" stroke="#8884d8" name="Heart Rate" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p>No data to display</p>
          )}
        </div>

        <div className="card">
          <h2>Recent History</h2>
          <div className="history-table">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>HR</th>
                  <th>HRV</th>
                  <th>Stage</th>
                </tr>
              </thead>
              <tbody>
                {data.slice(0, 10).map((d, idx) => (
                  <tr key={idx}>
                    <td>{d.timestamp ? new Date(d.timestamp).toLocaleTimeString() : 'N/A'}</td>
                    <td>{d.mean_hr?.toFixed(1)}</td>
                    <td>{d.hrv_rmssd?.toFixed(1)}</td>
                    <td>
                      <span className={`prediction-badge ${d.prediction?.toLowerCase()}`}>
                        {d.prediction}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
