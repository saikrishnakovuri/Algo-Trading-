/**
 * @file signalSlice.js
 * @description State slice for managing trading signals.
 */

import { STORE_CONFIG } from '../storeConfig';

export const createSignalSlice = (set, get) => ({
  signals: [], // Array of latest signals

  addSignal: (signal) => {
    set((state) => ({
      signals: [signal, ...state.signals].slice(0, STORE_CONFIG.MAX_SIGNAL_RETENTION),
    }));
  },

  clearSignals: () => {
    set({ signals: [] });
  },
});
