
import os

TARGET = '../AlgoTradingTelegramBotAndFrontend/frontend/src/pages/TradeJournal.js'

UPGRADED_CODE = r"""import React, { useState, useEffect } from 'react';
import { 
  BookOpen, 
  Download, 
  Filter, 
  ArrowUpRight, 
  ArrowDownRight, 
  Activity,
  RefreshCw,
  TrendingDown
} from 'lucide-react';

const API_BASE = '/api/journal';

export default function TradeJournal() {
    const [activeView, setActiveTab] = useState('trades');
    const [page, setPage] = useState(1);
    const [data, setData] = useState({ trades: [], total: 0, pages: 0 });
    const [summary, setSummary] = useState({ total_trades: 0, total_pnl: 0, win_rate: 0 });
    const [filters, setFilters] = useState({ strategy: '', result: '', source: '' });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (activeView === 'trades') {
            fetchJournal();
        }
        fetchSummary();
    }, [page, filters, activeView]);

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
        if (!window.confirm('Import results from backtest_detailed_results.csv?')) return;
        await fetch(`${API_BASE}/import-backtest`, { method: 'POST' });
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
                        onClick={() => setActiveTab(activeView === 'trades' ? 'analysis' : 'trades')}
                        className="bg-[#161b27] hover:bg-gray-800 text-[#00bcd4] font-bold px-6 py-2 rounded-lg border border-[#00bcd4]/30 flex items-center gap-2 text-xs"
                    >
                        {activeView === 'trades' ? <Activity size={16} /> : <BookOpen size={16} />}
                        {activeView === 'trades' ? 'LOSS ANALYSIS' : 'VIEW TRADES'}
                    </button>
                    <button 
                        onClick={importBacktest}
                        className="bg-[#161b27] hover:bg-gray-800 text-gray-400 font-bold px-6 py-2 rounded-lg border border-[#1e2130] flex items-center gap-2 text-xs"
                    >
                        <RefreshCw size={16} /> IMPORT
                    </button>
                    <a 
                        href={`${API_BASE}/export`}
                        className="bg-[#00bcd4] hover:bg-[#00acc1] text-black font-bold px-6 py-2 rounded-lg flex items-center gap-2 text-xs"
                    >
                        <Download size={16} /> EXPORT CSV
                    </a>
                </div>
            </div>

            {activeView === 'trades' ? (
                <>
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
                                    <tr><td colSpan="5" className="p-8 text-center text-gray-600 animate-pulse font-bold">LOADING...</td></tr>
                                ) : data.trades.map(t => (
                                    <tr key={t.trade_id} className="hover:bg-white/[0.02]">
                                        <td className="p-4 text-xs font-mono text-gray-400">{t.entry_time?.slice(0, 16).replace('T', ' ')}</td>
                                        <td className="p-4 font-bold text-xs">{t.symbol}</td>
                                        <td className="p-4 text-xs text-gray-300">{t.strategy_name}</td>
                                        <td className={`p-4 text-xs font-mono text-right font-bold ${t.pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                            ₹{t.pnl?.toLocaleString()}
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
                    </div>
                </>
            ) : (
                <LossAnalysisView />
            )}
        </div>
    );
}

function LossAnalysisView() {
    const [analysis, setAnalysis] = useState(null);

    useEffect(() => {
        fetch(`${API_BASE}/losses/analysis`).then(res => res.json()).then(setAnalysis);
    }, []);

    if (!analysis) return <div className="text-gray-500 animate-pulse font-bold">ANALYZING LOSS PATTERNS...</div>;

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="bg-[#161b27] p-6 rounded-2xl border border-red-500/20">
                    <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">Total Lost</p>
                    <p className="text-3xl font-black text-red-500">₹{analysis.total_lost?.toLocaleString()}</p>
                </div>
                <div className="bg-[#161b27] p-6 rounded-2xl border border-[#1e2130]">
                    <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">Loss Count</p>
                    <p className="text-3xl font-black text-white">{analysis.total_losses}</p>
                </div>
                <div className="bg-[#161b27] p-6 rounded-2xl border border-[#1e2130]">
                    <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">Avg. Loss</p>
                    <p className="text-3xl font-black text-white">₹{analysis.avg_loss?.toLocaleString()}</p>
                </div>
                <div className="bg-[#161b27] p-6 rounded-2xl border border-[#1e2130]">
                    <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">Worst Case</p>
                    <p className="text-3xl font-black text-red-400">₹{analysis.worst_loss?.toLocaleString()}</p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="bg-[#161b27] p-6 rounded-2xl border border-[#1e2130]">
                    <h3 className="text-white font-bold uppercase tracking-widest text-xs mb-6 flex items-center gap-2">
                        <TrendingDown size={16} className="text-red-500" /> Losses by Strategy
                    </h3>
                    <div className="space-y-4">
                        {analysis.by_strategy?.map(s => (
                            <div key={s.strategy} className="flex items-center gap-4">
                                <div className="flex-1">
                                    <div className="flex justify-between text-xs mb-1">
                                        <span className="text-gray-300 font-bold">{s.strategy}</span>
                                        <span className="text-red-400 font-mono">₹{s.total_lost?.toLocaleString()}</span>
                                    </div>
                                    <div className="w-full bg-gray-900 h-1.5 rounded-full overflow-hidden">
                                        <div 
                                            className="bg-red-500 h-full" 
                                            style={{width: `${Math.abs(s.total_lost / analysis.total_lost) * 100}%`}}
                                        ></div>
                                    </div>
                                </div>
                                <div className="text-[10px] font-bold text-gray-500 w-8">{s.count}x</div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="bg-[#161b27] p-6 rounded-2xl border border-[#1e2130]">
                    <h3 className="text-white font-bold uppercase tracking-widest text-xs mb-6 flex items-center gap-2">
                        <TrendingDown size={16} className="text-red-500" /> Losses by Day
                    </h3>
                    <div className="space-y-4">
                        {analysis.by_day?.map(d => (
                            <div key={d.day} className="flex items-center gap-4">
                                <div className="flex-1">
                                    <div className="flex justify-between text-xs mb-1">
                                        <span className="text-gray-300 font-bold">{d.day}</span>
                                        <span className="text-red-400 font-mono">₹{d.total_lost?.toLocaleString()}</span>
                                    </div>
                                    <div className="w-full bg-gray-900 h-1.5 rounded-full overflow-hidden">
                                        <div 
                                            className="bg-red-500 h-full" 
                                            style={{width: `${Math.abs(d.total_lost / analysis.total_lost) * 100}%`}}
                                        ></div>
                                    </div>
                                </div>
                                <div className="text-[10px] font-bold text-gray-500 w-8">{d.count}x</div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
"""

with open(TARGET, 'w', encoding='utf-8') as f:
    f.write(UPGRADED_CODE)
print("Trade Journal upgraded with Loss Analysis successfully!")
