import React, { memo } from 'react';
import { Briefcase } from 'lucide-react';

export const PositionPanel = memo(() => {
    return (
        <div className="flex flex-col flex-1 min-h-[200px]">
            <div className="px-3 py-2 text-xs font-semibold text-[#787b86] uppercase tracking-wider border-b border-[#2a2e39] flex justify-between items-center bg-[#0a0e17]">
                <span>Open Positions</span>
                <Briefcase size={14} />
            </div>
            <div className="flex-1 flex flex-col items-center justify-center text-[#787b86] p-4 text-center">
                <Briefcase size={32} className="mb-2 opacity-50" />
                <p className="text-sm">No active positions</p>
                <p className="text-xs opacity-70 mt-1">Waiting for strategy execution...</p>
            </div>
        </div>
    );
});

PositionPanel.displayName = 'PositionPanel';
