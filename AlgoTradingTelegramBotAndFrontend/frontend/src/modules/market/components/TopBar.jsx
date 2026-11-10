import React, { memo } from 'react';
import { useMarketTransition } from '../switching/useMarketTransition';
import { ConnectionIndicator } from './ConnectionIndicator';
import { FPSMonitor } from '../performance/FPSMonitor';
import { Activity, LayoutDashboard, Settings } from 'lucide-react';

export const TopBar = memo(() => {
    // The TopBar currently uses useMarketTransition, which subscribes to transitionStatus.
    // It will only re-render when the transition state or active symbol/timeframe changes.
    // It will NOT re-render on every candle update, saving CPU.
    const { 
        activeSymbol, 
        activeTimeframe, 
        switchSymbol, 
        switchTimeframe,
        isTransitioning 
    } = useMarketTransition();

    const symbols = ['NIFTY', 'BANKNIFTY', 'FINNIFTY'];
    const timeframes = ['1m', '5m', '15m', '1h', '1D'];

    return (
        <div className="h-14 flex items-center justify-between px-4 border-b border-[#2a2e39] bg-[#131722] text-[#d1d4dc] shrink-0">
            {/* Left: Brand / Connection */}
            <div className="flex items-center gap-6">
                <div className="flex items-center gap-2 font-bold text-white tracking-wider">
                    <Activity size={18} className="text-[#2962ff]" />
                    <span>ALGO<span className="text-[#2962ff]">TERMINAL</span></span>
                </div>
                <div className="h-4 w-px bg-[#2a2e39]" />
                <ConnectionIndicator />
                <div className="h-4 w-px bg-[#2a2e39]" />
                <FPSMonitor />
            </div>

            {/* Center: Market Controls */}
            <div className="flex items-center gap-6">
                {/* Symbol Selector */}
                <div className="flex bg-[#0a0e17] p-1 rounded-md border border-[#2a2e39]">
                    {symbols.map(s => (
                        <button
                            key={s}
                            disabled={isTransitioning}
                            onClick={() => switchSymbol(s)}
                            className={`px-4 py-1 text-sm font-medium rounded transition-colors ${
                                activeSymbol === s 
                                    ? 'bg-[#2a2e39] text-white shadow-sm' 
                                    : 'text-[#787b86] hover:text-[#d1d4dc] hover:bg-[#1e222d]'
                            } ${isTransitioning ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                        >
                            {s}
                        </button>
                    ))}
                </div>

                {/* Timeframe Selector */}
                <div className="flex bg-[#0a0e17] p-1 rounded-md border border-[#2a2e39]">
                    {timeframes.map(tf => (
                        <button
                            key={tf}
                            disabled={isTransitioning}
                            onClick={() => switchTimeframe(tf)}
                            className={`px-3 py-1 text-sm font-medium rounded transition-colors ${
                                activeTimeframe === tf 
                                    ? 'bg-[#2962ff] text-white shadow-sm' 
                                    : 'text-[#787b86] hover:text-[#d1d4dc] hover:bg-[#1e222d]'
                            } ${isTransitioning ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                        >
                            {tf}
                        </button>
                    ))}
                </div>
            </div>

            {/* Right: Tools */}
            <div className="flex items-center gap-4 text-[#787b86]">
                <button className="hover:text-white transition-colors p-2 rounded hover:bg-[#1e222d]">
                    <LayoutDashboard size={18} />
                </button>
                <button className="hover:text-white transition-colors p-2 rounded hover:bg-[#1e222d]">
                    <Settings size={18} />
                </button>
            </div>
        </div>
    );
});

TopBar.displayName = 'TopBar';
