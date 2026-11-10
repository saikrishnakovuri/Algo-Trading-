import React, { useState } from 'react';
import TradingChart from './TradingChart';
import { useMarketStore } from '../store/useMarketStore';
import { MarketTransitionManager } from '../switching/MarketTransitionManager';

/**
 * Transition Race Condition Validation Demo
 */
const TransitionValidationDemo = () => {
    const [testRunning, setTestRunning] = useState(false);
    const activeSymbol = useMarketStore(state => state.activeSymbol);
    const activeTimeframe = useMarketStore(state => state.activeTimeframe);
    const transitionStatus = useMarketStore(state => state.transitionStatus);

    /**
     * SIMULATE RAPID USER CLICKS
     * NIFTY -> BANKNIFTY -> FINNIFTY -> MIDCPNIFTY -> NIFTY (1h)
     * All triggered within 200ms, while REST fetches take > 500ms.
     */
    const runRaceTest = async () => {
        setTestRunning(true);
        console.log("==========================================");
        console.log("[Test] STARTING RAPID SWITCHING RACE TEST");
        console.log("==========================================");

        // 1. Switch to BANKNIFTY
        MarketTransitionManager.executeSwitch('BANKNIFTY', '5m');
        
        await new Promise(r => setTimeout(r, 50)); // User hesitates for 50ms

        // 2. Switch to FINNIFTY
        MarketTransitionManager.executeSwitch('FINNIFTY', '5m');

        await new Promise(r => setTimeout(r, 50));

        // 3. Switch to MIDCPNIFTY
        MarketTransitionManager.executeSwitch('MIDCPNIFTY', '15m');

        await new Promise(r => setTimeout(r, 50));

        // 4. Final intentional target: NIFTY 1h
        console.log("[Test] Firing final authoritative request: NIFTY 1h");
        MarketTransitionManager.executeSwitch('NIFTY', '1h');

        setTimeout(() => {
            console.log("==========================================");
            console.log("[Test] RACE TEST COMPLETE. Check logs for 'ABORTED stale transition'.");
            console.log("==========================================");
            setTestRunning(false);
        }, 3000); // Give time for all simulated slow networks to resolve
    };

    return (
        <div style={{ padding: '20px', backgroundColor: '#0f1117', minHeight: '100vh', color: '#fff' }}>
            <h1>Transition Race Safety Validation</h1>
            <p>Validates that rapid switching does not cause stale REST fetches to overwrite the final active stream.</p>
            
            <div style={{ margin: '20px 0', display: 'flex', gap: '15px' }}>
                <button 
                    onClick={runRaceTest}
                    disabled={testRunning}
                    style={{ padding: '12px 24px', backgroundColor: testRunning ? '#4c525e' : '#ef5350', color: 'white', border: 'none', borderRadius: '4px', cursor: testRunning ? 'not-allowed' : 'pointer', fontWeight: 'bold' }}
                >
                    {testRunning ? 'Running Test...' : 'Trigger Rapid Switch Stress Test'}
                </button>
                <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                    <span style={{ fontSize: '14px', color: '#26a69a' }}>Current State: {activeSymbol} ({activeTimeframe})</span>
                    <span style={{ fontSize: '12px', opacity: 0.7 }}>Status: {transitionStatus}</span>
                </div>
            </div>

            <div style={{ marginTop: '20px' }}>
                <TradingChart symbol={activeSymbol} timeframe={activeTimeframe} height="500px" />
            </div>

            <div style={{ marginTop: '40px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                <div className="card" style={{ padding: '15px', border: '1px solid #2a2e39', borderRadius: '8px' }}>
                    <h3>The Vulnerability (Without Tokens)</h3>
                    <p style={{ fontSize: '13px', opacity: 0.9 }}>
                        If a user clicks NIFTY, then BANKNIFTY rapidly:
                        <br/>1. NIFTY fetch starts (takes 1000ms).
                        <br/>2. BANKNIFTY fetch starts (takes 500ms).
                        <br/>3. BANKNIFTY resolves, chart loads BANKNIFTY.
                        <br/>4. NIFTY fetch resolves late, overwrites BANKNIFTY chart.
                        <br/><span style={{ color: '#ef5350' }}>Result: Chart shows NIFTY data, but UI says BANKNIFTY. WebSocket subscribes to NIFTY again.</span>
                    </p>
                </div>
                <div className="card" style={{ padding: '15px', border: '1px solid #2a2e39', borderRadius: '8px' }}>
                    <h3>The Solution (Transition Tokens)</h3>
                    <p style={{ fontSize: '13px', opacity: 0.9 }}>
                        Every switch generates a unique <code>transitionToken</code>. 
                        When an async REST fetch completes, it checks if its token still matches the global store token. 
                        If the user clicked elsewhere, the store token changed, and the old async fetch is safely ABORTED.
                        <br/><span style={{ color: '#26a69a' }}>Result: Mathematical guarantee that ONLY the final intended switch executes a WebSocket subscribe and Chart sync.</span>
                    </p>
                </div>
            </div>
        </div>
    );
};

export default TransitionValidationDemo;
