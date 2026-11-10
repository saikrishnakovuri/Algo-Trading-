import React from 'react';
import { Link } from "react-router-dom";
import { useApi } from '../hooks/useApi';
import StatCard from '../components/StatCard';
import PnLChart from '../components/PnLChart';
import { 
  Zap, 
  TrendingUp, 
  Wallet, 
  Activity,
  Target,
  AlertTriangle
} from 'lucide-react';

const Dashboard = () => {
  const { data: status } = useApi('/api/live/status', 5000);
  const { data: summary } = useApi('/api/analytics/summary', 10000);
  const { data: pnlHistory } = useApi('/api/analytics/pnl-history', 10000);
  const { data: signals } = useApi('/api/live/signals', 5000);

  // Safe numeric formatting
  const formatValue = (val) => {
    if (val === undefined || val === null) return '0';
    return Number(val).toLocaleString();
  };

  if (!status || !summary) return <div className="p-8 text-gray-500 animate-pulse">Loading live dashboard...</div>;

  const lastUpdate = status.last_update ? new Date(status.last_update) : null;
  const timeStr = lastUpdate && !isNaN(lastUpdate.getTime()) ? lastUpdate.toLocaleTimeString() : 'N/A';

  return (
    <div className="p-8 space-y-8">
      
      {/* Quick Links for Integration Visibility */}
      <div className="flex flex-wrap gap-4 mb-4">
        <Link to="/control-center" className="px-4 py-2 bg-[#00bcd4]/10 border border-[#00bcd4]/30 rounded-lg text-[#00bcd4] text-xs font-bold hover:bg-[#00bcd4]/20 transition-all">CONTROL CENTER</Link>
        <Link to="/pa-engine" className="px-4 py-2 bg-purple-500/10 border border-purple-500/30 rounded-lg text-purple-400 text-xs font-bold hover:bg-purple-500/20 transition-all">PA ENGINE</Link>
        <Link to="/journal" className="px-4 py-2 bg-green-500/10 border border-green-500/30 rounded-lg text-green-400 text-xs font-bold hover:bg-green-500/20 transition-all">TRADE JOURNAL</Link>
        <Link to="/backtest" className="px-4 py-2 bg-orange-500/10 border border-orange-500/30 rounded-lg text-orange-400 text-xs font-bold hover:bg-orange-500/20 transition-all">RUN BACKTEST</Link>
        <Link to="/config-explorer" className="px-4 py-2 bg-blue-500/10 border border-blue-500/30 rounded-lg text-blue-400 text-xs font-bold hover:bg-blue-500/20 transition-all">CONFIG EXPLORER</Link>
      </div>

      {/* Top row stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard 
          title="Total Trades" 
          value={summary.total_trades || 0} 
          subValue={`Wins: ${summary.wins || 0} | Losses: ${summary.losses || 0}`}
          icon={<Zap size={20} />} 
        />
        <StatCard 
          title="Win Rate" 
          value={`${summary.win_rate || 0}%`} 
          subValue="Last 30 days"
          icon={<Target size={20} />}
          color={summary.win_rate >= 50 ? 'green' : 'yellow'}
        />
        <StatCard 
          title="Total PnL" 
          value={`₹${formatValue(summary.total_pnl)}`} 
          subValue="Net Realized"
          icon={<TrendingUp size={20} />}
          color={summary.total_pnl >= 0 ? 'green' : 'red'}
        />
        <StatCard 
          title="Bot Status" 
          value={status.status || 'INACTIVE'} 
          subValue={`Last heartbeat: ${timeStr}`}
          icon={<Activity size={20} />}
          color={status.status === 'ACTIVE' ? 'green' : 'red'}
        />
      </div>

      {/* Second row: Market Context */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-[#161b27] border border-[#1e2130] p-6 rounded-xl space-y-4">
          <h3 className="text-gray-400 text-xs font-bold uppercase tracking-widest">Market Context</h3>
          <div className="flex justify-between items-center">
            <span className="text-gray-500">Regime</span>
            <span className={`px-3 py-1 rounded-full text-[10px] font-bold ${
              status.regime === 'TRENDING_UP' ? 'bg-green-500/10 text-green-500' :
              status.regime === 'TRENDING_DOWN' ? 'bg-red-500/10 text-red-500' : 
              status.regime === 'CHOPPY' ? 'bg-yellow-500/10 text-yellow-500' : 'bg-blue-500/10 text-blue-500'
            }`}>{status.regime}</span>
          </div>
          <div className="flex justify-between items-center text-xs">
            <span className="text-gray-500">Volatility</span>
            <span className="text-white font-medium uppercase">{status.volatility || 'Normal'}</span>
          </div>
          <div className="flex justify-between items-center text-xs">
            <span className="text-gray-500">Structure</span>
            <span className="text-white font-medium uppercase">{status.structure || 'None'}</span>
          </div>
          <div className="pt-2">
            <p className="text-[9px] text-gray-500 font-bold uppercase mb-2">Enabled Strategies</p>
            <div className="flex flex-wrap gap-1">
              {['VWAP', 'BREAKOUT', 'SMC', 'SWEEP', 'REVERSION'].map(s => (
                <span key={s} className="px-1.5 py-0.5 bg-[#1e2130] text-gray-400 text-[8px] rounded border border-[#30364d]">{s}</span>
              ))}
            </div>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-500">India VIX</span>
            <span className="text-[#00bcd4] font-mono font-bold">
              {typeof status.vix === 'number' ? status.vix.toFixed(2) : (status.vix_state || status.vix || 'NORMAL')}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-gray-500">Trades Today</span>
            <span className="text-white font-mono">{status.trades_today} / 5</span>
          </div>
          <div className="pt-4 border-t border-[#1e2130]">
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-500">Capital</span>
              <span className="text-white font-bold">₹{status.capital?.toLocaleString()}</span>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2">
          <PnLChart data={pnlHistory || []} height={220} />
        </div>
      </div>

      {/* Third row: Recent Signals & Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[#161b27] border border-[#1e2130] p-6 rounded-xl">
          <h3 className="text-gray-400 text-xs font-bold uppercase tracking-widest mb-6">Recent Signals</h3>
          <div className="space-y-4 max-h-80 overflow-y-auto pr-2">
            {signals?.map((s, i) => (
              <div key={i} className="bg-[#0f1117] p-4 rounded-lg border-l-4 border-[#00bcd4] flex justify-between items-center">
                <div>
                  <div className="font-bold text-white">{s.symbol} {s.direction} <span className="text-gray-600 text-[10px] ml-2 font-normal">{new Date(s.created_at).toLocaleTimeString()}</span></div>
                  <div className="text-xs text-gray-500">{s.strategy} | Conf: {s.confidence}%</div>
                </div>
                <div className="text-right">
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${s.action === 'TAKEN' ? 'bg-green-500/10 text-green-500' : 'bg-yellow-500/10 text-yellow-500'}`}>
                    {s.action}
                  </span>
                </div>
              </div>
            ))}
            {(!signals || signals.length === 0) && <div className="text-center py-8 text-gray-600 italic text-sm">Waiting for market signals...</div>}
          </div>
        </div>

        <div className="bg-[#161b27] border border-[#1e2130] p-6 rounded-xl">
          <h3 className="text-gray-400 text-xs font-bold uppercase tracking-widest mb-6">Risk Alerts</h3>
          <div className="space-y-4">
            <div className="flex gap-4 p-4 bg-red-500/5 border border-red-500/20 rounded-lg">
              <AlertTriangle className="text-red-500 flex-shrink-0" size={20} />
              <div>
                <p className="text-sm font-bold text-red-500">Daily Loss Limit</p>
                <p className="text-xs text-gray-400">Bot will pause if daily loss exceeds ₹30,000 (3%)</p>
              </div>
            </div>
            <div className="flex gap-4 p-4 bg-yellow-500/5 border border-yellow-500/20 rounded-lg">
              <AlertTriangle className="text-yellow-500 flex-shrink-0" size={20} />
              <div>
                <p className="text-sm font-bold text-yellow-500">Max Trades Warning</p>
                <p className="text-xs text-gray-400">Approaching maximum allowed trades (4/5 taken)</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
