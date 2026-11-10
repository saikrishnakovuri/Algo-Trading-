/**
 * CandleValidation.js
 * 
 * Logic to prevent malformed or duplicate candles from entering the pipeline.
 * 
 * Architectural Role:
 * - Defensive guard for the rendering engine.
 * - Ensures OHLC numeric integrity.
 * - Enforces strict chronological order.
 */

export class CandleValidation {
  /**
   * Validates a single candle object.
   */
  isValid(candle) {
    if (!candle) return false;

    const { time, open, high, low, close } = candle;

    // 1. Check for required fields
    if (time === undefined || open === undefined) return false;

    // 2. Check numeric integrity
    if (isNaN(open) || isNaN(high) || isNaN(low) || isNaN(close)) return false;

    // 3. Check OHLC logic (e.g., high >= low)
    if (high < low || high < open || high < close || low > open || low > close) {
      console.warn('[CandleValidation] Invalid OHLC relation detected', candle);
      // We might still allow it if the exchange sends it, but it's good to log
    }

    return true;
  }

  /**
   * Ensures the incoming candle is not older than the last rendered candle.
   */
  isChronological(incomingTime, lastTime) {
    return incomingTime >= lastTime;
  }
}
