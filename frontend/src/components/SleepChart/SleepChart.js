/**
 * SleepChart Component
 * Displays sleep quality trends over time.
 */
import React from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, 
  Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
import Card from '../Card';
import './SleepChart.css';

export const SleepChart = ({ data }) => {
  if (!data || data.length === 0) return null;

  return (
    <Card title="Sleep Quality Trend" variant="chart">
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis 
            domain={[0, 100]} 
            label={{ value: 'Score', angle: -90, position: 'insideLeft' }} 
          />
          <Tooltip />
          <Legend />
          <Line 
            type="monotone" 
            dataKey="score" 
            stroke="#8884d8" 
            strokeWidth={2} 
            name="Quality Score" 
            dot={{ r: 4 }} 
          />
          <Line 
            type="monotone" 
            dataKey="efficiency" 
            stroke="#82ca9d" 
            strokeWidth={2} 
            name="Efficiency %" 
            dot={{ r: 4 }} 
          />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
};

export default SleepChart;
