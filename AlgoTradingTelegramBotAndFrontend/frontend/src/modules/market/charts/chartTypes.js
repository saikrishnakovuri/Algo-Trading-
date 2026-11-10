/**
 * @typedef {Object} CandleData
 * @property {number} time - Unix timestamp in seconds
 * @property {number} open - Opening price
 * @property {number} high - Highest price
 * @property {number} low - Lowest price
 * @property {number} close - Closing price
 */

/**
 * @typedef {Object} TickData
 * @property {number} time - Unix timestamp in seconds
 * @property {number} price - Current price
 */

/**
 * @typedef {Object} ChartState
 * @property {string} symbol - Trading symbol
 * @property {string} timeframe - Chart timeframe (e.g., '1m', '5m', '1h')
 * @property {boolean} isLoading - Loading state
 */

// Export an empty object to satisfy module requirements if needed
export default {};
