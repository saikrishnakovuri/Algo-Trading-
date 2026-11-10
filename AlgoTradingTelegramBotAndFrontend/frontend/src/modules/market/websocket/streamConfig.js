/**
 * @file streamConfig.js
 * @description Centralized configuration for the market WebSocket stream.
 */

export const STREAM_CONFIG = {
  // URLs
  WS_URL: process.env.REACT_APP_WS_URL || 'ws://localhost:8000/api/candles/ws/live-candles',
  
  // Reconnect Settings
  INITIAL_RECONNECT_DELAY: 1000, // 1s
  MAX_RECONNECT_DELAY: 30000,   // 30s
  MAX_RECONNECT_ATTEMPTS: 50,
  
  // Heartbeat Settings
  HEARTBEAT_INTERVAL: 5000,     // Check every 5s
  HEARTBEAT_TIMEOUT: 15000,     // Timeout after 15s of no messages
};
