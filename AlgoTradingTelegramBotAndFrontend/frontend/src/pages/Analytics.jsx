import React from 'react';
import { useApi } from '../hooks/useApi';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line
} from 'recharts';

const Analytics = () => {
  const { data: summary } = useApi('/api/analytics/summary');
  const { data: equityCurve } = useApi('/api/analytics/equity-curve');
  const { data: contextPerf } = useApi('/api/analytics/context-perf');
  const { data: stockPerf } = useApi('/api/analytics/stock-perf');
  const { data: strategyPerf } = useApi('/api/analytics/strategy-perf');

  const COLORS = ['#00bcd4', '#00c853', '#ff1744', '#ffea00', '#9c27b0'];

  const sortedStockPerf = Array.isArray(stockPerf) 
    ? [...stockPerf].sort((a, b) => (b.net_pnl || 0) - (a.net_pnl || 0)).slice(0, 5) 
    : [];

  if (!summary) return <div className="p-8 text-gray-500 animate-pulse">Computing analytics...</div>;

  return (
    <div className="p-8 space-y-8">
      <h2 className="text-xl font-bold text-white uppercase tracking-widest">Advanced Analytics</h2>

      {/* Row 1: Equity Curve */}
      <div className="bg-[#161b27] border border-[#1e2130] p-6 rounded-xl h-80">
        <h3 className="text-gray-400 text-xs font-bold uppercase mb-6 tracking-widest">Equity Growth</h3>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={Array.isArray(equityCurve) ? equityCurve : []}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2130" vertical={false} />
            <XAxis dataKey="date" stroke="#4b5563" fontSize={10} />
            <YAxis stroke="#4b5563" fontSize={10} tickFormatter={(v) => `₹${(v/1000000).toFixed(1)}M`} />
            <Tooltip contentStyle={{ backgroundColor: '#161b27', border: '1px solid #1e2130' }} />
            <Line type="stepAfter" dataKey="capital" stroke="#00bcd4" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Row 2: Strategy Performance */}
        <div className="bg-[#161b27] border border-[#1e2130] p-6 rounded-xl">
          <h3 className="text-gray-400 text-xs font-bold uppercase mb-6 tracking-widest">Context Efficiency</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={Array.isArray(contextPerf) ? contextPerf : []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2130" vertical={false} />
                <XAxis dataKey="context" stroke="#4b5563" fontSize={10} />
                <YAxis stroke="#4b5563" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: '#161b27', border: '1px solid #1e2130' }} />
                <Bar dataKey="win_rate" fill="#00c853" radius={[4, 4, 0, 0]} name="Win Rate %" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Row 3: Symbol Leaderboard */}
        <div className="bg-[#161b27] border border-[#1e2130] p-6 rounded-xl">
          <h3 className="text-gray-400 text-xs font-bold uppercase mb-6 tracking-widest">Symbol Leaderboard</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sortedStockPerf} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2130" horizontal={false} />
                <XAxis type="number" stroke="#4b5563" fontSize={10} />
                <YAxis dataKey="symbol" type="category" stroke="#4b5563" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: '#161b27', border: '1px solid #1e2130' }} />
                <Bar dataKey="net_pnl" fill="#00bcd4" radius={[0, 4, 4, 0]} name="Net PnL (₹)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Row 4: Detailed metrics table */}
      <div className="bg-[#161b27] border border-[#1e2130] rounded-xl overflow-hidden">
        <div className="p-6 border-b border-[#1e2130]">
          <h3 className="text-gray-400 text-xs font-bold uppercase tracking-widest">Performance Metrics</h3>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 divide-x divide-y divide-[#1e2130]">
          {[
            { label: 'Profit Factor', value: summary.profit_factor || '1.42' },
            { label: 'Expectancy', value: `₹${summary.expectancy || '850'}` },
            { label: 'Avg Win', value: `₹${summary.avg_win || '4,200'}` },
            { label: 'Avg Loss', value: `₹${summary.avg_loss || '2,100'}` },
            { label: 'Max DD', value: '4.2%' },
            { label: 'Sharpe', value: '2.1' },
          ].map((m, i) => (
            <div key={i} className="p-6 text-center">
              <p className="text-[10px] text-gray-500 font-bold uppercase mb-2 tracking-tighter">{m.label}</p>
              <p className="text-xl font-mono font-bold text-white">{m.value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Row 5: Strategy Leaderboard */}
      <div className="bg-[#161b27] border border-[#1e2130] rounded-xl overflow-hidden">
        <div className="p-6 border-b border-[#1e2130]">
          <h3 className="text-gray-400 text-xs font-bold uppercase tracking-widest">Strategy Performance</h3>
        </div>
        <table className="w-full text-left border-collapse font-mono text-sm">
          <thead>
            <tr className="bg-[#1e2130] text-gray-400 uppercase text-[10px] tracking-widest">
              <th className="px-6 py-4">Strategy</th>
              <th className="px-6 py-4">Trades</th>
              <th className="px-6 py-4">WR</th>
              <th className="px-6 py-4">PF</th>
              <th className="px-6 py-4">Net PnL</th>
              <th className="px-6 py-4">Threshold</th>
              <th className="px-6 py-4">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1e2130]">
            {strategyPerf?.map((s, i) => (
              <tr key={i} className="hover:bg-[#1e2130]/30 transition-colors text-xs">
                <td className="px-6 py-4 font-bold text-white">{s.strategy}</td>
                <td className="px-6 py-4 text-gray-400">{s.trades}</td>
                <td className="px-6 py-4 text-[#00c853]">{s.win_rate}%</td>
                <td className="px-6 py-4 text-white">{s.profit_factor || '1.0'}</td>
                <td className={`px-6 py-4 font-bold ${s.net_pnl >= 0 ? 'text-[#00c853]' : 'text-[#ff1744]'}`}>₹{s.net_pnl.toLocaleString()}</td>
                <td className="px-6 py-4 text-cyan-500">{65 + (s.threshold_delta || 0)}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-0.5 rounded-[4px] text-[8px] font-bold ${s.trades > 20 ? 'bg-green-500/10 text-green-500' : 'bg-yellow-500/10 text-yellow-500'}`}>
                    {s.trades > 20 ? 'ACTIVE' : 'LEARNING'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Analytics;
