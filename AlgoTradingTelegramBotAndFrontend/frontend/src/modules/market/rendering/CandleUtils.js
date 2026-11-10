/**
 * CandleUtils.js
 * 
 * Normalization and timestamp utilities.
 * 
 * Architectural Role:
 * - Pure functions for data transformation.
 * - Timeframe duration calculations.
 * - Timestamp conversions (MS to S, ISO to Unix).
 */

export const CandleUtils = {
  /**
   * Normalizes raw backend data to TradingView format.
   */
  normalize(raw) {
    return {
      time: typeof raw.t === 'string' ? Math.floor(new Date(raw.t).getTime() / 1000) : Math.floor(raw.t / 1000),
      open: parseFloat(raw.o),
      high: parseFloat(raw.h),
      low: parseFloat(raw.l),
      close: parseFloat(raw.c)
    };
  },

  /**
   * Returns timeframe duration in seconds.
   */
  getTimeframeSeconds(timeframe) {
    const unit = timeframe.slice(-1);
    const value = parseInt(timeframe.slice(0, -1));

    switch (unit) {
      case 'm': return value * 60;
      case 'h': return value * 3600;
      case 'd': return value * 86400;
      default: return 60;
    }
  },

  /**
   * Formats a timestamp for display or internal keys.
   */
  formatTimestamp(ts) {
    return new Date(ts * 1000).toISOString();
  }
};
