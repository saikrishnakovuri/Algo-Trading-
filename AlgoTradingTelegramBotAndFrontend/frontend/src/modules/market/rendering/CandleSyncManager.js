/**
 * CandleSyncManager.js
 * 
 * Synchronizes Zustand store state with Chart series.
 * 
 * Architectural Role:
 * - Ensures consistency between the "source of truth" (Store) and the "view" (Chart).
 * - Handles reconciliation after network reconnections or browser tab refocus.
 * - Prevents "ghost candles" or gaps in the UI.
 */

export class CandleSyncManager {
  constructor(store, renderer) {
    this.store = store;
    this.renderer = renderer;
  }

  /**
   * Full reconciliation of chart data from store.
   * Useful after reconnection or major state resets.
   */
  syncFull() {
    const candles = this.store.getCandles();
    this.renderer.renderInitialHistory(candles);
  }

  /**
   * Verifies if the last N candles in store match what's expected.
   */
  verifySync() {
    // Logic to detect gaps or mismatches
    // If mismatch found, trigger a resync or history reload
  }
}
