/**
 * AlarmPopup Component
 * Full-screen alarm notification with snooze and dismiss options.
 */
import React from 'react';
import './AlarmPopup.css';

export const AlarmPopup = ({ 
  triggerReason, 
  onSnooze, 
  onDismiss 
}) => {
  const getMessage = () => {
    if (triggerReason === 'light_sleep_detected') {
      return 'Light sleep detected - optimal wake time!';
    }
    return 'Your alarm time has been reached';
  };

  return (
    <div className="alarm-popup-overlay">
      <div className="alarm-popup">
        <h2>⏰ Wake Up!</h2>
        <p className="alarm-message">{getMessage()}</p>
        <p className="alarm-time">{new Date().toLocaleTimeString()}</p>
        <div className="alarm-buttons">
          <button onClick={onSnooze} className="btn btn-warning">
            Snooze (9 min)
          </button>
          <button onClick={onDismiss} className="btn btn-success">
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
};

export default AlarmPopup;
