/**
 * @file ReconnectEngine.js
 * @description Centralized orchestrator for the WebSocket recovery lifecycle.
 */

import { useMarketStore } from '../store/useMarketStore';
import { BackoffManager } from './BackoffManager';
import { StreamRecoveryManager } from './StreamRecoveryManager';
import { marketWS } from '../websocket/websocketClient';

class ReconnectEngine {
    constructor() {
        this.timerId = null;
        this.isRecovering = false;
    }

    /**
     * Entry point for connection failure.
     */
    handleDisconnect() {
        const store = useMarketStore.getState();
        
        // If we are already connected or currently trying to reconnect, ignore.
        if (store.connectionStatus === 'CONNECTED' || store.connectionStatus === 'RECONNECTING') return;
        
        // If browser is offline, we don't start the timer yet. 
        // Window 'online' event will trigger it later.
        if (store.isBrowserOffline) {
            console.log('[Reconnect] Browser offline. Waiting for network...');
            return;
        }

        this.scheduleNextAttempt();
    }

    /**
     * Schedules the next reconnect attempt using exponential backoff.
     */
    scheduleNextAttempt() {
        if (this.timerId) return;

        const store = useMarketStore.getState();
        const attempt = store.reconnectAttempt;
        const delay = BackoffManager.getDelay(attempt);

        console.log(`[Reconnect] Scheduling attempt #${attempt + 1} in ${Math.round(delay)}ms`);
        store.setConnectionStatus('RECONNECTING');

        this.timerId = setTimeout(() => {
            this.timerId = null;
            this.executeAttempt();
        }, delay);
    }

    /**
     * Executes a single reconnect attempt.
     */
    async executeAttempt() {
        const store = useMarketStore.getState();
        
        try {
            // 1. Increment attempt count
            store.setReconnectAttempt(store.reconnectAttempt + 1);

            // 2. Trigger WS Connect
            // Note: marketWS.connect() will update store to CONNECTED on success
            await marketWS.connect();
            
            // 3. Monitor for success (handled via store subscription in a real app, 
            // but here we wait a bit and check)
            setTimeout(() => {
                if (useMarketStore.getState().connectionStatus === 'CONNECTED') {
                    this.handleSuccess();
                } else {
                    this.handleDisconnect(); // Retry
                }
            }, 2000);

        } catch (err) {
            console.error('[Reconnect] Attempt failed:', err);
            this.handleDisconnect(); // Retry
        }
    }

    /**
     * Finalizes recovery after connection is restored.
     */
    async handleSuccess() {
        console.log('[Reconnect] Connection restored. Starting state recovery...');
        const store = useMarketStore.getState();
        store.setReconnectAttempt(0);
        
        // Start high-integrity stream recovery
        await StreamRecoveryManager.recover();
    }

    /**
     * Forced reset (e.g., on manual disconnect or logout).
     */
    reset() {
        if (this.timerId) {
            clearTimeout(this.timerId);
            this.timerId = null;
        }
        useMarketStore.getState().setReconnectAttempt(0);
    }
}

export const reconnectEngine = new ReconnectEngine();
