/**
 * @file marketSelectors.js
 * @description Optimized selectors for the market store to prevent unnecessary rerenders.
 */

const EMPTY_ARRAY = [];

/**
 * Selector for latest candle of a symbol and timeframe.
 */
export const selectLatestCandle = (symbol, timeframe) => (state) => {
  const timeframeData = state.candles[symbol]?.[timeframe];
  if (!timeframeData || timeframeData.length === 0) return null;
  return timeframeData[timeframeData.length - 1];
};

/**
 * Selector for the full candle array.
 */
export const selectCandles = (symbol, timeframe) => (state) => {
  return state.candles[symbol]?.[timeframe] || EMPTY_ARRAY;
};

/**
 * Selector for the latest price of a symbol.
 */
export const selectLatestPrice = (symbol) => (state) => {
  const symbolTicks = state.ticks[symbol];
  if (!symbolTicks || symbolTicks.length === 0) return null;
  return symbolTicks[symbolTicks.length - 1].price;
};

/**
 * Selector for connection status.
 */
export const selectConnectionStatus = (state) => state.connectionStatus;

/**
 * Selector for latest signals.
 */
export const selectSignals = (state) => state.signals || EMPTY_ARRAY;
