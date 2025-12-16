/**
 * StatusBadge Component
 * Reusable status indicator with active/inactive states.
 * Implements DRY (Don't Repeat Yourself) principle.
 */
import React from 'react';
import './StatusBadge.css';

export const StatusBadge = ({ 
  label, 
  isActive, 
  activeText = 'Active', 
  inactiveText = 'Inactive' 
}) => (
  <div className="status-item">
    <span className="status-label">{label}</span>
    <span className={`status-indicator ${isActive ? 'active' : 'inactive'}`}>
      {isActive ? activeText : inactiveText}
    </span>
  </div>
);

export default StatusBadge;
