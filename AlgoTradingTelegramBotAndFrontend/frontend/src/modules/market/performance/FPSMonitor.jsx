import React, { useState, useEffect, memo } from 'react';
import { Activity } from 'lucide-react';

/**
 * FPSMonitor
 * 
 * Tracks actual browser render frame rate to ensure the trading terminal
 * remains responsive under heavy websocket load.
 */
export const FPSMonitor = memo(() => {
    const [fps, setFps] = useState(60);
    const [statusColor, setStatusColor] = useState('#26a69a'); // default green

    useEffect(() => {
        let frameCount = 0;
        let lastTime = performance.now();
        let animationFrameId;

        const measureFPS = () => {
            const now = performance.now();
            frameCount++;

            if (now >= lastTime + 1000) {
                // Calculate frames per second
                const currentFps = Math.round((frameCount * 1000) / (now - lastTime));
                setFps(currentFps);
                
                if (currentFps >= 55) setStatusColor('#26a69a'); // Green (Good)
                else if (currentFps >= 30) setStatusColor('#f57c00'); // Orange (Warning)
                else setStatusColor('#ef5350'); // Red (Critical)

                frameCount = 0;
                lastTime = now;
            }

            animationFrameId = requestAnimationFrame(measureFPS);
        };

        animationFrameId = requestAnimationFrame(measureFPS);

        return () => {
            cancelAnimationFrame(animationFrameId);
        };
    }, []);

    return (
        <div className="flex items-center gap-2 px-2 py-1 bg-[#1e222d] rounded border border-[#2a2e39]" title="Frames Per Second">
            <Activity size={14} style={{ color: statusColor }} />
            <span style={{ color: statusColor, fontSize: '12px', fontWeight: 'bold', minWidth: '40px', textAlign: 'right' }}>
                {fps} FPS
            </span>
        </div>
    );
});

FPSMonitor.displayName = 'FPSMonitor';
