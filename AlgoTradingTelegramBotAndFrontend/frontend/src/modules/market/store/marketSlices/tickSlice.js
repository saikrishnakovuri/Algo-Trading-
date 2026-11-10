/**
 * @file tickSlice.js
 * @description State slice for managing realtime tick data.
 */

import { STORE_CONFIG } from '../storeConfig';

export const createTickSlice = (set, get) => ({
  ticks: {}, // symbol -> tick array

  /**
   * addTick
   * Appends a new tick to the symbol's history.
   */
  addTick: (tick) => {
    set((state) => {
      const symbol = tick.symbol;
      const currentTicks = state.ticks[symbol] || [];
      
      // Limit memory growth by slicing to retention limit
      const updatedTicks = [...currentTicks, tick].slice(-STORE_CONFIG.RETENTION.TICKS);
      
      return {
        ticks: {
          ...state.ticks,
          [symbol]: updatedTicks,
        },
      };
    });
  },

  /**
   * clearTicks
   * Resets tick history.
   */
  clearTicks: (symbol) => {
    set((state) => {
      if (!symbol) return { ticks: {} };
      
      const newTicks = { ...state.ticks };
      delete newTicks[symbol];
      return { ticks: newTicks };
    });
  },
});
