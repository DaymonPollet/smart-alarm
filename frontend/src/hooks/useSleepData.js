/**
 * Custom Hook: useSleepData
 * Manages sleep data fetching and state.
 * Implements the Custom Hooks pattern for reusable stateful logic.
 */
import { useState, useEffect, useCallback } from 'react';
import { sleepService } from '../services/api';

export const useSleepData = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const response = await sleepService.getData();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching sleep data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Transform data for charts
  const chartData = data.slice(0, 20).reverse().map((d, idx) => ({
    index: idx + 1,
    score: d.overall_score || d.local_score || 0,
    efficiency: d.efficiency || 0,
    deepSleep: d.deep_sleep_minutes || 0,
    date: d.timestamp ? new Date(d.timestamp).toLocaleDateString() : '',
  }));

  const latestData = data[0] || {};

  return {
    data,
    chartData,
    latestData,
    loading,
    error,
    refetch: fetchData,
  };
};

export default useSleepData;
