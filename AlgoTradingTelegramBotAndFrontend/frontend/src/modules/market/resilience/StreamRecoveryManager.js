/**
 * @file StreamRecoveryManager.js
 * @description Deterministically restores market streams and fills history gaps after reconnect.
 */

import { useMarketStore } from '../store/useMarketStore';
import { marketWS } from '../websocket/websocketClient';
import { CandleHistoryLoader } from '../rendering/CandleHistoryLoader';

export const StreamRecoveryManager = {
    /**
     * Orchestrates state restoration after a successful reconnect.
     */
    recover: async () => {
        const store = useMarketStore.getState();
        const symbol = store.activeSymbol;
        const timeframe = store.activeTimeframe;
        const token = store.transitionToken;

        console.log(`[Recovery] Attempting stream recovery for ${symbol}(${timeframe})...`);

        try {
            // 1. Fetch latest history to fill any gap during the disconnect period
            // We use the SAME loader as transitions to ensure consistency.
            const history = await CandleHistoryLoader.fetchHistory(symbol, timeframe);

            // 2. TOKEN-BASED INTEGRITY CHECK
            // If a transition was triggered DURING the recovery, abort this stale recovery.
            const currentStore = useMarketStore.getState();
            if (currentStore.transitionToken !== token) {
                console.warn('[Recovery] ABORTED stale recovery. A newer transition token is active.');
                return;
            }

            // 3. Update Store with fresh history (Synchronizes Chart automatically)
            store.setCandles(symbol, timeframe, history);

            // 4. Resubscribe WebSocket to the LIVE channel
            // Note: marketWS.connect() handles basic re-subscription from its internal set,
            // but we call it here explicitly for recovery-guarantee.
            marketWS.subscribe(symbol, timeframe);

            console.log(`[Recovery] Recovery COMPLETE for ${symbol}(${timeframe})`);
            store.setConnectionStatus('CONNECTED');

        } catch (err) {
            console.error('[Recovery] Recovery failed:', err);
            store.setConnectionStatus('STALE'); // Mark as stale so user knows data might be old
        }
    }
};
