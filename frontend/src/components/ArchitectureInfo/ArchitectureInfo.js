/**
 * ArchitectureInfo Component
 * Displays system architecture documentation.
 */
import React from 'react';
import Card from '../Card';
import { QUALITY_THRESHOLDS } from '../../utils/helpers';
import './ArchitectureInfo.css';

export const ArchitectureInfo = () => {
  return (
    <Card title="System Architecture">
      <div className="architecture-info">
        <div className="arch-section">
          <h3>Local Model (Edge)</h3>
          <p>Random Forest Regression predicting sleep quality score (0-100).</p>
          <p>Features: revitalization, deep sleep, resting HR, restlessness, time features, lagged values.</p>
          <p>Always available for immediate predictions.</p>
        </div>
        <div className="arch-section">
          <h3>Cloud Model (Azure ML)</h3>
          <p>Random Forest Classifier predicting quality class (Poor/Fair/Good).</p>
          <p>Enhanced model with class probabilities.</p>
          <p>Falls back to local model when offline.</p>
        </div>
        <div className="arch-section">
          <h3>Data Pipeline</h3>
          <p>MQTT: Publishes predictions for IoT edge devices.</p>
          <p>SQLite: Stores predictions locally when cloud is unavailable.</p>
          <p>Auto-sync: Pending predictions sync when cloud reconnects.</p>
        </div>
      </div>
      <div className="quality-legend">
        <p><strong>Quality Thresholds:</strong></p>
        <div className="quality-badges">
          {QUALITY_THRESHOLDS.map(({ label, min, color }) => (
            <span 
              key={label}
              style={{ 
                backgroundColor: color, 
                color: 'white', 
                padding: '3px 10px', 
                borderRadius: '10px', 
                margin: '0 5px' 
              }}
            >
              {label} ({min === 0 ? `<55` : `${min}+`})
            </span>
          ))}
        </div>
      </div>
    </Card>
  );
};

export default ArchitectureInfo;
