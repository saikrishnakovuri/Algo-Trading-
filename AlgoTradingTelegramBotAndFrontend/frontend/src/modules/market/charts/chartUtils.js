/**
 * Utility functions for Chart Data Management
 */

/**
 * Normalizes candle data from backend to TradingView format
 * @param {Object} rawCandle - Candle data from WebSocket or API
 * @returns {Object} Normalized candle
 */
export const normalizeCandle = (rawCandle) => {
    return {
        time: ensureUnixTimestamp(rawCandle.time || rawCandle.timestamp),
        open: parseFloat(rawCandle.open),
        high: parseFloat(rawCandle.high),
        low: parseFloat(rawCandle.low),
        close: parseFloat(rawCandle.close),
    };
};

/**
 * Ensures timestamp is in Unix seconds format (TradingView requirement)
 * @param {number|string} timestamp - Raw timestamp
 * @returns {number} Unix timestamp in seconds
 */
export const ensureUnixTimestamp = (timestamp) => {
    if (!timestamp) return Math.floor(Date.now() / 1000);
    
    // If it's already in seconds (typical for many crypto/trading APIs)
    if (timestamp.toString().length <= 10) {
        return parseInt(timestamp);
    }
    
    // If it's in milliseconds
    return Math.floor(parseInt(timestamp) / 1000);
};

/**
 * Validates if a candle has all required fields
 * @param {Object} candle 
 * @returns {boolean}
 */
export const isValidCandle = (candle) => {
    return (
        candle &&
        typeof candle.time === 'number' &&
        !isNaN(candle.open) &&
        !isNaN(candle.high) &&
        !isNaN(candle.low) &&
        !isNaN(candle.close)
    );
};
