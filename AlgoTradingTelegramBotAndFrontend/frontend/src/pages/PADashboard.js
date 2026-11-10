import React, { useState, useEffect } from 'react';
import api from '../hooks/useApi';
import { 
  Save, 
  ShieldAlert, 
  Clock, 
  Calendar, 
  Activity, 
  BarChart3,
  CheckCircle2,
  XCircle,
  ToggleLeft,
  ToggleRight
} from 'lucide-react';
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';


const API_BASE = `${BACKEND_URL}/api/pa`; 

export default function PADashboard() {
    const [activeTab, setActiveTab] = useState('strategies');
    const [toast, setToast] = useState(null);

    const showToast = (msg, type = 'success') => {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 3000);
    };

    return (
        <div className="p-8 space-y-8 text-gray-100">
            <div className="flex justify-between items-center">
                <h1 className="text-2xl font-bold text-white uppercase tracking-widest">Price Action Engine</h1>
                <div className="flex gap-2">
                     {['strategies', 'config', 'edge', 'montecarlo', 'backtest'].map(tab => (
                        <button 
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`px-6 py-2 rounded-lg text-xs font-bold transition-all ${activeTab === tab ? 'bg-[#00bcd4] text-black' : 'bg-[#161b27] text-gray-500 hover:text-white border border-[#1e2130]'}`}
                        >
                            {tab.toUpperCase()}
                        </button>
                    ))}
                </div>
            </div>
            
            {toast && (
                <div className={`fixed top-4 right-4 p-4 rounded-xl text-white shadow-2xl z-50 flex items-center gap-3 animate-in slide-in-from-right ${toast.type === 'error' ? 'bg-red-600' : 'bg-green-600'}`}>
                    {toast.type === 'error' ? <XCircle size={20} /> : <CheckCircle2 size={20} />}
                    {toast.msg}
                </div>
            )}

            <div className="bg-[#161b27] border border-[#1e2130] p-8 rounded-2xl min-h-[600px]">
                {activeTab === 'strategies' && <PAStrategyManager showToast={showToast} />}
                {activeTab === 'config' && <PAConfigEditor showToast={showToast} />}
                {activeTab === 'edge' && <PAEdgeMonitor />}
                {activeTab === 'montecarlo' && <PAMonteCarlo />}
                {activeTab === 'backtest' && <PABacktestResults />}
            </div>
        </div>
    );
}

