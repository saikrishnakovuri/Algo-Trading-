/**
 * @file marketStateSlice.js
 * @description State slice for managing active symbol, timeframe, and transition status.
 */

export const createMarketStateSlice = (set, get) => ({
  activeSymbol: 'NIFTY',
  activeTimeframe: '5m',
  transitionStatus: 'IDLE', // IDLE, SWITCHING, LOADING_HISTORY, SYNCING, READY, ERROR
  transitionError: null,
  transitionToken: null, // Unique ID for race condition protection

  setActiveSymbol: (symbol) => {
    set({ activeSymbol: symbol });
  },

  setActiveTimeframe: (timeframe) => {
    set({ activeTimeframe: timeframe });
  },

  setTransitionStatus: (status) => {
    set({ transitionStatus: status });
  },

  setTransitionError: (error) => {
    set({ transitionError: error, transitionStatus: 'ERROR' });
  },

  setTransitionToken: (token) => {
    set({ transitionToken: token });
  }
});
