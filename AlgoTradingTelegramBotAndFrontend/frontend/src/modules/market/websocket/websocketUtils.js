/**
 * @file websocketUtils.js
 * @description Utility functions for WebSocket operations.
 */

/**
 * Validates if an object is a valid WebSocket event.
 * @param {any} event 
 * @returns {boolean}
 */
export function isValidEvent(event) {
  return event && typeof event === 'object' && 'type' in event;
}

/**
 * Helper to determine if an event is a market data event.
 * @param {string} type 
 * @returns {boolean}
 */
export function isMarketData(type) {
  return ['tick', 'candle', 'signal'].includes(type);
}
