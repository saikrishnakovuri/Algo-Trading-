/**
 * @file heartbeatManager.js
 * @description Monitors the health of the WebSocket connection via heartbeats.
 */

import { STREAM_CONFIG } from './streamConfig';

export class HeartbeatManager {
  constructor(client) {
    this.client = client;
    this.timer = null;
    this.lastReceived = 0;
  }

  /**
   * Starts the heartbeat monitoring.
   */
  start() {
    this.lastReceived = Date.now();
    this.timer = setInterval(() => {
      const now = Date.now();
      if (now - this.lastReceived > STREAM_CONFIG.HEARTBEAT_TIMEOUT) {
        console.warn('[WS] Heartbeat timeout. Forcing reconnect.');
        this.client.disconnect();
        this.client.reconnectManager.trigger();
      }
    }, STREAM_CONFIG.HEARTBEAT_INTERVAL);
  }

  /**
   * Called when a message is received to update the last received timestamp.
   */
  received() {
    this.lastReceived = Date.now();
  }

  /**
   * Stops heartbeat monitoring.
   */
  stop() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }
}
