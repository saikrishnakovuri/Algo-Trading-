import React, { useState, useEffect } from 'react';
import api, { useApi } from '../hooks/useApi';
import { 
  Play, 
  Pause, 
  XCircle, 
  Send,
  RefreshCw,
  Activity
} from 'lucide-react';

const NewTrade = () => {
  const { data: status, refetch: refetchStatus } = useApi('/api/live/status', 5000);
  const { data: positions, refetch: refetchPositions } = useApi('/api/live/positions', 5000);
  
  const [form, setForm] = useState({
    symbol: 'NIFTY',
    direction: 'CE',
    lots: 1,
    entry_type: 'MARKET',
    price: '',
    sl: '25.0',
    tp_r: 2.0,
    strategy: 'VWAP_BOUNCE'
  });

  const [loading, setLoading] = useState(false);

  const handleControl = async (type, payload = {}) => {
    setLoading(true);
    try {
      await api.post(`/api/control/${type}`, payload);
      // Brief delay to allow bot to process and backend to update
      setTimeout(() => { 
        refetchStatus(); 
        refetchPositions(); 
        setLoading(false);
      }, 1000);
    } catch (err) {
      alert(`Control failed: ${err.message}`);
      setLoading(false);
    }
  };

  const handlePlaceTrade = async (e) => {
    e.preventDefault();
    if (!window.confirm(`Place ${form.direction} order for ${form.symbol}?`)) return;
    handleControl('manual-trade', form);
  };

  // Safe numeric formatting
  const formatCurrency = (val) => {
    if (val === undefined || val === null) return '₹0.00';
    return `₹${Number(val).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
  };

  return (
    <div className="p-8 space-y-8">
      {/* Bot Status Bar */}
      <div className="bg-[#161b27] border border-[#1e2130] p-6 rounded-xl flex justify-between items-center shadow-lg">
        <div className="flex items-center gap-4">
          <div className={`w-3 h-3 rounded-full ${status?.status === 'ACTIVE' ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'}`}></div>
          <div>
            <p className="text-white font-bold text-lg tracking-tight">Bot is {status?.status || 'UNKNOWN'}</p>
            <p className="text-gray-500 text-[10px] uppercase font-mono tracking-widest">
              {status?.mode || 'PAPER'} MODE | {status?.trades_today || 0}/5 TRADES TAKEN
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          {status?.status === 'PAUSED' ? (
            <button 
              onClick={() => handleControl('resume-bot')}
              disabled={loading}
              className="flex items-center gap-2 bg-[#00c853] hover:bg-[#00e676] text-black font-bold px-6 py-2 rounded-lg transition-all disabled:opacity-50"
            >
              <Play size={18} fill="currentColor" /> RESUME BOT
            </button>
          ) : (
            <button 
              onClick={() => handleControl('pause-bot')}
              disabled={loading}
              className="flex items-center gap-2 bg-yellow-500 hover:bg-yellow-400 text-black font-bold px-6 py-2 rounded-lg transition-all disabled:opacity-50"
            >
              <Pause size={18} fill="currentColor" /> PAUSE BOT
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Manual Entry Form */}
        <div className="bg-[#161b27] border border-[#1e2130] p-8 rounded-xl space-y-6 shadow-xl">
          <h3 className="text-white font-bold flex items-center gap-2 uppercase tracking-widest text-sm border-b border-[#1e2130] pb-4">
            <Send size={18} className="text-[#00bcd4]" /> Manual Order Execution
          </h3>
          
          <form onSubmit={handlePlaceTrade} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-gray-500 text-[10px] font-bold uppercase tracking-wider">Symbol</label>
                <select 
                  className="w-full bg-[#0f1117] border border-[#1e2130] rounded-lg p-3 text-white focus:border-[#00bcd4] outline-none text-sm"
                  value={form.symbol}
                  onChange={(e) => setForm({...form, symbol: e.target.value})}
                >
                  <option>NIFTY</option>
                  <option>BANKNIFTY</option>
                  <option>RELIANCE</option>
                  <option>HDFCBANK</option>
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-gray-500 text-[10px] font-bold uppercase tracking-wider">Direction</label>
                <div className="flex bg-[#0f1117] rounded-lg p-1 border border-[#1e2130]">
                  <button 
                    type="button"
                    className={`flex-1 py-2 rounded-md text-[10px] font-bold transition-all ${form.direction === 'CE' ? 'bg-green-500 text-black shadow-lg shadow-green-500/20' : 'text-gray-500'}`}
                    onClick={() => setForm({...form, direction: 'CE'})}
                  >CALL (CE)</button>
                  <button 
                    type="button"
                    className={`flex-1 py-2 rounded-md text-[10px] font-bold transition-all ${form.direction === 'PE' ? 'bg-red-500 text-white shadow-lg shadow-red-500/20' : 'text-gray-500'}`}
                    onClick={() => setForm({...form, direction: 'PE'})}
                  >PUT (PE)</button>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <label className="text-gray-500 text-[10px] font-bold uppercase tracking-wider">Lots</label>
                <input 
                  type="number" min="1" max="50"
                  className="w-full bg-[#0f1117] border border-[#1e2130] rounded-lg p-3 text-white focus:border-[#00bcd4] outline-none font-mono text-sm"
                  value={form.lots}
                  onChange={(e) => setForm({...form, lots: parseInt(e.target.value)})}
                />
              </div>
              <div className="space-y-2 col-span-2">
                <label className="text-gray-500 text-[10px] font-bold uppercase tracking-wider">Strategy Reference</label>
                <select 
                  className="w-full bg-[#0f1117] border border-[#1e2130] rounded-lg p-3 text-white focus:border-[#00bcd4] outline-none text-sm"
                  value={form.strategy}
                  onChange={(e) => setForm({...form, strategy: e.target.value})}
                >
                  <option value="VWAP_BOUNCE">VWAP Bounce</option>
                  <option value="MOMENTUM_BREAKOUT">Momentum Breakout</option>
                  <option value="MANUAL">Manual Discretionary</option>
                  <option value="LIQUIDITY_TRAP">Liquidity Trap</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 pt-4 border-t border-[#1e2130]">
              <div className="space-y-2">
                <label className="text-gray-500 text-[10px] font-bold uppercase tracking-wider">SL (₹ Points)</label>
                <input 
                  type="number" step="0.5"
                  className="w-full bg-[#0f1117] border border-[#1e2130] rounded-lg p-3 text-white focus:border-[#00bcd4] outline-none font-mono text-sm"
                  value={form.sl}
                  onChange={(e) => setForm({...form, sl: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <label className="text-gray-500 text-[10px] font-bold uppercase tracking-wider">Target (R-Mult)</label>
                <input 
                  type="number" step="0.1"
                  className="w-full bg-[#0f1117] border border-[#1e2130] rounded-lg p-3 text-white focus:border-[#00bcd4] outline-none font-mono text-sm"
                  value={form.tp_r}
                  onChange={(e) => setForm({...form, tp_r: parseFloat(e.target.value)})}
                />
              </div>
            </div>

            <button 
              type="submit"
              disabled={loading}
              className="w-full bg-[#00bcd4] hover:bg-[#00acc1] text-black font-bold py-4 rounded-xl mt-4 transition-all flex items-center justify-center gap-2 uppercase tracking-widest shadow-lg shadow-cyan-500/20 disabled:opacity-50"
            >
              {loading ? <RefreshCw className="animate-spin" size={18} /> : <Send size={18} />}
              Execute Market Order
            </button>
          </form>
        </div>

        {/* Active Positions List */}
        <div className="space-y-6">
          <div className="bg-[#161b27] border border-[#1e2130] p-6 rounded-xl min-h-[400px] shadow-xl">
            <div className="flex justify-between items-center mb-6 border-b border-[#1e2130] pb-4">
              <h3 className="text-white font-bold uppercase tracking-widest text-sm flex items-center gap-2">
                <RefreshCw size={16} className="text-[#00c853]" /> Open Exposure
              </h3>
              <button 
                onClick={() => handleControl('close-all')}
                disabled={loading || !positions || positions.length === 0}
                className="text-red-500 hover:text-red-400 text-[10px] font-bold uppercase border border-red-500/30 px-3 py-1 rounded-lg transition-all disabled:opacity-30"
              >
                Close All
              </button>
            </div>

            <div className="space-y-3">
              {Array.isArray(positions) && positions.length > 0 ? positions.map((p, i) => (
                <div key={p.id || i} className="bg-[#0f1117] border border-[#1e2130] p-4 rounded-xl flex justify-between items-center group hover:border-gray-600 transition-all shadow-md">
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 flex items-center justify-center rounded-lg font-bold text-xs ${p.direction === 'CE' ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
                      {p.direction}
                    </div>
                    <div>
                      <p className="font-bold text-white text-sm tracking-tight">{p.stock}</p>
                      <p className="text-gray-600 text-[10px] font-mono uppercase">{p.lots} LOTS | AVG ₹{p.entry?.toFixed(2)}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <p className={`font-mono font-bold text-sm ${p.unrealized >= 0 ? 'text-[#00c853]' : 'text-[#ff1744]'}`}>
                        {p.unrealized >= 0 ? '+' : ''}{formatCurrency(p.unrealized)}
                      </p>
                      <p className="text-gray-600 text-[9px] uppercase tracking-tighter">Unrealised PnL</p>
                    </div>
                    <button 
                      onClick={() => handleControl('close-position', { trade_id: p.id })}
                      disabled={loading}
                      className="bg-red-500/10 hover:bg-red-500 text-red-500 hover:text-white p-2 rounded-lg transition-all opacity-40 group-hover:opacity-100 disabled:opacity-20"
                    >
                      <XCircle size={18} />
                    </button>
                  </div>
                </div>
              )) : (
                <div className="flex flex-col items-center justify-center py-24 text-gray-600 space-y-4">
                  <Activity size={48} className="opacity-10" />
                  <div className="text-center">
                    <p className="italic text-sm">No active market exposure</p>
                    <p className="text-[10px] uppercase tracking-widest mt-1 opacity-50">Monitoring for signals...</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NewTrade;
