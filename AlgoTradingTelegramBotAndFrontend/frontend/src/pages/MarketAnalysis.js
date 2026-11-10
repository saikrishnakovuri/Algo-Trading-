import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  Layers, 
  TrendingUp, 
  Target,
  RefreshCw,
  Search
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
const API_BASE = `${BACKEND_URL}/api`;

export default function MarketAnalysis() {
    const [indicators, setIndicators] = useState(null);
    const [smc, setSmc] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [iRes, sRes] = await Promise.all([
                fetch(`${API_BASE}/analysis/indicators`),
                fetch(`${API_BASE}/analysis/smc`)
            ]);
            if (iRes.ok) setIndicators(await iRes.json());
            if (sRes.ok) setSmc(await sRes.json());
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    return (
        <div className="p-8 space-y-8 text-gray-100">
             <div className="flex justify-between items-center">
                <h1 className="text-2xl font-bold text-white uppercase tracking-widest flex items-center gap-3">
                    <BarChart3 size={28} className="text-[#00bcd4]" /> Market Analysis Engine
                </h1>
                <button 
                    onClick={fetchData}
                    className="bg-[#161b27] hover:bg-gray-800 text-gray-400 font-bold px-6 py-2 rounded-lg border border-[#1e2130] flex items-center gap-2 text-xs"
                >
                    <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> REFRESH ANALYSIS
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Technical Indicators */}
                <div className="bg-[#161b27] p-6 rounded-2xl border border-[#1e2130]">
                    <h2 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-6 flex items-center gap-2">
                        <TrendingUp size={16} className="text-green-500" /> Technical Indicators
                    </h2>
                    <div className="space-y-6">
                        <IndicatorRow label="RSI (14)" value={indicators?.rsi?.toFixed(2)} status={indicators?.rsi > 70 ? 'Overbought' : indicators?.rsi < 30 ? 'Oversold' : 'Neutral'} />
                        <IndicatorRow label="VIX Volatility" value={indicators?.vix} status={indicators?.vix > 20 ? 'High' : 'Normal'} />
                        <IndicatorRow label="Trend Regime" value={indicators?.regime} status="Confirmed" />
                    </div>
                </div>

                {/* SMC structure */}
                <div className="bg-[#161b27] p-6 rounded-2xl border border-[#1e2130]">
                    <h2 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-6 flex items-center gap-2">
                        <Layers size={16} className="text-purple-500" /> Smart Money Concepts (SMC)
                    </h2>
                    <div className="space-y-4">
                        <div className="p-4 bg-[#0f1117] rounded-xl border border-[#1e2130]">
                            <p className="text-[10px] text-gray-600 font-bold uppercase mb-1">Market Structure</p>
                            <p className="text-xl font-black text-[#00bcd4]">{smc?.structure || 'BULLISH'}</p>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="p-4 bg-[#0f1117] rounded-xl border border-[#1e2130]">
                                <p className="text-[10px] text-gray-600 font-bold uppercase mb-1">Supply Zones</p>
                                <p className="text-lg font-bold text-red-400">{smc?.zones?.filter(z=>z.type==='supply').length || 0} Found</p>
                            </div>
                            <div className="p-4 bg-[#0f1117] rounded-xl border border-[#1e2130]">
                                <p className="text-[10px] text-gray-600 font-bold uppercase mb-1">Demand Zones</p>
                                <p className="text-lg font-bold text-green-400">{smc?.zones?.filter(z=>z.type==='demand').length || 0} Found</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            {/* SEARCH / SCANNER PLACEHOLDER */}
            <div className="bg-[#161b27] p-8 rounded-2xl border border-dashed border-[#1e2130] text-center space-y-4">
                <Search size={48} className="mx-auto text-gray-700" />
                <h3 className="text-xl font-bold text-gray-500 uppercase tracking-widest">Multi-Symbol Scanner</h3>
                <p className="text-sm text-gray-600 max-w-md mx-auto">Select symbols from your universe to run deep pattern analysis across 48 strategies in real-time.</p>
                <button className="bg-gray-800 text-gray-500 font-bold px-8 py-3 rounded-xl border border-[#1e2130] cursor-not-allowed">COMING SOON</button>
            </div>
        </div>
    );
}

function IndicatorRow({ label, value, status }) {
    return (
        <div className="flex justify-between items-center p-3 bg-[#0f1117] rounded-lg border border-[#1e2130]">
            <div>
                <p className="text-xs font-bold text-white">{label}</p>
                <p className="text-[10px] text-gray-500 uppercase">{status}</p>
            </div>
            <p className="text-lg font-mono font-bold text-[#00bcd4]">{value || '0.00'}</p>
        </div>
    );
}
