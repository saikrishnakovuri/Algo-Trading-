import React, { useState, useEffect } from 'react';
import api, { useApi } from '../hooks/useApi';
import { 
  Play, 
  History, 
  Settings2, 
  TrendingUp,
  AlertCircle,
  CheckCircle2
} from 'lucide-react';

const Backtesting = () => {
  const { data: history, refetch: refetchHistory } = useApi('/api/backtest/history', 10000);
  const [activeJobId, setActiveJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [result, setResult] = useState(null);

  const [config, setConfig] = useState({
    stocks: ['NIFTY'],
    start_date: '2025-11-01',
    end_date: '2026-01-31',
    entry_strategy: 'VWAP_BOUNCE',
    sl_type: 'ATR_2',
    tp_type: 'FIX_2R',
    capital: 1000000,
    risk_pct: 1.0
  });

  const handleRun = async () => {
    try {
      const resp = await api.post('/api/backtest/run', config);
      setActiveJobId(resp.data.job_id);
      setResult(null);
    } catch (err) {
      alert(`Failed to start backtest: ${err.message}`);
    }
  };

  useEffect(() => {
    let interval;
    if (activeJobId) {
      interval = setInterval(async () => {
        try {
          const resp = await api.get(`/api/backtest/status/${activeJobId}`);
          if (resp.data) {
            setJobStatus(resp.data);
            if (resp.data.status === 'COMPLETED') {
              const resResp = await api.get(`/api/backtest/result/${activeJobId}`);
              if (resResp.data) {
                setResult(resResp.data.result);
              }
              setActiveJobId(null);
              refetchHistory();
            } else if (resp.data.status === 'FAILED') {
              setActiveJobId(null);
            }
          }
        } catch (err) {
          console.error(err);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [activeJobId, refetchHistory]);

  return (
    <div className="p-8 space-y-8">
      <h2 className="text-xl font-bold text-white uppercase tracking-widest">Strategy Backtesting</h2>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Config Panel */}
        <div className="bg-[#161b27] border border-[#1e2130] p-6 rounded-xl space-y-6 h-fit">
          <h3 className="text-white font-bold flex items-center gap-2 uppercase tracking-widest text-xs">
            <Settings2 size={16} className="text-[#00bcd4]" /> Configuration
          </h3>
          
          <div className="space-y-4">
            <div className="space-y-1">
              <label className="text-[10px] text-gray-500 uppercase font-bold">Universe</label>
              <div className="flex gap-2">
                {['NIFTY', 'BANKNIFTY'].map(s => (
                  <button 
                    key={s}
                    onClick={() => setConfig({...config, stocks: config.stocks.includes(s) ? config.stocks.filter(x => x!==s) : [...config.stocks, s]})}
                    className={`px-3 py-1 rounded text-[10px] font-bold border transition-all ${config.stocks.includes(s) ? 'bg-[#00bcd4]/10 border-[#00bcd4] text-[#00bcd4]' : 'bg-[#0f1117] border-[#1e2130] text-gray-500'}`}
                  >{s}</button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-[10px] text-gray-500 uppercase font-bold">Start Date</label>
                <input type="date" value={config.start_date} className="w-full bg-[#0f1117] border border-[#1e2130] rounded p-2 text-xs text-white" onChange={(e)=>setConfig({...config, start_date: e.target.value})} />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] text-gray-500 uppercase font-bold">End Date</label>
                <input type="date" value={config.end_date} className="w-full bg-[#0f1117] border border-[#1e2130] rounded p-2 text-xs text-white" onChange={(e)=>setConfig({...config, end_date: e.target.value})} />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-[10px] text-gray-500 uppercase font-bold">Strategy</label>
              <select className="w-full bg-[#0f1117] border border-[#1e2130] rounded p-2 text-xs text-white" value={config.entry_strategy} onChange={(e)=>setConfig({...config, entry_strategy: e.target.value})}>
                <option value="VWAP_BOUNCE">VWAP Bounce</option>
                <option value="MOMENTUM_BREAKOUT">Momentum Breakout</option>
                <option value="LIQUIDITY_TRAP">Liquidity Trap</option>
                <option value="EMA_CROSSOVER">EMA Crossover</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-[10px] text-gray-500 uppercase font-bold">SL Type</label>
                <select className="w-full bg-[#0f1117] border border-[#1e2130] rounded p-2 text-xs text-white" value={config.sl_type} onChange={(e)=>setConfig({...config, sl_type: e.target.value})}>
                  <option value="ATR_1">ATR 1x</option>
                  <option value="ATR_2">ATR 2x</option>
                  <option value="EMA20">EMA 20</option>
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-[10px] text-gray-500 uppercase font-bold">TP Type</label>
                <select className="w-full bg-[#0f1117] border border-[#1e2130] rounded p-2 text-xs text-white" value={config.tp_type} onChange={(e)=>setConfig({...config, tp_type: e.target.value})}>
                  <option value="FIX_1.5R">Fixed 1.5R</option>
                  <option value="FIX_2R">Fixed 2.0R</option>
                  <option value="TRAIL_ATR">Trailing ATR</option>
                </select>
              </div>
            </div>

            <button 
              onClick={handleRun}
              disabled={!!activeJobId}
              className={`w-full py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-all ${activeJobId ? 'bg-gray-700 text-gray-500 cursor-not-allowed' : 'bg-[#00bcd4] hover:bg-[#00acc1] text-black shadow-lg shadow-[#00bcd4]/10'}`}
            >
              {activeJobId ? <RefreshCw className="animate-spin" size={18} /> : <Play size={18} fill="currentColor" />}
              {activeJobId ? 'ENGINE RUNNING...' : 'START BACKTEST'}
            </button>
          </div>
        </div>

        {/* Results Panel */}
        <div className="lg:col-span-2 space-y-6">
          {jobStatus && (
            <div className={`p-4 rounded-xl border flex items-center gap-4 ${jobStatus.status === 'RUNNING' ? 'bg-[#00bcd4]/5 border-[#00bcd4]/20' : jobStatus.status === 'FAILED' ? 'bg-red-500/5 border-red-500/20' : 'bg-green-500/5 border-green-500/20'}`}>
              {jobStatus.status === 'RUNNING' ? <Activity className="text-[#00bcd4] animate-pulse" /> : jobStatus.status === 'FAILED' ? <AlertCircle className="text-red-500" /> : <CheckCircle2 className="text-green-500" />}
              <div className="flex-1">
                <p className="text-white text-sm font-bold">Job {jobStatus.status}</p>
                <div className="w-full bg-[#0f1117] h-1.5 rounded-full mt-2 overflow-hidden">
                  <div className="bg-[#00bcd4] h-full transition-all duration-500" style={{ width: `${jobStatus.progress_pct}%` }}></div>
                </div>
              </div>
              <span className="text-[10px] font-mono text-gray-500">{jobStatus.progress_pct}%</span>
            </div>
          )}

          {result ? (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-[#161b27] border border-[#1e2130] p-4 rounded-xl text-center">
                  <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">Total Trades</p>
                  <p className="text-xl font-bold text-white">{result?.metrics?.total_trades || 0}</p>
                </div>
                <div className="bg-[#161b27] border border-[#1e2130] p-4 rounded-xl text-center">
                  <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">Win Rate</p>
                  <p className="text-xl font-bold text-[#00c853]">{result?.metrics?.win_rate || 0}%</p>
                </div>
                <div className="bg-[#161b27] border border-[#1e2130] p-4 rounded-xl text-center">
                  <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">Total PnL</p>
                  <p className={`text-xl font-bold ${(result?.metrics?.total_pnl || 0) >= 0 ? 'text-[#00c853]' : 'text-[#ff1744]'}`}>₹{(result?.metrics?.total_pnl || 0).toLocaleString()}</p>
                </div>
                <div className="bg-[#161b27] border border-[#1e2130] p-4 rounded-xl text-center">
                  <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">Profit Factor</p>
                  <p className="text-xl font-bold text-[#00bcd4]">{result?.metrics?.profit_factor || 0}</p>
                </div>
              </div>

              <div className="bg-[#161b27] border border-[#1e2130] p-6 rounded-xl">
                <h4 className="text-gray-400 text-[10px] font-bold uppercase mb-4 tracking-widest">Recent Backtest Trades</h4>
                <div className="max-h-64 overflow-y-auto font-mono text-xs">
                  <table className="w-full text-left">
                    <thead className="sticky top-0 bg-[#161b27] text-gray-600 border-b border-[#1e2130]">
                      <tr>
                        <th className="pb-2">Time</th>
                        <th className="pb-2">Symbol</th>
                        <th className="pb-2">Entry</th>
                        <th className="pb-2">Exit</th>
                        <th className="pb-2 text-right">PnL</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1e2130]/50">
                      {result.trades.slice(0, 50).map((t, i) => (
                        <tr key={i}>
                          <td className="py-2 text-gray-500">{(t.entry_time || '').split(' ')[0] || (t.entry_time || '').split('T')[0]}</td>
                          <td className="py-2 text-white">{t.symbol}</td>
                          <td className="py-2 text-gray-300">₹{(t.entry_price || 0).toFixed(1)}</td>
                          <td className="py-2 text-gray-300">₹{(t.exit_price || 0).toFixed(1)}</td>
                          <td className={`py-2 text-right font-bold ${(t.net_pnl || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                            {(t.net_pnl || 0) >= 0 ? '+' : ''}{(t.net_pnl || 0).toFixed(0)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-[#161b27]/50 border border-dashed border-[#1e2130] rounded-2xl flex flex-col items-center justify-center py-32 text-gray-600 space-y-4">
              <History size={48} className="opacity-10" />
              <p className="text-sm italic">Run a backtest to visualize historical performance</p>
            </div>
          )}

          {/* History table */}
          <div className="bg-[#161b27] border border-[#1e2130] p-6 rounded-xl">
             <h4 className="text-gray-400 text-[10px] font-bold uppercase mb-4 tracking-widest">Run History</h4>
             <div className="space-y-2">
               {history?.map((h, i) => (
                 <div key={i} className="flex justify-between items-center p-3 bg-[#0f1117] rounded-lg border border-[#1e2130] hover:border-gray-700 cursor-pointer transition-all">
                   <div className="flex items-center gap-3">
                     <span className={`w-2 h-2 rounded-full ${h.status === 'COMPLETED' ? 'bg-green-500' : 'bg-red-500'}`}></span>
                     <span className="text-xs text-white font-bold">{h.config.stocks.join(',')} | {h.config.entry_strategy}</span>
                   </div>
                   <div className="flex items-center gap-6">
                     <span className="text-[10px] text-gray-600 font-mono">{h.created_at.split('T')[0]}</span>
                     <button className="text-[#00bcd4] text-[10px] font-bold uppercase">View</button>
                   </div>
                 </div>
               ))}
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const RefreshCw = ({ className, size }) => (
  <svg 
    xmlns="http://www.w3.org/2000/svg" 
    width={size} 
    height={size} 
    viewBox="0 0 24 24" 
    fill="none" 
    stroke="currentColor" 
    strokeWidth="2" 
    strokeLinecap="round" 
    strokeLinejoin="round" 
    className={className}
  >
    <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8" />
    <path d="M21 3v5h-5" />
  </svg>
);

export default Backtesting;
