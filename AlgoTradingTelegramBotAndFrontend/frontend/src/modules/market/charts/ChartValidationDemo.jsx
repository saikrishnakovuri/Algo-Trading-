import React, { useState, useEffect } from 'react';
import TradingChart from './TradingChart';
import { useMarketStore } from '../store/useMarketStore';

/**
 * High-Frequency Burst Validation Demo
 */
const ChartValidationDemo = () => {
    const updateCandle = useMarketStore(state => state.updateCandle);
    const setCandles = useMarketStore(state => state.setCandles);

    // Initialize Store with mock history
    useEffect(() => {
        const history = [];
        let time = Math.floor(Date.now() / 1000) - (50 * 5 * 60);
        let price = 22500;

        for (let i = 0; i < 50; i++) {
            history.push({ symbol: 'NIFTY', timeframe: '5m', time, open: price, high: price + 10, low: price - 10, close: price + 2 });
            price += 2;
            time += 5 * 60;
        }
        setCandles('NIFTY', '5m', history);
    }, []);

    /**
     * SIMULATE BURST
     * Dispatches 5 messages in 50ms.
     * The 3rd message contains the High extreme.
     * The 5th message contains the final Close.
     */
    const simulateBurst = () => {
        const now = Math.floor(Date.now() / 1000);
        const candleTime = now - (now % 300);
        const base = { symbol: 'NIFTY', timeframe: '5m', time: candleTime, open: 22600 };

        console.log('[Demo] STARTING 50ms BURST (5 messages)...');

        // 1. Initial State (0ms)
        updateCandle({ ...base, high: 22610, low: 22590, close: 22605 });

        // 2. Throttled (10ms)
        setTimeout(() => updateCandle({ ...base, high: 22610, low: 22590, close: 22608 }), 10);

        // 3. Throttled - THE HIGH EXTREME (20ms)
        setTimeout(() => {
            console.log('[Demo] Dispatching HIGH EXTREME (22750) - Should be captured by Trailing Update');
            updateCandle({ ...base, high: 22750, low: 22590, close: 22650 });
        }, 20);

        // 4. Throttled (30ms)
        setTimeout(() => updateCandle({ ...base, high: 22750, low: 22580, close: 22620 }), 30);

        // 5. Final State - THE FINAL CLOSE (40ms)
        setTimeout(() => {
            console.log('[Demo] Dispatching FINAL CLOSE (22550) - Should be captured by Trailing Update');
            updateCandle({ ...base, high: 22750, low: 22550, close: 22550 });
        }, 40);
    };

    return (
        <div style={{ padding: '20px', backgroundColor: '#0f1117', minHeight: '100vh', color: '#fff' }}>
            <h1>Burst & Integrity Validation</h1>
            <p>Validates that Trailing Updates capture extremes during high-frequency bursts.</p>
            
            <div style={{ margin: '20px 0' }}>
                <button 
                    onClick={simulateBurst}
                    style={{ padding: '12px 24px', backgroundColor: '#ef5350', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
                >
                    Trigger 50ms WebSocket Burst
                </button>
                <span style={{ marginLeft: '15px', fontSize: '14px', opacity: 0.8 }}>
                    Throttle is 100ms. Burst is 50ms. Trailing update will apply at ~100ms.
                </span>
            </div>

            <div style={{ marginTop: '20px' }}>
                <TradingChart symbol="NIFTY" timeframe="5m" height="600px" />
            </div>

            <div style={{ marginTop: '40px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                <div className="card" style={{ padding: '15px', border: '1px solid #2a2e39', borderRadius: '8px' }}>
                    <h3>Integrity Guarantee</h3>
                    <ul>
                        <li><b>Highs:</b> Never missed (last snapshot wins).</li>
                        <li><b>Lows:</b> Never missed (last snapshot wins).</li>
                        <li><b>Close:</b> Always latest (trailing update wins).</li>
                    </ul>
                </div>
                <div className="card" style={{ padding: '15px', border: '1px solid #2a2e39', borderRadius: '8px' }}>
                    <h3>Technical Proof</h3>
                    <p style={{ fontSize: '14px' }}>
                        If 5 snapshots arrive in 50ms, the Store processes #1 immediately, throttles #2-#5, 
                        and then automatically executes #5 as a "Trailing Update" after 100ms. 
                        Since #5 contains the cumulative High/Low of the entire burst, no data is lost.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default ChartValidationDemo;
