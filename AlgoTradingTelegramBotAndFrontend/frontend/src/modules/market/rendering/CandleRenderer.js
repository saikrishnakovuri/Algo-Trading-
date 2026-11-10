/**
 * CandleRenderer.js
 * 
 * Orchestrates the rendering of candles to the Lightweight Charts series.
 * 
 * Architectural Role:
 * - High-level coordinator for chart updates.
 * - Manages the interaction between the rendering engine and the series object.
 * - Ensures efficient use of series.update() vs series.setData().
 */

export class CandleRenderer {
  constructor(series) {
    this.series = series;
  }

  /**
   * Performs initial data load using setData().
   * Used for history load, symbol switches, or timeframe changes.
   */
  renderInitialHistory(candles) {
    // Implementation will use series.setData(candles)
    console.log('[CandleRenderer] Rendering initial history', candles.length);
  }

  /**
   * Performs incremental update using update().
   * Used for realtime streaming to avoid full chart redraws.
   */
  renderUpdate(candle) {
    // Implementation will use series.update(candle)
    // console.log('[CandleRenderer] Rendering candle update', candle.time);
  }

  /**
   * Resets the series state.
   */
  clear() {
    this.series.setData([]);
  }
}
