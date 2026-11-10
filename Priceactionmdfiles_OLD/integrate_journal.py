
import os

FRONTEND_DIR = '../AlgoTradingTelegramBotAndFrontend/frontend/src'

JOURNAL_CODE = r"""import React, { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { 
  BookOpen, 
  Download, 
  Filter, 
  ArrowUpRight, 
  ArrowDownRight, 
  Clock, 
  ExternalLink,
  RefreshCw
} from 'lucide-react';

const API_BASE = '/api/journal';

export default function TradeJournal() {
    const [page, setPage] = useState(1);
    const [data, setData] = useState({ trades: [], total: 0, pages: 0 });
    const [summary, setSummary] = useState({ total_trades: 0, total_pnl: 0, win_rate: 0 });
    const [filters, setFilters] = useState({ strategy: '', result: '', source: '' });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchJournal();
        fetchSummary();
    }, [page, filters]);

    const fetchJournal = async () => {
        setLoading(true);
        const params = new URLSearchParams({ page, ...filters });
        const res = await fetch(`${API_BASE}/trades?${params}`);
        const d = await res.json();
        setData(d);
        setLoading(false);
    };

    const fetchSummary = async () => {
        const res = await fetch(`${API_BASE}/summary`);
        const s = await res.json();
        setSummary(s);
    };

    const importBacktest = async () => {
        if (!window.confirm('Import results from backtest_detailed_results.csv? This will overwrite existing backtest journal entries.')) return;
        const res = await fetch(`${API_BASE}/import-backtest`, { method: 'POST' });
        const result = await res.json();
        alert(`Imported ${result.imported} trades.`);
        fetchJournal();
        fetchSummary();
    };

    return (
        <div className="p-8 space-y-8 text-gray-100">
            <div className="flex justify-between items-center">
                <h1 className="text-2xl font-bold text-white uppercase tracking-widest flex items-center gap-3">
                    <BookOpen size={28} className="text-[#00bcd4]" /> P&L Trade Journal
                </h1>
                <div className="flex gap-4">
                    <button 
                        onClick={importBacktest}
                        className="bg-[#161b27] hover:bg-gray-800 text-gray-400 font-bold px-6 py-2 rounded-lg border border-[#1e2130] flex items-center gap-2 text-xs"
                    >
                        <RefreshCw size={16} /> IMPORT BACKTEST
                    </button>
                    <a 
                        href={`${API_BASE}/export`}
                        className="bg-[#00bcd4] hover:bg-[#00acc1] text-black font-bold px-6 py-2 rounded-lg flex items-center gap-2 text-xs"
                    >
                        <Download size={16} /> EXPORT CSV
                    </a>
                </div>
            </div>

            {/* Summary Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-[#161b27] p-6 rounded-2xl border border-[#1e2130]">
                    <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">Net Realized P&L</p>
                    <p className={`text-3xl font-black ${summary.total_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        ₹{summary.total_pnl?.toLocaleString()}
                    </p>
                </div>
                <div className="bg-[#161b27] p-6 rounded-2xl border border-[#1e2130]">
                    <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">Win Rate</p>
                    <p className="text-3xl font-black text-white">{summary.win_rate}%</p>
                </div>
                <div className="bg-[#161b27] p-6 rounded-2xl border border-[#1e2130]">
                    <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">Total Trades</p>
                    <p className="text-3xl font-black text-white">{summary.total_trades}</p>
                </div>
            </div>

            {/* Table Area */}
            <div className="bg-[#161b27] border border-[#1e2130] rounded-2xl overflow-hidden">
                <div className="p-4 bg-[#1c212e] border-b border-[#1e2130] flex justify-between items-center">
                    <div className="flex gap-4">
                        <select 
                            className="bg-[#0f1117] border border-[#1e2130] rounded-lg px-4 py-2 text-xs text-gray-400 outline-none"
                            value={filters.result}
                            onChange={(e) => setFilters({...filters, result: e.target.value})}
                        >
                            <option value="">All Results</option>
                            <option value="WIN">WIN</option>
                            <option value="LOSS">LOSS</option>
                        </select>
                        <select 
                            className="bg-[#0f1117] border border-[#1e2130] rounded-lg px-4 py-2 text-xs text-gray-400 outline-none"
                            value={filters.source}
                            onChange={(e) => setFilters({...filters, source: e.target.value})}
                        >
                            <option value="">All Sources</option>
                            <option value="live">Live</option>
                            <option value="backtest">Backtest</option>
                        </select>
                    </div>
                    <div className="text-[10px] text-gray-500 font-bold uppercase">
                        Page {page} of {data.pages}
                    </div>
                </div>

                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="border-b border-[#1e2130] bg-[#1c212e]/30">
                            <th className="p-4 text-[10px] text-gray-500 font-bold uppercase">Date/Time</th>
                            <th className="p-4 text-[10px] text-gray-500 font-bold uppercase">Symbol</th>
                            <th className="p-4 text-[10px] text-gray-500 font-bold uppercase">Strategy</th>
                            <th className="p-4 text-[10px] text-gray-500 font-bold uppercase text-right">P&L</th>
                            <th className="p-4 text-[10px] text-gray-500 font-bold uppercase text-center">Result</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1e2130]">
                        {loading ? (
                            <tr><td colSpan="5" className="p-8 text-center text-gray-600 animate-pulse uppercase tracking-widest font-bold">Fetching Journal...</td></tr>
                        ) : data.trades.map(t => (
                            <tr key={t.trade_id} className="hover:bg-white/[0.02] transition-colors group">
                                <td className="p-4 text-xs font-mono text-gray-400">
                                    {t.entry_time?.slice(0, 16).replace('T', ' ')}
                                </td>
                                <td className="p-4">
                                    <div className="flex items-center gap-2">
                                        <span className={`p-1 rounded ${t.pnl >= 0 ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'}`}>
                                            {t.pnl >= 0 ? <ArrowUpRight size={14}/> : <ArrowDownRight size={14}/>}
                                        </span>
                                        <span className="font-bold text-xs">{t.symbol}</span>
                                    </div>
                                </td>
                                <td className="p-4 text-xs text-gray-300 font-medium">{t.strategy_name}</td>
                                <td className={`p-4 text-xs font-mono text-right font-bold ${t.pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                    {t.pnl >= 0 ? '+' : ''}₹{t.pnl?.toLocaleString()}
                                </td>
                                <td className="p-4 text-center">
                                    <span className={`text-[10px] font-black px-3 py-1 rounded-full ${t.result === 'WIN' ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
                                        {t.result}
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>

                <div className="p-4 bg-[#1c212e] flex justify-center gap-4">
                    <button 
                        disabled={page === 1}
                        onClick={() => setPage(p => p - 1)}
                        className="px-6 py-2 rounded-lg bg-[#0f1117] text-gray-400 disabled:opacity-30 font-bold text-xs"
                    >PREV</button>
                    <button 
                        disabled={page >= data.pages}
                        onClick={() => setPage(p => p + 1)}
                        className="px-6 py-2 rounded-lg bg-[#0f1117] text-gray-400 disabled:opacity-30 font-bold text-xs"
                    >NEXT</button>
                </div>
            </div>
        </div>
    );
}
"""

