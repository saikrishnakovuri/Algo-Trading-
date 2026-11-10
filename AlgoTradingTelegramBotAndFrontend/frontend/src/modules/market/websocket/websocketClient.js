/**
 * @file websocketClient.js
 * @description Core WebSocket client for the market stream.
 * DISPATCHES TO ZUSTAND STORE ONLY.
 */

import { useMarketStore } from '../store/useMarketStore';
import { STREAM_CONFIG } from './streamConfig';
import { normalizeEvent } from './websocketEvents';
import { reconnectEngine } from '../resilience/ReconnectEngine';

class MarketWebSocketClient {
    constructor() {
        this.socket = null;
        this.url = STREAM_CONFIG.WS_URL;
        this.activeSubscriptions = new Set();
        this._setupConnectivityListeners();
    }

    /**
     * Browser Offline/Online Detection
     */
    _setupConnectivityListeners() {
        window.addEventListener('online', () => {
            console.log('[Network] Browser ONLINE. Triggering recovery...');
            useMarketStore.getState().setBrowserOffline(false);
            reconnectEngine.handleDisconnect();
        });

        window.addEventListener('offline', () => {
            console.warn('[Network] Browser OFFLINE.');
            useMarketStore.getState().setBrowserOffline(true);
            useMarketStore.getState().setConnectionStatus('DISCONNECTED');
        });
    }

    /**
     * Connect to the FastAPI WebSocket Gateway
     */
    connect() {
        if (this.socket && this.socket.readyState <= 1) return;

        console.log(`[WS] Connecting to ${this.url}...`);
        this.socket = new WebSocket(this.url);

        this.socket.onopen = () => {
            console.log('[WS] Connected successfully');
            useMarketStore.getState().setConnectionStatus('CONNECTED');
            useMarketStore.getState().recordHeartbeat();
            
            // Re-subscribe to all active subscriptions on reconnect
            this.activeSubscriptions.forEach(sub => {
                this._send({ type: 'subscribe', ...JSON.parse(sub) });
            });
        };

        this.socket.onmessage = (event) => {
            try {
                const rawData = JSON.parse(event.data);
                
                // --- HEARTBEAT TRACKING ---
                useMarketStore.getState().recordHeartbeat();

                const normalized = normalizeEvent(rawData);
                if (!normalized) return;

                this.dispatchToStore(normalized);
            } catch (err) {
                console.error('[WS] Message parse error:', err);
            }
        };

        this.socket.onclose = () => {
            console.warn('[WS] Connection closed');
            useMarketStore.getState().setConnectionStatus('DISCONNECTED');
            
            // Hand off to ReconnectEngine for controlled recovery
            reconnectEngine.handleDisconnect();
        };

        this.socket.onerror = (error) => {
            console.error('[WS] Socket error:', error);
            useMarketStore.getState().setConnectionStatus('ERROR');
            useMarketStore.getState().setLastError('Socket failed');
            
            // Hand off to ReconnectEngine
            reconnectEngine.handleDisconnect();
        };
    }

    /**
     * Subscribe to a symbol/timeframe stream
     */
    subscribe(symbol, timeframe) {
        const sub = JSON.stringify({ symbol, timeframe });
        if (this.activeSubscriptions.has(sub)) return;

        console.log(`[WS] Subscribing to ${symbol} (${timeframe})`);
        this.activeSubscriptions.add(sub);
        this._send({ type: 'subscribe', symbol, timeframe });
    }

    /**
     * Unsubscribe from a symbol/timeframe stream
     */
    unsubscribe(symbol, timeframe) {
        const sub = JSON.stringify({ symbol, timeframe });
        if (!this.activeSubscriptions.has(sub)) return;

        console.log(`[WS] Unsubscribing from ${symbol} (${timeframe})`);
        this.activeSubscriptions.delete(sub);
        this._send({ type: 'unsubscribe', symbol, timeframe });
    }

    /**
     * Internal helper to send messages safely
     */
    _send(message) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(message));
        } else {
            console.warn('[WS] Socket not open. Message queued or lost:', message);
        }
    }

    /**
     * Dispatch normalized events to the Zustand store
     */
    dispatchToStore(event) {
        const store = useMarketStore.getState();

        switch (event.type) {
            case 'candle':
                store.updateCandle(event);
                break;
            case 'tick':
                store.addTick(event);
                break;
            case 'signal':
                store.addSignal(event);
                break;
            default:
                // System or unknown events
                break;
        }
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
    }
}

export const marketWS = new MarketWebSocketClient();
