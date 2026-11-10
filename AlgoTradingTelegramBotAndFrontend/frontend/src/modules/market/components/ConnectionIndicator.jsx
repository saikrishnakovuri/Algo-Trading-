import React from 'react';
import { useMarketStore } from '../store/useMarketStore';

export const ConnectionIndicator = () => {
    const status = useMarketStore(state => state.connectionStatus);

    const getStatusConfig = () => {
        switch (status) {
            case 'CONNECTED':
                return { color: '#26a69a', text: 'Live', pulse: true };
            case 'CONNECTING':
            case 'RECONNECTING':
                return { color: '#f57c00', text: 'Connecting...', pulse: true };
            case 'ERROR':
            case 'DISCONNECTED':
                return { color: '#ef5350', text: 'Disconnected', pulse: false };
            default:
                return { color: '#787b86', text: 'Unknown', pulse: false };
        }
    };

    const config = getStatusConfig();

    return (
        <div className="flex items-center gap-2 text-xs font-semibold">
            <div className="relative flex items-center justify-center h-3 w-3">
                {config.pulse && (
                    <span 
                        className="absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping"
                        style={{ backgroundColor: config.color }}
                    />
                )}
                <span 
                    className="relative inline-flex rounded-full h-2 w-2"
                    style={{ backgroundColor: config.color }}
                />
            </div>
            <span style={{ color: config.color }}>{config.text}</span>
        </div>
    );
};
