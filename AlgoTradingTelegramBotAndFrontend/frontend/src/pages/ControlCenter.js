import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  ShieldCheck, 
  Database, 
  Cpu, 
  Clock, 
  Zap, 
  RefreshCw,
  Play,
  Pause,
  AlertCircle
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
const API_BASE = `${BACKEND_URL}/api`;

export default function ControlCenter() {
    const [health, setHealth] = useState(null);
    const [context, setContext] = useState({});
    const [loading, setLoading] = useState(true);

    const fetchData = async () => {
        try {
            const hRes = await fetch(`${API_BASE}/system/health`);
            const cRes = await fetch(`${API_BASE}/live/context`);
            if (hRes.ok) setHealth(await hRes.json());
            if (cRes.ok) setContext(await cRes.json());
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 5000);
        return () => clearInterval(interval);
    }, []);

    const sendControl = async (type) => {
        try {
            await fetch(`${API_BASE}/control/${type}`, { method: 'POST' });
            fetchData();
        } catch (err) {
            alert(err.message);
        }
    };

    if (loading && !health) return <div className="p-8 text-gray-500 animate-pulse font-bold tracking-widest uppercase">Initializing Control Center...</div>;

    return (
        <div className="p-8 space-y-8 text-gray-100">
            <div className="flex justify-between items-center">
                <h1 className="text-2xl font-bold text-white uppercase tracking-widest flex items-center gap-3">
                    <Cpu size={28} className="text-[#00bcd4]" /> System Control Center
                </h1>
                <div className="flex gap-4">
                    <button 
                        onClick={() => sendControl('resume-bot')}
                        className="bg-green-600 hover:bg-green-700 text-white font-bold px-6 py-2 rounded-lg flex items-center gap-2 text-xs"
                    >
                        <Play size={16} /> START BOT
                    </button>
                    <button 
                        onClick={() => sendControl('pause-bot')}
                        className="bg-yellow-600 hover:bg-yellow-700 text-white font-bold px-6 py-2 rounded-lg flex items-center gap-2 text-xs"
                    >
                        <Pause size={16} /> PAUSE BOT
                    </button>
                    <button 
                        onClick={() => sendControl('close-all')}
                        className="bg-red-600 hover:bg-red-700 text-white font-bold px-6 py-2 rounded-lg flex items-center gap-2 text-xs"
                    >
                        <Zap size={16} /> EMERGENCY KILL
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
                <StatusCard 
                    title="Bot Status" 
                    value={health?.bot?.status || 'OFFLINE'} 
                    color={health?.bot?.status === 'ACTIVE' ? 'green' : 'red'}
                    icon={<Activity size={20}/>}
                />
                <StatusCard 
                    title="System Mode" 
                    value={health?.bot?.mode || 'PAPER'} 
                    color="blue"
                    icon={<ShieldCheck size={20}/>}
                />
                <StatusCard 
                    title="Scheduler" 
                    value={health?.scheduler?.running ? 'RUNNING' : 'STOPPED'} 
                    color={health?.scheduler?.running ? 'green' : 'gray'}
                    icon={<Clock size={20}/>}
                />
                <StatusCard 
                    title="Data Source" 
                    value={health?.data_layer?.symbol || 'YFINANCE'} 
                    color="purple"
                    icon={<Database size={20}/>}
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="bg-[#161b27] p-6 rounded-2xl border border-[#1e2130] lg:col-span-2">
                    <h2 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-6 flex items-center gap-2">
                        <Activity size={16} className="text-[#00bcd4]" /> Market Context Snapshot
                    </h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                         <div className="space-y-1">
                            <p className="text-[10px] text-gray-600 font-bold uppercase">PCR</p>
                            <p className="text-xl font-black text-white">{health?.data_layer?.option_summary?.PCR || '0.0'}</p>
                         </div>
                         <div className="space-y-1">
                            <p className="text-[10px] text-gray-600 font-bold uppercase">Trend</p>
                            <p className="text-xl font-black text-[#00bcd4]">{context?.regime || 'RANGING'}</p>
                         </div>
                         <div className="space-y-1">
                            <p className="text-[10px] text-gray-600 font-bold uppercase">Volatility</p>
                            <p className="text-xl font-black text-yellow-500">{context?.vix || '0.0'}</p>
                         </div>
                         <div className="space-y-1">
                            <p className="text-[10px] text-gray-600 font-bold uppercase">Context</p>
                            <p className="text-xl font-black text-purple-400">{context?.state || 'Neutral'}</p>
                         </div>
                    </div>
                    <div className="mt-8 p-4 bg-[#0f1117] rounded-xl border border-[#1e2130]">
                        <p className="text-[10px] text-gray-600 font-bold uppercase mb-2">Options Sentiment</p>
                        <p className="text-xs text-gray-400 leading-relaxed italic">
                            {health?.data_layer?.option_summary?.CE_OI_Change} | {health?.data_layer?.option_summary?.PE_OI_Change}
                        </p>
                    </div>
                </div>

                <div className="bg-[#161b27] p-6 rounded-2xl border border-[#1e2130]">
                    <h2 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-6 flex items-center gap-2">
                        <RefreshCw size={16} className="text-[#00bcd4]" /> Active Scheduled Jobs
                    </h2>
                    <div className="space-y-3">
                        {health?.scheduler?.jobs?.map(job => (
                            <div key={job} className="flex items-center gap-3 p-3 bg-[#0f1117] rounded-lg border border-[#1e2130]">
                                <div className="w-2 h-2 rounded-full bg-green-500"></div>
                                <span className="text-xs font-bold text-gray-300">{job}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
            
            <div className="bg-[#161b27] p-6 rounded-2xl border border-[#1e2130]">
                <h2 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-6 flex items-center gap-2">
                    <AlertCircle size={16} className="text-orange-500" /> Raw System State
                </h2>
                <pre className="text-[10px] font-mono text-gray-500 bg-[#0f1117] p-4 rounded-xl overflow-auto max-h-[300px]">
                    {JSON.stringify({ health, context }, null, 2)}
                </pre>
            </div>
        </div>
    );
}

function StatusCard({ title, value, color, icon }) {
    const colorClasses = {
        green: 'text-green-500 bg-green-500/10',
        red: 'text-red-500 bg-red-500/10',
        blue: 'text-blue-400 bg-blue-400/10',
        purple: 'text-purple-400 bg-purple-400/10',
        gray: 'text-gray-500 bg-gray-500/10',
    };
    
    return (
        <div className="bg-[#161b27] p-6 rounded-2xl border border-[#1e2130] flex items-center gap-4">
            <div className={`p-3 rounded-xl ${colorClasses[color]}`}>
                {icon}
            </div>
            <div>
                <p className="text-[10px] text-gray-600 font-bold uppercase">{title}</p>
                <p className="text-lg font-black text-white">{value}</p>
            </div>
        </div>
    );
}
