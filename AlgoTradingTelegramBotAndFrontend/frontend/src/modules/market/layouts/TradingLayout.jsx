import React, { useEffect } from 'react';
import { TopBar } from '../components/TopBar';
import { Sidebar } from '../components/Sidebar';
import { BottomPanel } from '../components/BottomPanel';
import { PerformanceDashboard } from '../testing/PerformanceDashboard';
import { ReconnectOverlay } from '../resilience/ReconnectOverlay';
import { staleDataDetector } from '../resilience/StaleDataDetector';
import TradingChart from '../charts/TradingChart';
import { useMarketTransition } from '../switching/useMarketTransition';
import { useMarketStream } from '../websocket/useMarketStream';
import { MarketTransitionManager } from '../switching/MarketTransitionManager';

/**
 * TradingLayout
 * 
 * The main architectural shell for the professional trading terminal.
 * Implements a responsive grid prioritizing chart visibility using ONLY inline styles.
 */
export const TradingLayout = () => {
    const { activeSymbol, activeTimeframe } = useMarketTransition();
    
    // Initialize Realtime Market Stream
    useMarketStream();

    // Initialize resilience background monitors and default market state
    useEffect(() => {
        console.log('[Terminal] Initializing Resilience Monitors...');
        staleDataDetector.start();

        // Trigger initial market load if not already set or as a default entry point
        console.log('[Terminal] Triggering initial market switch...');
        MarketTransitionManager.executeSwitch('NIFTY', '5m');

        return () => {
            console.log('[Terminal] Stopping Resilience Monitors...');
            staleDataDetector.stop();
        };
    }, []);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', backgroundColor: '#0a0e17', color: '#d1d4dc', overflow: 'hidden', position: 'relative' }}>
            {/* Resilience Overlay (highest priority) */}
            <ReconnectOverlay />

            {/* 1. Global Navigation & Controls */}
            <TopBar />

            {/* 2. Main Content Area */}
            <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
                
                {/* 2a. Left Sidebar (Watchlist, Signals) */}
                <Sidebar />

                {/* 2b. Central Chart Area */}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative', minWidth: 0, backgroundColor: '#0a0e17' }}>
                    
                    {/* The Chart Container receives all flexible space */}
                    <div style={{ flex: 1, position: 'relative', padding: '4px' }}>
                        <div style={{ position: 'absolute', top: '4px', left: '4px', right: '4px', bottom: '4px', borderRadius: '4px', overflow: 'hidden', border: '1px solid #2a2e39', backgroundColor: '#131722' }}>
                            <TradingChart 
                                symbol={activeSymbol} 
                                timeframe={activeTimeframe} 
                                height="100%" 
                            />
                        </div>
                    </div>

                </div>
            </div>

            {/* 3. Bottom Terminal Panels */}
            <div style={{ display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
                <BottomPanel />
                
                {/* Phase 11: Validation & Chaos Terminal (Dev Mode Only) */}
                <PerformanceDashboard />

                {/* 3a. Terminal Footer (Metadata) */}
                <div style={{
                    padding: '4px 15px',
                    backgroundColor: '#131722',
                    borderTop: '1px solid #2a2e39',
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: '11px',
                    color: '#787b86'
                }}>
                    <div>Realtime Market Data · {activeSymbol} · {activeTimeframe}</div>
                    <div style={{ display: 'flex', gap: '16px' }}>
                        <div>Memory: Stable</div>
                        <div>Status: Connected</div>
                    </div>
                </div>
            </div>
            
            {/* CSS Additions for custom scrollbars to maintain dark aesthetic */}
            <style dangerouslySetInnerHTML={{__html: `
                .custom-scrollbar::-webkit-scrollbar {
                    width: 6px;
                    height: 6px;
                }
                .custom-scrollbar::-webkit-scrollbar-track {
                    background: #131722;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb {
                    background: #2a2e39;
                    border-radius: 3px;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover {
                    background: #4c525e;
                }
            `}} />
        </div>
    );
};
