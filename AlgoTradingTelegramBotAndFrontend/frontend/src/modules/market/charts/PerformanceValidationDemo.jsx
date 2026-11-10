import React, { useState, useEffect } from 'react';
import TradingChart from './TradingChart';
import { useMarketStore } from '../store/useMarketStore';

/**
 * High-Frequency Performance Validation Demo
 */
const PerformanceValidationDemo = () => {
    const [testRunning, setTestRunning] = useState(false);
    const updateCandle = useMarketStore(state => state.updateCandle);
    const setCandles = useMarketStore(state => state.setCandles);

    // Initialize Store with mock history
    useEffect(() => {
        const history = [];
        let time = Math.floor(Date.now() / 1000) - (500 * 5 * 60);
        let price = 22500;

        for (let i = 0; i < 500; i++) {
            history.push({ symbol: 'NIFTY', timeframe: '5m', time, open: price, high: price + 10, low: price - 10, close: price + 2 });
            price += 2;
            time += 5 * 60;
        }
        setCandles('NIFTY', '5m', history);
    }, []);

    /**
     * SIMULATE EXTREME HIGH-FREQUENCY BURST
     * Dispatches 1000 updates in 2 seconds (500 updates/sec).
     * Validates that React does not crash and TradingView remains responsive via RAF and Store throttling.
     */
    const runStressTest = () => {
        setTestRunning(true);
        console.log("==========================================");
        console.log("[Test] STARTING EXTREME 500 MSG/SEC STRESS TEST");
        console.log("==========================================");

        const now = Math.floor(Date.now() / 1000);
        const candleTime = now - (now % 300);
        const base = { symbol: 'NIFTY', timeframe: '5m', time: candleTime, open: 22600 };

        let count = 0;
        const totalMessages = 1000;
        const durationMs = 2000;
        const intervalMs = durationMs / totalMessages;

        const intervalId = setInterval(() => {
            count++;
            
            // Random walk price
            const noise = (Math.random() - 0.5) * 5;
            const newClose = 22600 + noise;
            
            // Dispatch to store. This tests the store's 100ms throttle.
            updateCandle({ ...base, high: 22650, low: 22550, close: newClose });

            if (count >= totalMessages) {
                clearInterval(intervalId);
                console.log("==========================================");
                console.log(`[Test] FINISHED processing ${totalMessages} messages.`);
                console.log("==========================================");
                setTestRunning(false);
            }
        }, intervalMs);
    };

    return (
        <div style={{ padding: '20px', backgroundColor: '#0f1117', minHeight: '100vh', color: '#fff' }}>
            <h1>Performance Optimization Validation</h1>
            <p>Validates that React memoization, Store Throttling, and RAF keep the UI stable under extreme load.</p>
            
            <div style={{ margin: '20px 0', display: 'flex', gap: '15px' }}>
                <button 
                    onClick={runStressTest}
                    disabled={testRunning}
                    style={{ padding: '12px 24px', backgroundColor: testRunning ? '#4c525e' : '#ef5350', color: 'white', border: 'none', borderRadius: '4px', cursor: testRunning ? 'not-allowed' : 'pointer', fontWeight: 'bold' }}
                >
                    {testRunning ? 'Running Stress Test...' : 'Trigger 500 Updates/Sec Burst (2s)'}
                </button>
            </div>

            <div style={{ marginTop: '20px' }}>
                <TradingChart symbol="NIFTY" timeframe="5m" height="500px" />
            </div>

            <div style={{ marginTop: '40px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                <div className="card" style={{ padding: '15px', border: '1px solid #2a2e39', borderRadius: '8px' }}>
                    <h3>Performance Protections</h3>
                    <ul>
                        <li><b>React.memo():</b> TopBar, Sidebars, and Charts ignore state changes unless their specific props change.</li>
                        <li><b>Store Throttling:</b> Zustand drops redundant tick events within a 100ms window, firing only a trailing update.</li>
                        <li><b>RAF Rendering:</b> The chart component uses <code>requestAnimationFrame</code> to limit native library calls to 60fps.</li>
                    </ul>
                </div>
                <div className="card" style={{ padding: '15px', border: '1px solid #2a2e39', borderRadius: '8px' }}>
                    <h3>Expected Results</h3>
                    <p style={{ fontSize: '13px', opacity: 0.9 }}>
                        1. FPS Monitor (top bar) should remain mostly stable (55-60 FPS).<br/>
                        2. The UI should remain perfectly responsive; buttons shouldn't freeze.<br/>
                        3. The Chart price line should animate smoothly at 10Hz (100ms throttle), despite receiving 500 messages per second.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default PerformanceValidationDemo;
