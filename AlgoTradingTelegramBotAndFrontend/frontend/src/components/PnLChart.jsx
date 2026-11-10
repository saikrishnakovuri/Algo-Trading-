import React from 'react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';

const PnLChart = ({ data, height = 300 }) => {
  const chartData = Array.isArray(data) ? data : [];
  
  return (
    <div className="bg-[#161b27] border border-[#1e2130] p-6 rounded-xl" style={{ height }}>
      <h3 className="text-gray-400 text-xs font-bold uppercase mb-6 tracking-widest">Performance History</h3>
      <div className="w-full h-full pb-8">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorPnL" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#00c853" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#00c853" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2130" vertical={false} />
            <XAxis 
              dataKey="date" 
              stroke="#4b5563" 
              fontSize={10} 
              tickLine={false} 
              axisLine={false} 
            />
            <YAxis 
              stroke="#4b5563" 
              fontSize={10} 
              tickLine={false} 
              axisLine={false} 
              tickFormatter={(value) => `₹${value.toLocaleString()}`}
            />
            <Tooltip 
              contentStyle={{ backgroundColor: '#161b27', border: '1px solid #1e2130', borderRadius: '8px' }}
              itemStyle={{ color: '#00c853' }}
              formatter={(value) => [`₹${value.toLocaleString()}`, 'Cumulative PnL']}
            />
            <Area 
              type="monotone" 
              dataKey="cumulative_pnl" 
              stroke="#00c853" 
              fillOpacity={1} 
              fill="url(#colorPnL)" 
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default PnLChart;
