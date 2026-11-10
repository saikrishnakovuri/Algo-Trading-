/**
 * @file StaleDataDetector.js
 * @description Monitors for frozen market feeds and triggers recovery if data becomes stale.
 */

import { useMarketStore } from '../store/useMarketStore';
import { reconnectEngine } from './ReconnectEngine';

class StaleDataDetector {
    constructor() {
        this.timerId = null;
        this.STALE_THRESHOLD_MS = 15000; // 15 seconds without data
    }

    /**
     * Starts monitoring the feed health.
     */
    start() {
        if (this.timerId) return;

        this.timerId = setInterval(() => {
            this.checkHealth();
        }, 5000);
    }

    /**
     * Checks if the current market feed is stale.
     */
    checkHealth() {
        const store = useMarketStore.getState();
        
        // Only check if we ARE supposed to be connected
        if (store.connectionStatus !== 'CONNECTED') return;

        const lastHeartbeat = store.lastHeartbeatTs;
        const now = Date.now();

        if (lastHeartbeat > 0 && (now - lastHeartbeat > this.STALE_THRESHOLD_MS)) {
            console.warn(`[StaleDetector] Market feed is STALE. Last update: ${new Date(lastHeartbeat).toLocaleTimeString()}`);
            
            // Mark state and trigger recovery
            store.setConnectionStatus('STALE');
            reconnectEngine.handleDisconnect();
        }
    }

    /**
     * Stops the monitor.
     */
    stop() {
        if (this.timerId) {
            clearInterval(this.timerId);
            this.timerId = null;
        }
    }
}

export const staleDataDetector = new StaleDataDetector();
