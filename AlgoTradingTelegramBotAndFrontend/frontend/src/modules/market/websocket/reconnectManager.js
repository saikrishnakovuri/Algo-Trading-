/**
 * @file reconnectManager.js
 * @description Manages WebSocket reconnection logic with exponential backoff.
 */

import { STREAM_CONFIG } from './streamConfig';

export class ReconnectManager {
  constructor(client) {
    this.client = client;
    this.attempts = 0;
    this.timer = null;
  }

  /**
   * Triggers a reconnection attempt.
   */
  trigger() {
    if (this.attempts >= STREAM_CONFIG.MAX_RECONNECT_ATTEMPTS) {
      console.error('[WS] Max reconnect attempts reached');
      return;
    }

    const delay = Math.min(
      STREAM_CONFIG.INITIAL_RECONNECT_DELAY * Math.pow(2, this.attempts),
      STREAM_CONFIG.MAX_RECONNECT_DELAY
    );

    console.log(`[WS] Reconnecting in ${delay}ms (Attempt ${this.attempts + 1})`);
    
    this.timer = setTimeout(() => {
      this.attempts++;
      this.client.connect();
    }, delay);
  }

  /**
   * Resets the reconnection counter.
   */
  reset() {
    this.attempts = 0;
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }
}
