import React, { memo } from 'react';
import { Target, Zap, ShieldAlert } from 'lucide-react';

export const SignalLogPanel = memo(() => {
    // Mock signal history for layout verification
    const signals = [
        { time: '10:15:00', type: 'BUY', reason: 'BOS + FVG Sweep', price: '22580', conf: '92%' },
        { time: '10:05:00', type: 'SELL', reason: 'Bearish CHOCH', price: '22610', conf: '85%' },
        { time: '09:45:00', type: 'BUY', reason: 'Liquidity Grab', price: '22550', conf: '78%' },
    ];

    return (
        <div className="flex flex-col h-1/3 min-h-[200px] border-b border-[#2a2e39]">
            <div className="px-3 py-2 text-xs font-semibold text-[#787b86] uppercase tracking-wider border-b border-[#2a2e39] flex justify-between items-center bg-[#0a0e17]">
                <span>Active Signals</span>
                <Zap size={14} className="text-[#26a69a]" />
            </div>
            <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-2">
                {signals.map((sig, idx) => (
                    <div key={idx} className="bg-[#1e222d] rounded border border-[#2a2e39] p-2 text-xs">
                        <div className="flex justify-between items-center mb-1">
                            <span className="text-[#787b86]">{sig.time}</span>
                            <span className={`font-bold px-1.5 py-0.5 rounded ${sig.type === 'BUY' ? 'bg-[#26a69a]/20 text-[#26a69a]' : 'bg-[#ef5350]/20 text-[#ef5350]'}`}>
                                {sig.type}
                            </span>
                        </div>
                        <div className="font-semibold text-[#d1d4dc] truncate">{sig.reason}</div>
                        <div className="flex justify-between items-center mt-1 text-[#787b86]">
                            <span>@ {sig.price}</span>
                            <span>Conf: <span className="text-white">{sig.conf}</span></span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
});

SignalLogPanel.displayName = 'SignalLogPanel';
