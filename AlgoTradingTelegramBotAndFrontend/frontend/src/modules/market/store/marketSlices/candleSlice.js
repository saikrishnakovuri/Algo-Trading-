/**
 * @file candleSlice.js
 * @description State slice for managing candle data with high-frequency "Trailing Update" protection.
 */

import { STORE_CONFIG } from '../storeConfig';

export const createCandleSlice = (set, get) => ({
  candles: {}, // symbol -> timeframe -> candle array
  _lastUpdateTs: 0,
  _pendingUpdates: {}, // symbol -> timeframe -> timeoutId
  _lastSkippedData: {}, // symbol -> timeframe -> latest candle data

  /**
   * updateCandle
   * High-integrity throttled update.
   */
  updateCandle: (candle, force = false) => {
    const { symbol, timeframe, time, timestamp } = candle;
    const candleTime = time || timestamp;
    const now = Date.now();
    const throttleMs = STORE_CONFIG.UPDATE_THROTTLE_MS || 0;

    const key = `${symbol}-${timeframe}`;

    // 1. Check if we should throttle
    if (!force && throttleMs > 0 && (now - get()._lastUpdateTs < throttleMs)) {
        get()._lastSkippedData[key] = candle;

        if (!get()._pendingUpdates[key]) {
            const timeoutId = setTimeout(() => {
                const latestData = get()._lastSkippedData[key];
                
                // --- STALE UPDATE PROTECTION ---
                // Before applying, verify if a newer candle has already been rolled over
                const currentStore = get();
                const symbolData = currentStore.candles[symbol] || {};
                const timeframeData = symbolData[timeframe] || [];
                const lastCandle = timeframeData[timeframeData.length - 1];
                const lastCandleTime = lastCandle ? (lastCandle.time || lastCandle.timestamp) : 0;

                if (latestData && (latestData.time || latestData.timestamp) >= lastCandleTime) {
                    // console.log(`[Store] Applying Trailing Update for ${key}`);
                    get().updateCandle(latestData, true); // Force apply
                } else {
                    console.warn(`[Store] REJECTED stale trailing update for ${key}. Newer candle rollover detected.`);
                }
                
                // Cleanup
                const pending = { ...get()._pendingUpdates };
                delete pending[key];
                set({ _pendingUpdates: pending });
            }, throttleMs);

            set((state) => ({
                _pendingUpdates: { ...state._pendingUpdates, [key]: timeoutId }
            }));
        }
        return;
    }

    // 2. Perform the actual State Update
    set((state) => {
      const symbolData = state.candles[symbol] || {};
      const timeframeData = symbolData[timeframe] || [];
      const lastCandle = timeframeData[timeframeData.length - 1];
      const lastCandleTime = lastCandle ? (lastCandle.time || lastCandle.timestamp) : null;

      let updatedTimeframeData;

      if (lastCandleTime === candleTime) {
        // Update current forming candle (SNAPSHOT update)
        updatedTimeframeData = [...timeframeData.slice(0, -1), candle];
      } else if (!lastCandleTime || candleTime > lastCandleTime) {
        // Append new candle
        updatedTimeframeData = [...timeframeData, candle].slice(-STORE_CONFIG.RETENTION.CANDLES);
      } else {
        // --- STALE SNAPSHOT REJECTION ---
        // This handles cases where an out-of-order message arrives directly
        console.warn(`[Store] REJECTED out-of-order snapshot for ${key}: ${candleTime} < ${lastCandleTime}`);
        return state;
      }

      // Cleanup skipped data as it's now applied
      const lastSkipped = { ...state._lastSkippedData };
      delete lastSkipped[key];

      return {
        _lastUpdateTs: now,
        _lastSkippedData: lastSkipped,
        candles: {
          ...state.candles,
          [symbol]: {
            ...symbolData,
            [timeframe]: updatedTimeframeData,
          },
        },
      };
    });
  },

  /**
   * clearPendingUpdates
   * Safely clears all scheduled trailing update timers.
   * MUST be called during symbol/timeframe switches and unmounts.
   */
  clearPendingUpdates: (symbol, timeframe) => {
    const pending = get()._pendingUpdates;
    const skipped = get()._lastSkippedData;
    
    if (symbol && timeframe) {
        const key = `${symbol}-${timeframe}`;
        if (pending[key]) {
            clearTimeout(pending[key]);
            const newPending = { ...pending };
            delete newPending[key];
            const newSkipped = { ...skipped };
            delete newSkipped[key];
            set({ _pendingUpdates: newPending, _lastSkippedData: newSkipped });
            console.log(`[Store] Cleared pending updates for ${key}`);
        }
    } else {
        // Clear EVERYTHING
        Object.values(pending).forEach(id => clearTimeout(id));
        set({ _pendingUpdates: {}, _lastSkippedData: {} });
        console.log(`[Store] Cleared ALL pending updates`);
    }
  },

  /**
   * clearCandles
   * Resets the candle history for a specific symbol/timeframe.
   */
  clearCandles: (symbol, timeframe) => {
    set((state) => ({
      candles: {
        ...state.candles,
        [symbol]: {
          ...(state.candles[symbol] || {}),
          [timeframe]: [],
        },
      },
    }));
  },

  setCandles: (symbol, timeframe, candleArray) => {
    // Clear any pending timers for this symbol/timeframe before setting bulk data
    get().clearPendingUpdates(symbol, timeframe);
    
    set((state) => ({
      candles: {
        ...state.candles,
        [symbol]: {
          ...(state.candles[symbol] || {}),
          [timeframe]: candleArray.slice(-STORE_CONFIG.RETENTION.CANDLES),
        },
      },
    }));
  },
});
