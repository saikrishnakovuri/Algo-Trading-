import React, { memo } from 'react';
import { useMarketStore } from '../store/useMarketStore';
import { RefreshCw, WifiOff, AlertTriangle } from 'lucide-react';

/**
 * ReconnectOverlay
 * 
 * High-visibility overlay that appears over the terminal during connectivity loss.
 * Prevents interaction with stale data and provides clear recovery status.
 */
export const ReconnectOverlay = memo(() => {
    const status = useMarketStore(state => state.connectionStatus);
    const isOffline = useMarketStore(state => state.isBrowserOffline);
    const attempt = useMarketStore(state => state.reconnectAttempt);

    const showOverlay = status === 'RECONNECTING' || status === 'DISCONNECTED' || status === 'STALE' || isOffline;

    if (!showOverlay) return null;

    const getOverlayConfig = () => {
        if (isOffline) {
            return {
                icon: <WifiOff size={48} className="text-[#ef5350] mb-4" />,
                title: 'No Internet Connection',
                desc: 'Please check your network settings. Waiting for restoration...',
                color: '#ef5350'
            };
        }
        if (status === 'RECONNECTING') {
            return {
                icon: <RefreshCw size={48} className="text-[#2962ff] mb-4 animate-spin" />,
                title: 'Reconnecting to Market...',
                desc: `Attempting to restore live stream (Attempt #${attempt})...`,
                color: '#2962ff'
            };
        }
        if (status === 'STALE') {
            return {
                icon: <AlertTriangle size={48} className="text-[#f57c00] mb-4" />,
                title: 'Market Feed Stale',
                desc: 'We detected a freeze in the data stream. Triggering recovery...',
                color: '#f57c00'
            };
        }
        return {
            icon: <AlertTriangle size={48} className="text-[#787b86] mb-4" />,
            title: 'Disconnected',
            desc: 'The connection to the market gateway was lost.',
            color: '#787b86'
        };
    };

    const config = getOverlayConfig();

    return (
        <div className="absolute inset-0 z-[100] flex items-center justify-center bg-[#0a0e17]/80 backdrop-blur-sm transition-all duration-500">
            <div className="bg-[#131722] p-8 rounded-xl border border-[#2a2e39] shadow-2xl max-w-md w-full text-center">
                <div className="flex justify-center">{config.icon}</div>
                <h2 className="text-xl font-bold text-white mb-2 tracking-tight">{config.title}</h2>
                <p className="text-[#787b86] text-sm mb-6 leading-relaxed">
                    {config.desc}
                </p>
                <div className="flex items-center justify-center gap-2">
                    <div className="h-1.5 w-1.5 rounded-full animate-bounce bg-[#2962ff]" style={{ animationDelay: '0ms' }} />
                    <div className="h-1.5 w-1.5 rounded-full animate-bounce bg-[#2962ff]" style={{ animationDelay: '200ms' }} />
                    <div className="h-1.5 w-1.5 rounded-full animate-bounce bg-[#2962ff]" style={{ animationDelay: '400ms' }} />
                </div>
            </div>
        </div>
    );
});

ReconnectOverlay.displayName = 'ReconnectOverlay';
