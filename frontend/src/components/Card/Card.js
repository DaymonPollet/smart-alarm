/**
 * Card Component
 * Reusable card container with optional variants.
 */
import React from 'react';
import './Card.css';

export const Card = ({ 
  title, 
  children, 
  variant = 'default',
  className = ''
}) => {
  const variantClass = variant !== 'default' ? `card--${variant}` : '';
  
  return (
    <div className={`card ${variantClass} ${className}`}>
      {title && <h2>{title}</h2>}
      {children}
    </div>
  );
};

export default Card;
