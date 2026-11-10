import React, { useState, useEffect } from 'react';
import { useMarketStore } from '../store/useMarketStore';
import { mockServer } from '../testing/MockWebSocketServer';
import { MarketStressGenerator } from '../testing/MarketStressGenerator';
import { FPSMonitor } from '../performance/FPSMonitor';
import { Gauge, Zap, AlertOctagon, Terminal } from 'lucide-react';

/**
 * Performance & Chaos Dashboard
 * 
 * Central control panel for Phase 11 validation.
 * Displays real-time metrics and chaos triggers.
 */
export const PerformanceDashboard = () => {
    const status = useMarketStore(state => state.connectionStatus);
    const reconnectCount = useMarketStore(state => state.reconnectAttempt);
    const activeSymbol = useMarketStore(state => state.activeSymbol);
    
    const [msgPerSec, setMsgPerSec] = useState(0);
    const [lastCount, setLastCount] = useState(0);

    // Calculate Messages Per Second
    useEffect(() => {
        const interval = setInterval(() => {
            const current = mockServer.msgCount;
            setMsgPerSec(current - lastCount);
            setLastCount(current);
        }, 1000);
        return () => clearInterval(interval);
    }, [lastCount]);

    return (
        <div className="bg-[#131722] border-t border-[#2a2e39] p-4 text-[#d1d4dc] font-mono">
            <div className="flex items-center gap-6 mb-6">
                <div className="flex items-center gap-2 text-white font-bold">
                    <Terminal size={18} className="text-[#2962ff]" />
                    <span>CHAOS TERMINAL V1.0</span>
                </div>
                <div className="h-4 w-px bg-[#2a2e39]" />
                <FPSMonitor />
                <div className="flex items-center gap-2 px-3 py-1 bg-[#0a0e17] rounded border border-[#2a2e39]">
                    <Zap size={14} className="text-[#f57c00]" />
                    <span className="text-xs">{msgPerSec} MSG/SEC</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1 bg-[#0a0e17] rounded border border-[#2a2e39]">
                    <span className="text-xs uppercase opacity-60">Status:</span>
                    <span className="text-xs font-bold text-[#26a69a]">{status}</span>
                </div>
            </div>

            <div className="grid grid-cols-4 gap-4">
                {/* Simulation Controls */}
                <div className="bg-[#0a0e17] p-4 rounded border border-[#2a2e39]">
                    <h4 className="text-[10px] uppercase text-[#787b86] mb-3 font-bold">Simulation</h4>
                    <div className="space-y-2">
                        <button 
                            onClick={() => mockServer.start()} 
                            className="w-full text-left px-3 py-1.5 bg-[#1e222d] hover:bg-[#2a2e39] rounded text-xs"
                        >
                            ▶ Start Mock Stream
                        </button>
                        <button 
                            onClick={() => mockServer.stop()} 
                            className="w-full text-left px-3 py-1.5 bg-[#1e222d] hover:bg-[#2a2e39] rounded text-xs text-[#ef5350]"
                        >
                            ■ Stop All Streams
                        </button>
                    </div>
                </div>

                {/* Chaos Triggers */}
                <div className="bg-[#0a0e17] p-4 rounded border border-[#2a2e39]">
                    <h4 className="text-[10px] uppercase text-[#787b86] mb-3 font-bold">Chaos Injection</h4>
                    <div className="space-y-2">
                        <button 
                            onClick={() => mockServer.simulateDisconnect()} 
                            className="w-full text-left px-3 py-1.5 bg-[#ef5350]/10 hover:bg-[#ef5350]/20 border border-[#ef5350]/30 rounded text-xs text-[#ef5350]"
                        >
                            ⚡ Inject Disconnect
                        </button>
                        <button 
                            onClick={() => MarketStressGenerator.runRapidNavigation()} 
                            className="w-full text-left px-3 py-1.5 bg-[#2962ff]/10 hover:bg-[#2962ff]/20 border border-[#2962ff]/30 rounded text-xs text-[#2962ff]"
                        >
                            🌀 Rapid Nav Stress
                        </button>
                    </div>
                </div>

                {/* Load Scenarios */}
                <div className="bg-[#0a0e17] p-4 rounded border border-[#2a2e39]">
                    <h4 className="text-[10px] uppercase text-[#787b86] mb-3 font-bold">Load Scenarios</h4>
                    <div className="space-y-2">
                        <button 
                            onClick={() => MarketStressGenerator.runOpeningBell()} 
                            className="w-full text-left px-3 py-1.5 bg-[#26a69a]/10 hover:bg-[#26a69a]/20 border border-[#26a69a]/30 rounded text-xs text-[#26a69a]"
                        >
                            🔔 Opening Bell (50Hz)
                        </button>
                        <button 
                            onClick={() => MarketStressGenerator.runExtremeLoad()} 
                            className="w-full text-left px-3 py-1.5 bg-[#ef5350]/10 hover:bg-[#ef5350]/20 border border-[#ef5350]/30 rounded text-xs text-[#ef5350]"
                        >
                            🔥 Extreme (1000Hz+)
                        </button>
                    </div>
                </div>

                {/* Health Metrics */}
                <div className="bg-[#0a0e17] p-4 rounded border border-[#2a2e39]">
                    <h4 className="text-[10px] uppercase text-[#787b86] mb-3 font-bold">Health Audit</h4>
                    <div className="text-[11px] space-y-1">
                        <div className="flex justify-between">
                            <span className="opacity-60">Reconnects:</span>
                            <span className={reconnectCount > 0 ? 'text-[#f57c00]' : ''}>{reconnectCount}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="opacity-60">Active:</span>
                            <span className="text-white">{activeSymbol}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="opacity-60">Total Events:</span>
                            <span className="text-[#26a69a]">{mockServer.msgCount.toLocaleString()}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