def integrate_journal():
    # 1. Write the component
    path = os.path.join(FRONTEND_DIR, 'pages', 'TradeJournal.js')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(JOURNAL_CODE)
    
    # 2. Update App.js
    app_path = os.path.join(FRONTEND_DIR, 'App.js')
    with open(app_path, 'r', encoding='utf-8') as f:
        app_code = f.read()
    
    if 'TradeJournal' not in app_code:
        app_code = app_code.replace("import PADashboard from './pages/PADashboard';", "import PADashboard from './pages/PADashboard';\nimport TradeJournal from './pages/TradeJournal';")
        app_code = app_code.replace('<Route path="/pa-engine" element={<PADashboard />} />', '<Route path="/pa-engine" element={<PADashboard />} />\n              <Route path="/journal" element={<TradeJournal />} />')
        with open(app_path, 'w', encoding='utf-8') as f:
            f.write(app_code)

    # 3. Update Sidebar.jsx
    sidebar_path = os.path.join(FRONTEND_DIR, 'components', 'Sidebar.jsx')
    with open(sidebar_path, 'r', encoding='utf-8') as f:
        sidebar_code = f.read()
        
    if '/journal' not in sidebar_code:
        inject_str = '<NavLink to="/journal" className={({isActive}) => `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${isActive ? "bg-[#00bcd4]/10 text-[#00bcd4]" : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"}`}><span className="text-xl">📓</span><span className="font-medium">Journal</span></NavLink>\n          '
        sidebar_code = sidebar_code.replace('<NavLink to="/pa-engine"', inject_str + '<NavLink to="/pa-engine"')
        with open(sidebar_path, 'w', encoding='utf-8') as f:
            f.write(sidebar_code)

if __name__ == "__main__":
    integrate_journal()
    print("Trade Journal integration complete.")
