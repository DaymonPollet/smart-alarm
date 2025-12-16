/**
 * Helper Utilities
 * Shared utility functions used across components.
 */

/**
 * Get color based on sleep quality level
 * @param {string} quality - Quality level (excellent, good, fair, poor)
 * @returns {string} Hex color code
 */
export const getQualityColor = (quality) => {
  switch (quality?.toLowerCase()) {
    case 'excellent':
      return '#28a745';
    case 'good':
      return '#5cb85c';
    case 'fair':
      return '#f0ad4e';
    case 'poor':
      return '#d9534f';
    default:
      return '#6c757d';
  }
};

/**
 * Format timestamp to locale date string
 * @param {string} timestamp - ISO timestamp
 * @returns {string} Formatted date
 */
export const formatDate = (timestamp) => {
  if (!timestamp) return 'N/A';
  return new Date(timestamp).toLocaleDateString();
};

/**
 * Format timestamp to locale time string
 * @param {string} timestamp - ISO timestamp
 * @returns {string} Formatted time
 */
export const formatTime = (timestamp) => {
  if (!timestamp) return 'N/A';
  return new Date(timestamp).toLocaleTimeString();
};

/**
 * Format number with fixed decimal places
 * @param {number} value - Number to format
 * @param {number} decimals - Decimal places
 * @returns {string} Formatted number or 'N/A'
 */
export const formatNumber = (value, decimals = 1) => {
  if (value === null || value === undefined) return 'N/A';
  return value.toFixed(decimals);
};

/**
 * Quality thresholds for reference
 */
export const QUALITY_THRESHOLDS = [
  { label: 'Excellent', min: 85, color: '#28a745' },
  { label: 'Good', min: 70, color: '#5cb85c' },
  { label: 'Fair', min: 55, color: '#f0ad4e' },
  { label: 'Poor', min: 0, color: '#d9534f' },
];
