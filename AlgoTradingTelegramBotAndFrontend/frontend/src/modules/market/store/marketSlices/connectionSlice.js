/**
 * @file connectionSlice.js
 * @description Enhanced state slice for managing WebSocket resilience and recovery.
 */

export const createConnectionSlice = (set, get) => ({
  connectionStatus: 'DISCONNECTED', // CONNECTING, CONNECTED, DISCONNECTED, RECONNECTING, STALE, ERROR
  lastError: null,
  lastHeartbeatTs: 0,
  reconnectAttempt: 0,
  isBrowserOffline: !navigator.onLine,

  setConnectionStatus: (status) => {
    set({ connectionStatus: status });
  },

  setLastError: (error) => {
    set({ lastError: error });
  },

  recordHeartbeat: () => {
    set({ lastHeartbeatTs: Date.now() });
  },

  setReconnectAttempt: (attempt) => {
    set({ reconnectAttempt: attempt });
  },

  setBrowserOffline: (isOffline) => {
    set({ isBrowserOffline: isOffline });
  }
});