function PAStrategyManager({ showToast }) {
    const [strategies, setStrategies] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchStrategies();
    }, []);

    const fetchStrategies = async () => {
        try {
            const res = await fetch(`${API_BASE}/strategies`);
            const data = await res.json();
            setStrategies(data);
            setLoading(false);
        } catch (err) {
            console.error(err);
        }
    };

    const toggle = async (name) => {
        try {
            await fetch(`${API_BASE}/strategies/${encodeURIComponent(name)}/toggle`, { method: 'PUT' });
            showToast(`${name} toggled`);
            fetchStrategies();
        } catch (err) {
            showToast(err.message, 'error');
        }
    };

    if (loading) return <div className="text-gray-500 animate-pulse">Loading strategies...</div>;

    return (
        <div className="space-y-6">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Activity size={20} className="text-[#00bcd4]" /> Strategy Survivor Pool
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {strategies.map(s => (
                    <div key={s.name} className={`p-4 rounded-xl border transition-all ${s.active ? 'bg-[#00bcd4]/5 border-[#00bcd4]/30' : 'bg-[#0f1117] border-[#1e2130] grayscale opacity-60'}`}>
                        <div className="flex justify-between items-start mb-2">
                            <span className="font-bold text-sm text-white truncate max-w-[200px]">{s.name}</span>
                            <button onClick={() => toggle(s.name)}>
                                {s.active ? <ToggleRight className="text-[#00bcd4]" size={28} /> : <ToggleLeft className="text-gray-600" size={28} />}
                            </button>
                        </div>
                        <div className="flex justify-between text-[10px] uppercase font-bold text-gray-500">
                            <span>PF: <span className="text-green-500">{s.profit_factor}</span></span>
                            <span>Conf: {s.confidence}</span>
                            <span>Dir: {s.direction}</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function PAConfigEditor({ showToast }) {
    const [config, setConfig] = useState(null);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        fetch(`${API_BASE}/config`).then(res => res.json()).then(setConfig);
    }, []);

    const handleSave = async () => {
        setSaving(true);
        try {
            const res = await fetch(`${API_BASE}/config`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            if (res.ok) showToast('Configuration saved successfully');
            else throw new Error('Failed to save');
        } catch (err) {
            showToast(err.message, 'error');
        }
        setSaving(false);
    };

    if (!config) return null;

    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
    const hours = [9, 10, 11, 12, 13, 14, 15];

    return (
        <div className="space-y-8">
            <div className="flex justify-between items-center">
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    <ShieldAlert size={20} className="text-red-500" /> Risk & Schedule Controls
                </h2>
                <button 
                    onClick={handleSave}
                    className="bg-[#00bcd4] text-black font-bold px-6 py-2 rounded-lg flex items-center gap-2 hover:bg-[#00acc1]"
                >
                    <Save size={18} /> {saving ? 'SAVING...' : 'SAVE CONFIG'}
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="bg-[#0f1117] p-6 rounded-xl border border-[#1e2130] space-y-6">
                    <div className="space-y-4">
                        <div className="flex justify-between items-end">
                            <label className="text-xs font-bold text-gray-500 uppercase">Trading Capital</label>
                            <span className="text-[#00bcd4] font-mono font-bold">₹{config.capital?.toLocaleString()}</span>
                        </div>
                        <input 
                            type="number" 
                            className="w-full bg-[#161b27] border border-[#1e2130] rounded-lg p-3 text-white outline-none"
                            value={config.capital}
                            onChange={(e) => setConfig({...config, capital: parseInt(e.target.value)})}
                        />
                    </div>

                    <div className="space-y-4">
                        <div className="flex justify-between items-end">
                            <label className="text-xs font-bold text-gray-500 uppercase">Risk Per Trade ({(config.risk_pct * 100).toFixed(2)}%)</label>
                            <span className="text-red-400 font-mono font-bold">₹{(config.capital * config.risk_pct).toLocaleString()}</span>
                        </div>
                        <input 
                            type="range" min="0.0025" max="0.05" step="0.0025"
                            className="w-full accent-[#00bcd4]"
                            value={config.risk_pct}
                            onChange={(e) => setConfig({...config, risk_pct: parseFloat(e.target.value)})}
                        />
                    </div>
                </div>

                <div className="bg-[#0f1117] p-6 rounded-xl border border-[#1e2130] space-y-6">
                    <div className="space-y-3">
                        <label className="text-xs font-bold text-gray-500 uppercase flex items-center gap-2"><Calendar size={14}/> Active Trading Days</label>
                        <div className="flex flex-wrap gap-2">
                            {days.map(d => (
                                <button
                                    key={d}
                                    onClick={() => {
                                        const active = config.allowed_days || [];
                                        const updated = active.includes(d) ? active.filter(x => x !== d) : [...active, d];
                                        setConfig({...config, allowed_days: updated});
                                    }}
                                    className={`px-4 py-2 rounded-lg text-[10px] font-bold border transition-all ${config.allowed_days?.includes(d) ? 'bg-[#00bcd4]/10 border-[#00bcd4] text-[#00bcd4]' : 'bg-[#161b27] border-[#1e2130] text-gray-500'}`}
                                >{d.toUpperCase()}</button>
                            ))}
                        </div>
                    </div>

                    <div className="space-y-3">
                        <label className="text-xs font-bold text-gray-500 uppercase flex items-center gap-2"><Clock size={14}/> Active Trading Hours</label>
                        <div className="flex flex-wrap gap-2">
                            {hours.map(h => (
                                <button
                                    key={h}
                                    onClick={() => {
                                        const active = config.allowed_hours || [];
                                        const updated = active.includes(h) ? active.filter(x => x !== h) : [...active, h];
                                        setConfig({...config, allowed_hours: updated});
                                    }}
                                    className={`w-12 py-2 rounded-lg text-[10px] font-bold border transition-all ${config.allowed_hours?.includes(h) ? 'bg-[#00bcd4]/10 border-[#00bcd4] text-[#00bcd4]' : 'bg-[#161b27] border-[#1e2130] text-gray-500'}`}
                                >{h}:00</button>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function PAEdgeMonitor() {
    const [edge, setEdge] = useState(null);

    useEffect(() => {
        fetch(`${API_BASE}/edge`).then(res => res.json()).then(setEdge);
    }, []);

    if (!edge) return <div className="text-gray-500 animate-pulse">Running edge analysis...</div>;

    return (
        <div className="space-y-6">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <BarChart3 size={20} className="text-[#00bcd4]" /> Edge Statistical Strength
            </h2>
            <div className="p-6 bg-[#0f1117] rounded-xl border border-[#1e2130]">
                <div className={`text-2xl font-black mb-6 ${edge.status === 'GREEN' ? 'text-green-500' : 'text-red-500'}`}>STATUS: {edge.status}</div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="space-y-4">
                        <h3 className="text-xs font-bold text-gray-500 uppercase border-b border-[#1e2130] pb-2">Statistical Tests</h3>
                        <div className="space-y-2 text-sm">
                            <div className="flex justify-between"><span>Rolling P&L</span><span className="text-white font-mono">₹{edge.decay?.second_half_avg_pnl?.toLocaleString()}</span></div>
                            <div className="flex justify-between"><span>Win Rate</span><span className="text-white font-mono">{edge.triggers?.current_win_rate}%</span></div>
                            <div className="flex justify-between"><span>Max Loss Streak</span><span className="text-red-400 font-mono">{edge.streaks?.max_loss_streak}</span></div>
                        </div>
                    </div>
                    <div className="space-y-4">
                        <h3 className="text-xs font-bold text-gray-500 uppercase border-b border-[#1e2130] pb-2">Kelly Position Sizing</h3>
                        <div className="space-y-2 text-sm">
                            <div className="flex justify-between"><span>Optimal Risk</span><span className="text-[#00bcd4] font-mono">{edge.kelly?.recommended_risk_pct}%</span></div>
                            <div className="flex justify-between"><span>Half Kelly</span><span className="text-white font-mono">{edge.kelly?.half_kelly_pct}%</span></div>
                            <div className="flex justify-between"><span>Edge Decay</span><span className="text-yellow-500 font-mono">{edge.decay?.verdict}</span></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function PAMonteCarlo() {
    const [mc, setMc] = useState(null);

    useEffect(() => {
        fetch(`${API_BASE}/montecarlo`).then(res => res.json()).then(setMc);
    }, []);

    if (!mc) return <div className="text-gray-500 animate-pulse">Running 10,000 randomized simulations...</div>;

    const data = mc.at_current_risk;

    return (
        <div className="space-y-6">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Activity size={20} className="text-purple-500" /> Monte Carlo Stress Test
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="p-6 bg-[#0f1117] rounded-xl border border-[#1e2130] text-center">
                    <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">Prob. Profit</p>
                    <p className="text-3xl font-black text-green-500">{data.probabilities?.profit}%</p>
                </div>
                <div className="p-6 bg-[#0f1117] rounded-xl border border-[#1e2130] text-center">
                    <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">Prob. 70% ROI</p>
                    <p className="text-3xl font-black text-[#00bcd4]">{data.probabilities?.target_70pct_roi}%</p>
                </div>
                <div className="p-6 bg-[#0f1117] rounded-xl border border-[#1e2130] text-center">
                    <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">Prob. Ruin</p>
                    <p className="text-3xl font-black text-red-500">{data.probabilities?.ruin}%</p>
                </div>
            </div>
            <div className="p-6 bg-[#0f1117] rounded-xl border border-[#1e2130]">
                <h3 className="text-xs font-bold text-gray-500 uppercase mb-4">Worst-Case Drawdown Forecast</h3>
                <div className="w-full bg-gray-800 h-4 rounded-full overflow-hidden flex">
                    <div style={{width: `${data.drawdown?.median_max_dd_pct}%`}} className="bg-yellow-500 h-full"></div>
                    <div style={{width: `${Math.max(0, data.drawdown?.p95_max_dd_pct - data.drawdown?.median_max_dd_pct)}%`}} className="bg-orange-600 h-full"></div>
                    <div style={{width: `${Math.max(0, data.drawdown?.worst_dd_pct - data.drawdown?.p95_max_dd_pct)}%`}} className="bg-red-700 h-full"></div>
                </div>
                <div className="flex justify-between text-[10px] font-bold mt-2 text-gray-500">
                    <span>MEDIAN: {data.drawdown?.median_max_dd_pct}%</span>
                    <span>95th %ILE: {data.drawdown?.p95_max_dd_pct}%</span>
                    <span>WORST: {data.drawdown?.worst_dd_pct}%</span>
                </div>
            </div>
        </div>
    );
}

function PABacktestResults() {
    const [files, setFiles] = useState([]);
    const [selected, setSelected] = useState(null);

    useEffect(() => {
        fetch(`${API_BASE}/backtest/files`).then(res => res.json()).then(setFiles);
    }, []);

    const loadFile = (name) => {
        fetch(`${API_BASE}/backtest/${name}`).then(res => res.json()).then(setSelected);
    };

    return (
        <div className="space-y-6">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <BarChart3 size={20} className="text-yellow-500" /> Historical Backtest Data
            </h2>
            <div className="flex flex-wrap gap-3">
                {files.map(f => (
                    <button 
                        key={f.name} 
                        onClick={() => loadFile(f.name)} 
                        className={`px-4 py-2 rounded-lg text-xs font-bold border transition-all ${selected?.name === f.name ? 'bg-yellow-500/10 border-yellow-500 text-yellow-500' : 'bg-[#0f1117] border-[#1e2130] text-gray-500 hover:text-white'}`}
                    >
                        {f.name.replace('.csv', '')}
                    </button>
                ))}
            </div>
            {selected && (
                <div className="bg-[#0f1117] p-4 rounded-xl border border-[#1e2130] overflow-auto max-h-[500px]">
                     <pre className="text-[10px] text-gray-400 font-mono">
                        {JSON.stringify(selected, null, 2)}
                    </pre>
                </div>
            )}
        </div>
    );
}
