/**
 * @file useMarketStream.js
 * @description React hook for integrating the market WebSocket stream into the frontend.
 * Manages the connection lifecycle and dispatches incoming events to the Zustand store.
 */

import { useEffect } from 'react';
import { marketWS as wsClient } from './websocketClient';
import { useMarketStore } from '../store/useMarketStore';

/**
 * useMarketStream Hook
 * Initializes the WebSocket connection on mount and cleans up on unmount.
 */
export function useMarketStream() {
  const { addTick, updateCandle, addSignal, setConnectionStatus } = useMarketStore();

  useEffect(() => {
    // Connect to WebSocket
    wsClient.connect();

    // The current wsClient (marketWS) automatically dispatches to store via its internal onmessage.
    // It does NOT support a callback-based subscription in the way this hook was written.
    // We keep the hook for connection lifecycle management only.
    
    return () => {
      // marketWS is a singleton and manages its own lifecycle.
      // We don't disconnect on every unmount to maintain the connection across tab switches.
      console.log('[useMarketStream] Component unmounted - maintaining WS singleton');
    };
  }, []); // Only run once on mount

  // Return connection status for UI components
  return {
    status: wsClient.status,
  };
}
