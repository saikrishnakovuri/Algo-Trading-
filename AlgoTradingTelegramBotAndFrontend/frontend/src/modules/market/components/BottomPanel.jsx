import React, { useState, memo } from 'react';
import { Terminal, BookOpen, AlertTriangle } from 'lucide-react';

export const BottomPanel = memo(() => {
    const [activeTab, setActiveTab] = useState('logs');
    const [isCollapsed, setIsCollapsed] = useState(false);

    if (isCollapsed) {
        return (
            <div 
                className="h-8 border-t border-[#2a2e39] bg-[#131722] flex items-center px-4 cursor-pointer hover:bg-[#1e222d] text-xs text-[#787b86]"
                onClick={() => setIsCollapsed(false)}
            >
                ▲ Click to expand terminal bottom panel
            </div>
        );
    }

    return (
        <div className="h-48 flex-shrink-0 border-t border-[#2a2e39] bg-[#131722] flex flex-col">
            {/* Tabs */}
            <div className="flex items-center border-b border-[#2a2e39] bg-[#0a0e17] px-2 h-8">
                <button 
                    onClick={() => setActiveTab('logs')}
                    className={`px-4 h-full text-xs font-semibold flex items-center gap-2 border-b-2 ${activeTab === 'logs' ? 'border-[#2962ff] text-white' : 'border-transparent text-[#787b86] hover:text-[#d1d4dc]'}`}
                >
                    <Terminal size={14} /> System Logs
                </button>
                <button 
                    onClick={() => setActiveTab('orders')}
                    className={`px-4 h-full text-xs font-semibold flex items-center gap-2 border-b-2 ${activeTab === 'orders' ? 'border-[#2962ff] text-white' : 'border-transparent text-[#787b86] hover:text-[#d1d4dc]'}`}
                >
                    <BookOpen size={14} /> Order History
                </button>
                <button 
                    onClick={() => setActiveTab('errors')}
                    className={`px-4 h-full text-xs font-semibold flex items-center gap-2 border-b-2 ${activeTab === 'errors' ? 'border-[#ef5350] text-white' : 'border-transparent text-[#787b86] hover:text-[#d1d4dc]'}`}
                >
                    <AlertTriangle size={14} /> Errors
                </button>
                
                <div className="ml-auto">
                    <button 
                        onClick={() => setIsCollapsed(true)}
                        className="p-1 hover:bg-[#1e222d] rounded text-[#787b86] hover:text-white"
                    >
                        ▼
                    </button>
                </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto p-2 font-mono text-[11px] text-[#a9adc1] bg-[#0a0e17]">
                {activeTab === 'logs' && (
                    <div className="space-y-1">
                        <div><span className="text-[#787b86]">10:15:02</span> [Engine] Volatility contraction detected.</div>
                        <div><span className="text-[#787b86]">10:15:05</span> <span className="text-[#26a69a]">[Websocket]</span> Heartbeat OK.</div>
                        <div><span className="text-[#787b86]">10:16:00</span> [Store] Trailing update applied seamlessly.</div>
                        <div><span className="text-[#787b86]">10:16:01</span> [TradingChart] Render 60fps stable.</div>
                    </div>
                )}
                {activeTab === 'orders' && (
                    <div className="text-[#787b86] italic p-2">No orders submitted this session.</div>
                )}
                {activeTab === 'errors' && (
                    <div className="text-[#787b86] italic p-2">No system errors detected.</div>
                )}
            </div>
        </div>
    );
});

BottomPanel.displayName = 'BottomPanel';
