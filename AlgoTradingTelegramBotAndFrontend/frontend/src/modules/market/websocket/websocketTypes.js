/**
 * @file websocketTypes.js
 * @description JSDoc types for WebSocket events and connection states.
 */

/**
 * @typedef {Object} TickEvent
 * @property {'tick'} type
 * @property {string} symbol
 * @property {number} price
 * @property {string} timestamp
 */

/**
 * @typedef {Object} CandleEvent
 * @property {'candle'} type
 * @property {string} symbol
 * @property {string} timeframe
 * @property {number} open
 * @property {number} high
 * @property {number} low
 * @property {number} close
 * @property {number} volume
 * @property {string} timestamp
 */

/**
 * @typedef {Object} SignalEvent
 * @property {'signal'} type
 * @property {'BUY' | 'SELL'} signal
 * @property {string} symbol
 * @property {string} reason
 * @property {string} timestamp
 */

/**
 * @typedef {Object} SystemEvent
 * @property {'system'} type
 * @property {string} message
 * @property {string} level - 'info' | 'warning' | 'error'
 */

/**
 * @typedef {'CONNECTING' | 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING' | 'ERROR'} ConnectionState
 */

export {};
