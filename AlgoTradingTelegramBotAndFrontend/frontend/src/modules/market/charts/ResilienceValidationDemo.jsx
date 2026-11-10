import React, { useState } from 'react';
import { useMarketStore } from '../store/useMarketStore';
import { reconnectEngine } from '../resilience/ReconnectEngine';
import { MarketTransitionManager } from '../switching/MarketTransitionManager';
import TradingChart from './TradingChart';

/**
 * Resilience Engineering Validation Demo
 */
const ResilienceValidationDemo = () => {
    const [log, setLog] = useState([]);
    const status = useMarketStore(state => state.connectionStatus);
    const isOffline = useMarketStore(state => state.isBrowserOffline);
    const setStatus = useMarketStore(state => state.setConnectionStatus);
    const setOffline = useMarketStore(state => state.setBrowserOffline);

    const addLog = (msg) => {
        setLog(prev => [`${new Date().toLocaleTimeString()} - ${msg}`, ...prev.slice(0, 10)]);
        console.log(`[ResilienceTest] ${msg}`);
    };

    /**
     * TEST 1: Simulate Socket Drop
     */
    const simulateDrop = () => {
        addLog("Simulating WebSocket DROP...");
        setStatus('DISCONNECTED');
        reconnectEngine.handleDisconnect();
    };

    /**
     * TEST 2: Simulate Stale Feed
     * We don't update heartbeat for 15s. StaleDataDetector should catch it.
     */
    const simulateStale = () => {
        addLog("Simulating STALE feed (freezing heartbeats)...");
        // StaleDataDetector runs every 5s, threshold 15s.
        // In this demo, we'll just force the state to show the UI reaction.
        setStatus('STALE');
        setTimeout(() => reconnectEngine.handleDisconnect(), 2000);
    };

    /**
     * TEST 3: Simulate Browser Offline
     */
    const simulateOffline = () => {
        addLog("Simulating Browser OFFLINE...");
        setOffline(true);
        setStatus('DISCONNECTED');
    };

    /**
     * TEST 4: Race Condition during Recovery
     * Trigger recovery, then immediately switch symbol.
     * Recovery should ABORT due to token mismatch.
     */
    const simulateRecoveryRace = async () => {
        addLog("Starting Recovery Race Test...");
        
        // 1. Enter Reconnecting
        setStatus('RECONNECTING');
        
        // 2. Trigger a "Recovery" that takes time
        addLog("Triggering slow recovery for NIFTY...");
        reconnectEngine.handleSuccess(); // This calls StreamRecoveryManager.recover()

        // 3. IMMEDIATELY switch symbol (User clicks BANKNIFTY)
        setTimeout(() => {
            addLog("USER INTERVENTION: Switching to BANKNIFTY during recovery!");
            MarketTransitionManager.executeSwitch('BANKNIFTY', '5m');
        }, 100);
    };

    return (
        <div className="p-8 bg-[#0a0e17] min-h-screen text-[#d1d4dc] font-mono relative">
            {/* The actual ReconnectOverlay should be tested here */}
            {/* But since this is a demo file, we'll just look at the logs and chart stability */}
            
            <h1 className="text-2xl font-bold mb-4 text-white">Resilience Engineering Audit</h1>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
                <div className="space-y-4 bg-[#131722] p-6 rounded-lg border border-[#2a2e39]">
                    <h3 className="text-lg font-semibold text-[#2962ff]">Chaos Triggers</h3>
                    <div className="grid grid-cols-2 gap-3">
                        <button onClick={simulateDrop} className="px-4 py-2 bg-[#ef5350] hover:bg-[#ef5350]/80 rounded font-bold text-white text-xs">
                            Drop WebSocket
                        </button>
                        <button onClick={simulateStale} className="px-4 py-2 bg-[#f57c00] hover:bg-[#f57c00]/80 rounded font-bold text-white text-xs">
                            Freeze Feed
                        </button>
                        <button onClick={simulateOffline} className="px-4 py-2 bg-[#787b86] hover:bg-[#787b86]/80 rounded font-bold text-white text-xs">
                            Toggle Offline
                        </button>
                        <button onClick={simulateRecoveryRace} className="px-4 py-2 bg-[#2962ff] hover:bg-[#2962ff]/80 rounded font-bold text-white text-xs">
                            Recovery Race
                        </button>
                    </div>

                    <div className="mt-6">
                        <h4 className="text-xs uppercase text-[#787b86] mb-2">Live Logs</h4>
                        <div className="bg-[#0a0e17] p-3 rounded h-48 overflow-y-auto border border-[#2a2e39] text-[10px]">
                            {log.map((l, i) => <div key={i} className="mb-1">{l}</div>)}
                        </div>
                    </div>
                </div>

                <div className="space-y-4 bg-[#131722] p-6 rounded-lg border border-[#2a2e39]">
                    <h3 className="text-lg font-semibold text-[#26a69a]">Status Monitor</h3>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="p-3 bg-[#0a0e17] rounded border border-[#2a2e39]">
                            <div className="text-[10px] text-[#787b86] uppercase">Status</div>
                            <div className="text-sm font-bold mt-1 text-white">{status}</div>
                        </div>
                        <div className="p-3 bg-[#0a0e17] rounded border border-[#2a2e39]">
                            <div className="text-[10px] text-[#787b86] uppercase">Network</div>
                            <div className="text-sm font-bold mt-1 text-white">{isOffline ? 'OFFLINE' : 'ONLINE'}</div>
                        </div>
                    </div>
                    
                    <div className="mt-4 p-4 border border-[#26a69a]/20 bg-[#26a69a]/5 rounded text-xs text-[#26a69a]">
                        <b>Engineering Guarantees:</b>
                        <ul className="list-disc ml-4 mt-2 space-y-1 opacity-90">
                            <li>Deterministic Recovery (Token-Aware)</li>
                            <li>Exponential Backoff (No Storms)</li>
                            <li>Duplicate Stream Prevention</li>
                            <li>Stale Feed Auto-Detection</li>
                        </ul>
                    </div>
                </div>
            </div>

            <div className="h-[400px] rounded-xl border border-[#2a2e39] overflow-hidden shadow-2xl">
                <TradingChart symbol="NIFTY" timeframe="5m" height="100%" />
            </div>
        </div>
    );
};

export default ResilienceValidationDemo;
