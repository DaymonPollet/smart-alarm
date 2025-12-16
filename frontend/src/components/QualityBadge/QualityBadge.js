/**
 * QualityBadge Component
 * Displays sleep quality with color-coded styling.
 */
import React from 'react';
import { getQualityColor } from '../../utils/helpers';
import './QualityBadge.css';

export const QualityBadge = ({ 
  quality, 
  size = 'medium',
  showLabel = false,
  label = ''
}) => {
  const sizeClass = `quality-badge--${size}`;
  
  return (
    <span 
      className={`quality-badge ${sizeClass}`}
      style={{ backgroundColor: getQualityColor(quality) }}
    >
      {showLabel && label && <span className="quality-badge__label">{label}: </span>}
      {quality?.toUpperCase() || 'N/A'}
    </span>
  );
};

export default QualityBadge;
