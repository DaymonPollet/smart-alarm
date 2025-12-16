/**
 * SleepHistory Component
 * Table displaying sleep session history with quality comparisons.
 */
import React from 'react';
import { getQualityColor, formatDate } from '../../utils/helpers';
import Card from '../Card';
import './SleepHistory.css';

export const SleepHistory = ({ data, limit = 15 }) => {
  return (
    <Card title="Sleep History">
      <div className="history-table">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Duration</th>
              <th>Efficiency</th>
              <th>Deep Sleep</th>
              <th>Local</th>
              <th>Cloud</th>
              <th>Final</th>
            </tr>
          </thead>
          <tbody>
            {data.length > 0 ? (
              data.slice(0, limit).map((d, idx) => (
                <tr key={idx} className={d.is_main_sleep ? 'main-sleep' : ''}>
                  <td>{formatDate(d.timestamp)}</td>
                  <td>{d.duration_hours?.toFixed(1) || '-'} hrs</td>
                  <td>{d.efficiency || '-'}%</td>
                  <td>{d.deep_sleep_minutes || '-'} min</td>
                  <td>
                    <span 
                      className="quality-badge-small"
                      style={{ 
                        backgroundColor: getQualityColor(d.local_quality), 
                        color: 'white', 
                        padding: '2px 6px', 
                        borderRadius: '8px', 
                        fontSize: '0.8em' 
                      }}
                    >
                      {d.local_quality?.toUpperCase() || '-'}
                    </span>
                  </td>
                  <td>
                    {d.cloud_quality ? (
                      <span 
                        className="quality-badge-small"
                        style={{ 
                          backgroundColor: getQualityColor(d.cloud_quality), 
                          color: 'white', 
                          padding: '2px 6px', 
                          borderRadius: '8px', 
                          fontSize: '0.8em' 
                        }}
                      >
                        {d.cloud_quality?.toUpperCase()}
                      </span>
                    ) : (
                      <span style={{ color: '#999', fontSize: '0.8em' }}>-</span>
                    )}
                  </td>
                  <td>
                    <span 
                      className="quality-badge-small"
                      style={{ 
                        backgroundColor: getQualityColor(d.quality), 
                        color: 'white', 
                        padding: '2px 8px', 
                        borderRadius: '10px', 
                        fontSize: '0.85em', 
                        fontWeight: 'bold' 
                      }}
                    >
                      {d.quality?.toUpperCase() || 'N/A'}
                    </span>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', padding: '20px' }}>
                  No sleep data available. Connect Fitbit and fetch your sleep history.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
};

export default SleepHistory;
