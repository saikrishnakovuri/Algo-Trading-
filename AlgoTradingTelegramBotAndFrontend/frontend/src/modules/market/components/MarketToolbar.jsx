import React, { memo } from 'react';
import { useMarketTransition } from '../switching/useMarketTransition';

/**
 * MarketToolbar
 * 
 * Provides UI controls for switching symbols and timeframes.
 * Integrates with useMarketTransition for coordinated stack-wide updates.
 */
export const MarketToolbar = memo(() => {
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
        <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '20px',
            padding: '10px 15px',
            backgroundColor: '#131722',
            borderBottom: '1px solid #2a2e39',
            color: '#d1d4dc',
            fontSize: '14px'
        }}>
            {/* Symbol Selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ opacity: 0.6 }}>Symbol:</span>
                <div style={{ display: 'flex', gap: '4px' }}>
                    {symbols.map(s => (
                        <button
                            key={s}
                            disabled={isTransitioning}
                            onClick={() => switchSymbol(s)}
                            style={{
                                padding: '4px 10px',
                                borderRadius: '4px',
                                border: '1px solid #2a2e39',
                                backgroundColor: activeSymbol === s ? '#26a69a' : '#1e222d',
                                color: activeSymbol === s ? '#fff' : '#d1d4dc',
                                cursor: isTransitioning ? 'not-allowed' : 'pointer',
                                fontWeight: activeSymbol === s ? 'bold' : 'normal'
                            }}
                        >
                            {s}
                        </button>
                    ))}
                </div>
            </div>

            {/* Timeframe Selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ opacity: 0.6 }}>Timeframe:</span>
                <div style={{ display: 'flex', gap: '4px' }}>
                    {timeframes.map(tf => (
                        <button
                            key={tf}
                            disabled={isTransitioning}
                            onClick={() => switchTimeframe(tf)}
                            style={{
                                padding: '4px 10px',
                                borderRadius: '4px',
                                border: '1px solid #2a2e39',
                                backgroundColor: activeTimeframe === tf ? '#2962ff' : '#1e222d',
                                color: activeTimeframe === tf ? '#fff' : '#d1d4dc',
                                cursor: isTransitioning ? 'not-allowed' : 'pointer',
                                fontWeight: activeTimeframe === tf ? 'bold' : 'normal'
                            }}
                        >
                            {tf}
                        </button>
                    ))}
                </div>
            </div>

            {/* Status Indicator */}
            {isTransitioning && (
                <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px', color: '#2962ff' }}>
                    <div className="spinner-small" />
                    <span>Updating Market...</span>
                </div>
            )}
        </div>
    );
});

MarketToolbar.displayName = 'MarketToolbar';
export default MarketToolbar;
