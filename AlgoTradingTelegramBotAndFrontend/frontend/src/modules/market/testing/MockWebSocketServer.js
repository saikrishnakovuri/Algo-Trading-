/**
 * @file MockWebSocketServer.js
 * @description In-browser Mock WebSocket Server for controlled chaos engineering.
 * 
 * Simulates real market behavior:
 * - High-frequency ticks
 * - Candle formation
 * - Disconnects / Malformed packets
 * - Reconnect cycles
 */

import { useMarketStore } from '../store/useMarketStore';

class MockWebSocketServer {
    constructor() {
        this.isRunning = false;
        this.tickInterval = null;
        this.config = {
            symbol: 'NIFTY',
            timeframe: '5m',
            basePrice: 22000,
            volatility: 5,
            tickSpeedMs: 100, // Normal: 10hz, Stress: 1ms
            isBursting: false
        };
        this.msgCount = 0;
    }

    /**
     * Start the simulation
     */
    start(config = {}) {
        this.config = { ...this.config, ...config };
        if (this.isRunning) return;
        
        console.log(`[MockServer] Starting simulation for ${this.config.symbol}...`);
        this.isRunning = true;
        this._scheduleTick();
    }

    /**
     * Stop the simulation
     */
    stop() {
        this.isRunning = false;
        if (this.tickInterval) clearTimeout(this.tickInterval);
        console.log(`[MockServer] Simulation stopped. Total messages: ${this.msgCount}`);
    }

    /**
     * Simulate a WebSocket Disconnect
     */
    simulateDisconnect() {
        console.warn("[MockServer] FORCING DISCONNECT SCENARIO...");
        // We trigger the frontend's handler directly to simulate physical loss
        const { connectionStatus } = useMarketStore.getState();
        if (connectionStatus === 'CONNECTED') {
            useMarketStore.getState().setConnectionStatus('DISCONNECTED');
        }
    }

    /**
     * Internal Tick Engine
     */
    _scheduleTick() {
        if (!this.isRunning) return;

        const delay = this.config.tickSpeedMs;
        
        this.tickInterval = setTimeout(() => {
            this._generateEvent();
            this._scheduleTick();
        }, delay);
    }

    _generateEvent() {
        const now = Math.floor(Date.now() / 1000);
        const candleTime = now - (now % 300); // 5m snap
        
        // Random walk
        const change = (Math.random() - 0.5) * this.config.volatility;
        this.config.basePrice += change;

        const event = {
            type: 'candle',
            symbol: this.config.symbol,
            timeframe: this.config.timeframe,
            time: candleTime,
            open: 22000,
            high: this.config.basePrice + 20,
            low: this.config.basePrice - 20,
            close: this.config.basePrice,
            volume: Math.floor(Math.random() * 1000),
            timestamp: new Date().toISOString()
        };

        // Dispatch directly to store as if it came from marketWS
        useMarketStore.getState().updateCandle(event);
        useMarketStore.getState().recordHeartbeat();
        this.msgCount++;
    }
}

export const mockServer = new MockWebSocketServer();
