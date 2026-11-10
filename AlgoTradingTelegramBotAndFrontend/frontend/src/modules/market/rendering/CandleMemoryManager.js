/**
 * CandleMemoryManager.js
 * 
 * Pruning logic for old candle data.
 * 
 * Architectural Role:
 * - Prevents OOM (Out of Memory) in the browser during long-running sessions.
 * - Maintains a "rolling window" of candles in the Zustand store.
 * - Configurable limits per timeframe.
 */

export class CandleMemoryManager {
  constructor(maxCandles = 2000) {
    this.maxCandles = maxCandles;
  }

  /**
   * Checks if pruning is required and returns the pruned array.
   */
  prune(candles) {
    if (candles.length <= this.maxCandles) {
      return candles;
    }

    const excess = candles.length - this.maxCandles;
    console.log(`[CandleMemoryManager] Pruning ${excess} candles`);
    
    // Keep the most recent candles
    return candles.slice(excess);
  }

  setMaxCandles(limit) {
    this.maxCandles = limit;
  }
}
