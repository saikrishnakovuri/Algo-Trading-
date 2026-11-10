import { create } from 'zustand';

interface MarketState {
  isConnected: boolean;
  setConnected: (status: boolean) => void;
}

export const useMarketStore = create<MarketState>((set) => ({
  isConnected: false,
  setConnected: (status) => set({ isConnected: status }),
}));
