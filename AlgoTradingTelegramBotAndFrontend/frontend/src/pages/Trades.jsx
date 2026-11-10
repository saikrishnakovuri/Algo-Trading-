import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { Search, Download, Filter } from 'lucide-react';

const Trades = () => {
  const [filters, setFilters] = useState({ symbol: '', direction: '', strategy: '' });
  const { data: trades, loading } = useApi(`/api/trades?limit=100&symbol=${filters.symbol}&direction=${filters.direction}&strategy=${filters.strategy}`);

  const handleExport = () => {
    if (!trades) return;
    const headers = ['Date', 'Symbol', 'Dir', 'Entry', 'Exit', 'PnL', 'Strategy'];
    const csv = [
      headers.join(','),
      ...trades.map(t => [
        t.timestamp,
        t.symbol,
        t.direction,
        t.entry_price,
        t.exit_price || 'N/A',
        t.pnl_abs || 0,
        t.strategy_name
      ].join(','))
    ].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `trades_export_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-white">Trade History</h2>
        <button 
          onClick={handleExport}
          className="flex items-center gap-2 bg-[#1e2130] hover:bg-[#2a2f42] text-gray-300 px-4 py-2 rounded-lg transition-colors border border-[#30364d]"
        >
          <Download size={18} /> Export CSV
        </button>
      </div>

      {/* Filter Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 bg-[#161b27] p-4 rounded-xl border border-[#1e2130]">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={16} />
          <input 
            type="text" 
            placeholder="Search symbol..." 
            className="w-full bg-[#0f1117] border border-[#1e2130] rounded-lg py-2 pl-10 pr-4 text-sm text-white focus:outline-none focus:border-[#00bcd4]"
            onChange={(e) => setFilters({...filters, symbol: e.target.value})}
          />
        </div>
        <select 
          className="bg-[#0f1117] border border-[#1e2130] rounded-lg py-2 px-4 text-sm text-white focus:outline-none focus:border-[#00bcd4]"
          onChange={(e) => setFilters({...filters, direction: e.target.value})}
        >
          <option value="">All Directions</option>
          <option value="BUY">BUY</option>
          <option value="SELL">SELL</option>
        </select>
        <select 
          className="bg-[#0f1117] border border-[#1e2130] rounded-lg py-2 px-4 text-sm text-white focus:outline-none focus:border-[#00bcd4]"
          onChange={(e) => setFilters({...filters, strategy: e.target.value})}
        >
          <option value="">All Strategies</option>
          <option value="VWAP_BOUNCE">VWAP Bounce</option>
          <option value="MOMENTUM_BREAKOUT">Momentum Breakout</option>
        </select>
        <div className="flex items-center gap-2 text-gray-500 text-xs px-2 font-mono uppercase">
          <Filter size={14} /> {trades?.length || 0} Trades found
        </div>
      </div>

      {/* Trades Table */}
      <div className="bg-[#161b27] border border-[#1e2130] rounded-xl overflow-hidden">
        <table className="w-full text-left border-collapse font-mono text-sm">
          <thead>
            <tr className="bg-[#1e2130] text-gray-400 uppercase text-[10px] tracking-widest">
              <th className="px-6 py-4 font-bold">Timestamp</th>
              <th className="px-6 py-4 font-bold">Symbol</th>
              <th className="px-6 py-4 font-bold">Dir</th>
              <th className="px-6 py-4 font-bold">Entry</th>
              <th className="px-6 py-4 font-bold">Exit</th>
              <th className="px-6 py-4 font-bold text-right">PnL (₹)</th>
              <th className="px-6 py-4 font-bold">Strategy</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1e2130]">
            {loading ? (
              <tr><td colSpan="7" className="px-6 py-12 text-center text-gray-600 animate-pulse italic">Loading history...</td></tr>
            ) : trades?.length > 0 ? trades.map((t, i) => (
              <tr key={i} className="hover:bg-[#1e2130]/30 transition-colors">
                <td className="px-6 py-4 text-gray-500 text-xs whitespace-nowrap">{t.timestamp}</td>
                <td className="px-6 py-4 font-bold text-white">{t.symbol}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${t.direction === 'BUY' ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
                    {t.direction}
                  </span>
                </td>
                <td className="px-6 py-4 text-gray-300">₹{t.entry_price?.toLocaleString()}</td>
                <td className="px-6 py-4 text-gray-300">{t.exit_price ? `₹${t.exit_price.toLocaleString()}` : '—'}</td>
                <td className={`px-6 py-4 text-right font-bold ${t.pnl_abs >= 0 ? 'text-[#00c853]' : 'text-[#ff1744]'}`}>
                  {t.pnl_abs ? `₹${t.pnl_abs.toLocaleString()}` : '—'}
                </td>
                <td className="px-6 py-4 text-gray-500">{t.strategy_name}</td>
              </tr>
            )) : (
              <tr><td colSpan="7" className="px-6 py-12 text-center text-gray-600 italic">No trades matching current filters.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Trades;
