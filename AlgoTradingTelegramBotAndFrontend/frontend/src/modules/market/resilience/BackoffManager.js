/**
 * @file BackoffManager.js
 * @description Manages exponential backoff logic for websocket reconnections.
 */

import { STREAM_CONFIG } from '../websocket/streamConfig';

export const BackoffManager = {
    /**
     * Calculates the delay for the next reconnect attempt.
     * @param {number} attempt - The current attempt count (0-indexed).
     * @returns {number} Delay in milliseconds.
     */
    getDelay: (attempt) => {
        const baseDelay = STREAM_CONFIG.INITIAL_RECONNECT_DELAY || 1000;
        const maxDelay = STREAM_CONFIG.MAX_RECONNECT_DELAY || 30000;
        
        // Exponential backoff: base * 2^attempt
        const delay = Math.min(baseDelay * Math.pow(2, attempt), maxDelay);
        
        // Add 10% jitter to prevent reconnect storms
        const jitter = delay * 0.1 * Math.random();
        
        return delay + jitter;
    }
};
