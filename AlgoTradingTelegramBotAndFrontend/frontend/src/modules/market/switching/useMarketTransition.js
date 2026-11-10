import { useCallback } from 'react';
import { useMarketStore } from '../store/useMarketStore';
import { MarketTransitionManager } from './MarketTransitionManager';

/**
 * useMarketTransition Hook
 * 
 * Exposes symbol/timeframe switching logic to React components
 * with built-in transition state awareness.
 */
export const useMarketTransition = () => {
    const activeSymbol = useMarketStore(state => state.activeSymbol);
    const activeTimeframe = useMarketStore(state => state.activeTimeframe);
    const transitionStatus = useMarketStore(state => state.transitionStatus);
    const transitionError = useMarketStore(state => state.transitionError);

    const switchSymbol = useCallback((newSymbol) => {
        if (newSymbol === activeSymbol) return;
        MarketTransitionManager.executeSwitch(newSymbol, activeTimeframe);
    }, [activeSymbol, activeTimeframe]);

    const switchTimeframe = useCallback((newTimeframe) => {
        if (newTimeframe === activeTimeframe) return;
        MarketTransitionManager.executeSwitch(activeSymbol, newTimeframe);
    }, [activeSymbol, activeTimeframe]);

    return {
        activeSymbol,
        activeTimeframe,
        transitionStatus,
        transitionError,
        switchSymbol,
        switchTimeframe,
        isTransitioning: transitionStatus !== 'READY' && transitionStatus !== 'IDLE' && transitionStatus !== 'ERROR'
    };
};
