/**
 * CandleLifecycle.js
 * 
 * Manages partial vs finalized candle transitions.
 * 
 * Architectural Role:
 * - Tracks the state of the "current" candle.
 * - Determines if an incoming tick/update belongs to the current candle or starts a new one.
 * - Handles timeframe-aware boundary logic.
 */

export class CandleLifecycle {
  constructor(timeframe) {
    this.timeframe = timeframe;
    this.lastFinalizedTimestamp = null;
  }

  /**
   * Determines the type of update required based on the incoming candle timestamp.
   * Returns 'UPDATE' (same candle) or 'APPEND' (new candle).
   */
  determineUpdateType(incomingCandle, lastKnownCandle) {
    if (!lastKnownCandle) return 'APPEND';
    
    // Logic to compare timestamps based on timeframe
    if (incomingCandle.time === lastKnownCandle.time) {
      return 'UPDATE';
    } else if (incomingCandle.time > lastKnownCandle.time) {
      return 'APPEND';
    }
    
    return 'IGNORE'; // Stale data
  }

  /**
   * Transition timeframe if user switches view.
   */
  setTimeframe(newTimeframe) {
    this.timeframe = newTimeframe;
    this.lastFinalizedTimestamp = null;
  }
}
