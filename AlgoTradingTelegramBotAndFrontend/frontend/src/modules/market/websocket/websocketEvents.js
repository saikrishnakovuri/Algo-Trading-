/**
 * @file websocketEvents.js
 * @description Event parser and normalizer for incoming WebSocket messages.
 */

/**
 * Normalizes raw WebSocket data into structured events.
 * @param {Object} rawData 
 * @returns {Object|null} Normalized event or null if invalid.
 */
export function normalizeEvent(rawData) {
  if (!rawData || !rawData.type) {
    console.warn('[WS] Received malformed event:', rawData);
    return null;
  }

  // Basic validation and mapping
  switch (rawData.type) {
    case 'tick':
      return {
        type: 'tick',
        symbol: rawData.symbol,
        price: Number(rawData.price),
        timestamp: rawData.timestamp || new Date().toISOString(),
      };
    case 'candle':
      return {
        type: 'candle',
        symbol: rawData.symbol,
        timeframe: rawData.timeframe,
        time: rawData.time,
        open: Number(rawData.open),
        high: Number(rawData.high),
        low: Number(rawData.low),
        close: Number(rawData.close),
        volume: Number(rawData.volume),
        timestamp: rawData.timestamp,
      };
    case 'signal':
      return {
        type: 'signal',
        signal: rawData.signal,
        symbol: rawData.symbol,
        reason: rawData.reason,
        timestamp: rawData.timestamp || new Date().toISOString(),
      };
    default:
      // Return raw data if type is unrecognized but present
      return rawData;
  }
}
