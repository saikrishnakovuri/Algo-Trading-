import React, { memo } from 'react';
import { WatchlistPanel } from './WatchlistPanel';
import { SignalLogPanel } from './SignalLogPanel';
import { PositionPanel } from './PositionPanel';

export const Sidebar = memo(() => {
    return (
        <div className="w-72 flex-shrink-0 border-r border-[#2a2e39] bg-[#131722] flex flex-col h-full">
            <WatchlistPanel />
            <SignalLogPanel />
            <PositionPanel />
        </div>
    );
});

Sidebar.displayName = 'Sidebar';
