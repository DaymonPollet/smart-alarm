/**
 * ProbabilityBars Component
 * Displays cloud model prediction probabilities.
 */
import React from 'react';
import { getQualityColor } from '../../utils/helpers';
import Card from '../Card';
import './ProbabilityBars.css';

export const ProbabilityBars = ({ probabilities }) => {
  if (!probabilities || Object.keys(probabilities).length === 0) {
    return null;
  }

  return (
    <Card title="Cloud Model Probabilities">
      <div className="probability-bars">
        {Object.entries(probabilities).map(([label, prob]) => (
          <div key={label} className="prob-row">
            <span className="prob-label">{label}</span>
            <div className="prob-bar-container">
              <div 
                className="prob-bar" 
                style={{ 
                  width: `${prob * 100}%`,
                  backgroundColor: getQualityColor(label)
                }}
              />
            </div>
            <span className="prob-value">{(prob * 100).toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </Card>
  );
};

export default ProbabilityBars;
