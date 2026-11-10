/**
 * @file TradingChart.jsx
 * @description Refined TradingChart component that reads from Zustand store.
 */

import React, { useEffect, useRef, memo } from 'react';
import { chartConfig } from './chartConfig';
import { chartTheme } from './chartTheme';
import { ChartLifecycle } from './ChartLifecycle';
import { CandleSeriesManager } from './CandleSeriesManager';
import { useMarketStore } from '../store/useMarketStore';
import { selectLatestCandle } from '../store/marketSelectors';

/**
 * TradingChart Component
 * 
 * Responsibilities:
 * - Initialize TradingView Lightweight Chart
 * - Manage chart lifecycle
 * - PERFORMANCE: Throttled updates via requestAnimationFrame (RAF).
 * - PERFORMANCE: Only the latest candle triggers reactive updates.
 * - PERFORMANCE: Reactively populates history when transition manager completes.
 * - SAFETY: Clears pending store timers on unmount.
 */
const TradingChart = memo(({ 
    symbol = 'NIFTY', 
    timeframe = '5m', 
    height = '500px' 
}) => {
    const chartContainerRef = useRef(null);
    const chartRef = useRef(null);
    const candleSeriesRef = useRef(null);
    const seriesManagerRef = useRef(null);
    const rafIdRef = useRef(null);

    // 1. Reactive hooks
    const latestCandle = useMarketStore(selectLatestCandle(symbol, timeframe));
    const transitionStatus = useMarketStore(state => state.transitionStatus);
    const historyCount = useMarketStore(state => state.candles[symbol]?.[timeframe]?.length || 0);
    const clearPendingUpdates = useMarketStore(state => state.clearPendingUpdates);

    // Effect: Initialize Chart (Singleton Infrastructure)
    useEffect(() => {
        console.log(`%c[TradingChart] MOUNTED for ${symbol}`, 'background: #222; color: #bada55; font-size: 14px');
        if (!chartContainerRef.current) {
            console.error('[TradingChart] FAILED: containerRef is null');
            return;
        }

        console.log(`[TradingChart] INITIALIZING singleton chart for ${symbol}...`);
        console.log('[TradingChart] Container Dimensions:', {
            width: chartContainerRef.current.clientWidth,
            height: chartContainerRef.current.clientHeight
        });

        const { chart, candleSeries } = ChartLifecycle.init(
            chartContainerRef.current,
            chartConfig,
            chartTheme
        );

        if (!chart || !candleSeries) {
            console.error('[TradingChart] Chart initialization failed - skipping series setup');
            return;
        }

        chartRef.current = chart;
        candleSeriesRef.current = candleSeries;
        seriesManagerRef.current = new CandleSeriesManager(candleSeries);

        // Load whatever history is ALREADY in the store
        const currentStore = useMarketStore.getState();
        const initialHistory = currentStore.candles[symbol]?.[timeframe] || [];

        if (initialHistory.length > 0) {
            seriesManagerRef.current.setInitialData(initialHistory);
            chart.timeScale().fitContent();
        }

        const cleanupResize = ChartLifecycle.registerResizeHandler(chart, chartContainerRef.current);

        return () => {
            console.log(`[TradingChart] CLEANUP lifecycle for ${symbol}`);
            if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current);
            cleanupResize();
            ChartLifecycle.destroy(chart);
            if (clearPendingUpdates) {
                clearPendingUpdates(symbol, timeframe);
            }
            chartRef.current = null;
            candleSeriesRef.current = null;
            seriesManagerRef.current = null;
        };
    }, [symbol, timeframe]);

    // Effect: History Sync (Triggers when TransitionManager loads history)
    useEffect(() => {
        if (seriesManagerRef.current && historyCount > 0) {
            const currentHistory = useMarketStore.getState().candles[symbol][timeframe];
            // Use setInitialData (setData) for the bulk history load
            seriesManagerRef.current.setInitialData(currentHistory);
            if (chartRef.current) {
                chartRef.current.timeScale().fitContent();
            }
        }
    }, [historyCount, symbol, timeframe]);

    // Effect: Incremental Update (Consume latest candle from store)
    useEffect(() => {
        if (seriesManagerRef.current && latestCandle) {
            if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current);

            rafIdRef.current = requestAnimationFrame(() => {
                if (seriesManagerRef.current) {
                    seriesManagerRef.current.updateCandle(latestCandle);
                }
                rafIdRef.current = null;
            });
        }
    }, [latestCandle]);

    const isTransitioning = transitionStatus !== 'READY' && transitionStatus !== 'IDLE' && transitionStatus !== 'ERROR';

    return (
        <div 
            className="trading-chart-wrapper"
            style={{ 
                width: '100%', 
                height: height, 
                position: 'relative',
                backgroundColor: chartTheme.dark.background,
                borderRadius: '8px',
                overflow: 'hidden',
                border: '1px solid #2a2e39'
            }}
        >
            <div 
                ref={chartContainerRef} 
                className="trading-chart-container"
                style={{ width: '100%', height: '100%' }}
            />
            
            {/* Loading Overlay */}
            {isTransitioning && (
                <div style={{
                    position: 'absolute',
                    top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(19, 23, 34, 0.7)',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 20,
                    color: '#fff',
                    fontFamily: chartConfig.layout.fontFamily
                }}>
                    <div className="spinner" style={{ marginBottom: '10px' }}>Syncing...</div>
                    <div style={{ fontSize: '12px', opacity: 0.7 }}>{transitionStatus}</div>
                </div>
            )}

            <div style={{
                position: 'absolute',
                top: '12px',
                left: '12px',
                zIndex: 10,
                color: chartTheme.dark.text,
                fontSize: '14px',
                fontWeight: 'bold',
                pointerEvents: 'none',
                fontFamily: chartConfig.layout.fontFamily
            }}>
                {symbol} · {timeframe} 
            </div>

            {/* DEBUG OVERLAY */}
            <div style={{
                position: 'absolute',
                top: '50px',
                left: '12px',
                zIndex: 100,
                background: 'rgba(255, 0, 0, 0.8)',
                color: 'white',
                padding: '5px',
                fontSize: '10px',
                borderRadius: '4px',
                pointerEvents: 'none'
            }}>
                DEBUG: Chart Wrapper Active | History: {historyCount} | Transition: {transitionStatus}
            </div>
        </div>
    );
}, (prevProps, nextProps) => {
    // Only re-render if the core identity props change.
    // The component manages its own reactive data updates via Zustand selectors,
    // so it doesn't need to re-render when a parent re-renders.
    return prevProps.symbol === nextProps.symbol && prevProps.timeframe === nextProps.timeframe;
});

TradingChart.displayName = 'TradingChart';
export default TradingChart;
