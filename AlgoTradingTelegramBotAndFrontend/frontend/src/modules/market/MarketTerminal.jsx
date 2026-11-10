import React from 'react';
import MarketToolbar from './components/MarketToolbar';
import TradingChart from './charts/TradingChart';
import { useMarketTransition } from './switching/useMarketTransition';

/**
 * MarketTerminal
 * 
 * The main container for the professional trading terminal.
 * Orchestrates the relationship between market controls and the chart engine.
 */
const MarketTerminal = () => {
    const { activeSymbol, activeTimeframe } = useMarketTransition();

    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            width: '100%',
            height: '100%',
            backgroundColor: '#0f1117',
            overflow: 'hidden'
        }}>
            {/* 1. Global Market Controls */}
            <MarketToolbar />

            {/* 2. Primary Visualization Layer */}
            <div style={{ flex: 1, padding: '10px', position: 'relative' }}>
                <TradingChart 
                    symbol={activeSymbol} 
                    timeframe={activeTimeframe} 
                    height="100%" 
                />
            </div>

            {/* 3. Terminal Footer (Metadata) */}
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
                <div>Status: Connected</div>
            </div>
        </div>
    );
};

export default MarketTerminal;
