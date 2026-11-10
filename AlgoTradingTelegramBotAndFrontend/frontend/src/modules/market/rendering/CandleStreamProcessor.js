/**
 * CandleStreamProcessor.js
 * 
 * Processes incoming websocket candle events.
 * 
 * Architectural Role:
 * - High-speed ingestion point for realtime data.
 * - Validates, normalizes, and routes candle events.
 * - Orchestrates the update flow: Validate -> Lifecycle -> Store -> Renderer.
 */

export class CandleStreamProcessor {
  constructor(lifecycle, renderer, validator, store) {
    this.lifecycle = lifecycle;
    this.renderer = renderer;
    this.validator = validator;
    this.store = store;
  }

  /**
   * Entry point for raw websocket candle messages.
   */
  processEvent(event) {
    // 1. Validate event structure and data
    if (!this.validator.isValid(event)) return;

    // 2. Normalize (e.g., convert timestamps to seconds)
    const candle = this.normalizeEvent(event);

    // 3. Determine Lifecycle Action
    const lastCandle = this.store.getLatestCandle();
    const action = this.lifecycle.determineUpdateType(candle, lastCandle);

    if (action === 'UPDATE') {
      this.store.updateLatestCandle(candle);
      this.renderer.renderUpdate(candle);
    } else if (action === 'APPEND') {
      this.store.appendCandle(candle);
      this.renderer.renderUpdate(candle);
    }
  }

  normalizeEvent(event) {
    // Convert backend specific fields to standard OHLC
    return {
      time: event.t / 1000,
      open: event.o,
      high: event.h,
      low: event.l,
      close: event.c
    };
  }
}
