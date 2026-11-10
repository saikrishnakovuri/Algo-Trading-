import { useMarketStore } from '../store/useMarketStore';
import { marketWS } from '../websocket/websocketClient';
import { CandleHistoryLoader } from '../rendering/CandleHistoryLoader';

/**
 * MarketTransitionManager
 * 
 * Orchestrates the complex lifecycle of switching symbols or timeframes.
 * Protected against race conditions using a unique transition token.
 */
export const MarketTransitionManager = {
    /**
     * Executes a coordinated switch to a new market segment
     * @param {string} newSymbol 
     * @param {string} newTimeframe 
     */
    executeSwitch: async (newSymbol, newTimeframe) => {
        const store = useMarketStore.getState();
        const oldSymbol = store.activeSymbol;
        const oldTimeframe = store.activeTimeframe;

        // 1. Generate Unique Transition Token
        const token = Date.now().toString() + Math.random().toString(36).substr(2, 9);
        store.setTransitionToken(token);

        // 2. Enter SWITCHING state
        store.setTransitionStatus('SWITCHING');
        console.log(`[Transition] Initiating switch to ${newSymbol}(${newTimeframe}) [Token: ${token}]`);

        try {
            // 3. PAUSE current stream
            marketWS.unsubscribe(oldSymbol, oldTimeframe);

            // 4. CLEANUP (Timers and old data)
            store.clearPendingUpdates(oldSymbol, oldTimeframe);
            store.clearCandles(oldSymbol, oldTimeframe);

            // 5. Update Active Selection
            store.setActiveSymbol(newSymbol);
            store.setActiveTimeframe(newTimeframe);

            // 6. FETCH HISTORY
            store.setTransitionStatus('LOADING_HISTORY');
            
            // Simulating network delay in demo/dev mode if fetch is too fast, but normally just fetch:
            const history = await CandleHistoryLoader.fetchHistory(newSymbol, newTimeframe);

            // --- RACE CONDITION PROTECTION ---
            // If the user clicked another symbol while we were fetching history,
            // the transitionToken in the store will have changed. We MUST abort
            // the rest of this transition to prevent stale data and duplicate subs.
            // This is safer than checking activeSymbol because it prevents A->B->A race bugs.
            const currentStore = useMarketStore.getState();
            if (currentStore.transitionToken !== token) {
                console.warn(`[Transition] ABORTED stale transition for ${newSymbol}(${newTimeframe}) [Token: ${token}]. Newer request active.`);
                return;
            }

            // 7. SYNC STORE & CHART
            store.setTransitionStatus('SYNCING');
            store.setCandles(newSymbol, newTimeframe, history);

            // 8. RESUME STREAM
            marketWS.subscribe(newSymbol, newTimeframe);

            // 9. READY
            store.setTransitionStatus('READY');
            console.log(`[Transition] ${newSymbol}(${newTimeframe}) is now READY [Token: ${token}]`);

        } catch (err) {
            console.error(`[Transition] Switch failed for ${newSymbol} [Token: ${token}]:`, err);
            
            // Only set error if we are still the active transition attempt
            const currentStore = useMarketStore.getState();
            if (currentStore.transitionToken === token) {
                store.setTransitionError(err.message);
            }
        }
    }
};
