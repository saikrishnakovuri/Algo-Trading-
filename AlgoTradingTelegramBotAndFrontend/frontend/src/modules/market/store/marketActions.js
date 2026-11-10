/**
 * @file marketActions.js
 * @description Action creators and dispatch helpers for the market store.
 */

import { useMarketStore } from './useMarketStore';

/**
 * Convenience wrapper for store actions.
 * In a real app, these might be used for complex multi-slice updates.
 */
export const marketActions = {
  updateMarketData: (event) => {
    const store = useMarketStore.getState();
    
    switch (event.type) {
      case 'tick':
        store.addTick(event);
        break;
      case 'candle':
        store.updateCandle(event);
        break;
      case 'signal':
        store.addSignal(event);
        break;
      default:
        console.warn('Unknown market event type:', event.type);
    }
  },
  
  setConnectionStatus: (status) => {
    useMarketStore.getState().setConnectionStatus(status);
  }
};
