/**
 * @file useMarketStore.js
 * @description Centralized Zustand store for market data.
 * Combines multiple slices for ticks, candles, signals, and connection state.
 */

import { create } from 'zustand';
import { createTickSlice } from './marketSlices/tickSlice';
import { createCandleSlice } from './marketSlices/candleSlice';
import { createSignalSlice } from './marketSlices/signalSlice';
import { createConnectionSlice } from './marketSlices/connectionSlice';
import { createMarketStateSlice } from './marketSlices/marketStateSlice';

/**
 * useMarketStore
 * The single source of truth for all realtime market data in the frontend.
 */
export const useMarketStore = create((set, get) => ({
  ...createTickSlice(set, get),
  ...createCandleSlice(set, get),
  ...createSignalSlice(set, get),
  ...createConnectionSlice(set, get),
  ...createMarketStateSlice(set, get),
}));
