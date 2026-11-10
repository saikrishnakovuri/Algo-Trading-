/**
 * JSDoc Type Definitions for Market State
 * @typedef {Object} Tick
 * @property {string} symbol
 * @property {number} price
 * @property {number} [volume]
 * @property {string} timestamp
 * 
 * @typedef {Object} Candle
 * @property {string} symbol
 * @property {string} timeframe
 * @property {number} open
 * @property {number} high
 * @property {number} low
 * @property {number} close
 * @property {number} volume
 * @property {string} timestamp
 * 
 * @typedef {Object} Signal
 * @property {'BUY'|'SELL'} signal
 * @property {string} symbol
 * @property {string} reason
 * @property {string} timestamp
 * 
 * @typedef {'CONNECTING'|'CONNECTED'|'DISCONNECTED'|'RECONNECTING'|'ERROR'} ConnectionState
 */

export {};
