/**
 * DeepSleepChart Component
 * Bar chart showing deep sleep minutes over time.
 */
import React from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, 
  Tooltip, ResponsiveContainer 
} from 'recharts';
import Card from '../Card';

export const DeepSleepChart = ({ data }) => {
  if (!data || data.length === 0) return null;

  return (
    <Card title="Deep Sleep Minutes" variant="chart">
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis label={{ value: 'Minutes', angle: -90, position: 'insideLeft' }} />
          <Tooltip />
          <Bar dataKey="deepSleep" fill="#6366f1" name="Deep Sleep" />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
};

export default DeepSleepChart;
