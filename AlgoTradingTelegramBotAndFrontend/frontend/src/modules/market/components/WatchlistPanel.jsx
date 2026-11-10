import React, { memo } from 'react';
import { useMarketStore } from '../store/useMarketStore';

export const WatchlistPanel = memo(() => {
    // In a real app, this would fetch from a watchlist store.
    // We use mock data for the layout structure.
    const watchlist = [
        { symbol: 'NIFTY', price: '22605.50', change: '+0.45%', up: true },
        { symbol: 'BANKNIFTY', price: '48200.15', change: '-0.12%', up: false },
        { symbol: 'FINNIFTY', price: '21450.00', change: '+0.20%', up: true },
        { symbol: 'RELIANCE', price: '2950.25', change: '+1.15%', up: true },
        { symbol: 'HDFCBANK', price: '1520.40', change: '-0.50%', up: false },
    ];

    return (
        <div className="flex flex-col h-1/3 min-h-[200px] border-b border-[#2a2e39]">
            <div className="px-3 py-2 text-xs font-semibold text-[#787b86] uppercase tracking-wider border-b border-[#2a2e39] bg-[#0a0e17]">
                Watchlist
            </div>
            <div className="flex-1 overflow-y-auto custom-scrollbar">
                {watchlist.map((item, idx) => (
                    <div 
                        key={idx} 
                        className="flex justify-between items-center px-3 py-2 border-b border-[#2a2e39] hover:bg-[#1e222d] cursor-pointer transition-colors"
                    >
                        <span className="font-semibold text-sm text-[#d1d4dc]">{item.symbol}</span>
                        <div className="text-right">
                            <div className={`text-sm font-bold ${item.up ? 'text-[#26a69a]' : 'text-[#ef5350]'}`}>
                                {item.price}
                            </div>
                            <div className={`text-xs ${item.up ? 'text-[#26a69a]' : 'text-[#ef5350]'} opacity-80`}>
                                {item.change}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
});

WatchlistPanel.displayName = 'WatchlistPanel';
