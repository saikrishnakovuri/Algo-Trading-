import { api, fetchApi } from '../../../api';
import { useMarketStore } from '../store/useMarketStore';

/**
 * CandleHistoryLoader
 * 
 * Responsibilities:
 * - Fetch historical candle data via REST API
 * - Normalize data for the market store
 * - Handle loading states and errors
 */
export const CandleHistoryLoader = {
    /**
     * Fetches historical candles for a specific symbol and timeframe
     * @param {string} symbol 
     * @param {string} timeframe 
     * @param {number} limit 
     * @returns {Promise<Array>}
     */
    fetchHistory: async (symbol, timeframe, limit = 500) => {
        try {
            const endpoint = `/candles/history?symbol=${symbol}&timeframe=${timeframe}&limit=${limit}`;
            console.log(`[HistoryLoader] Fetching history from ${endpoint}...`);
            const data = await fetchApi(endpoint);
            
            // Polling workaround removed. Real-time updates are now handled by WebSocket.
            if (window.candlePollInterval) {
                clearInterval(window.candlePollInterval);
                window.candlePollInterval = null;
            }

            return data;
        } catch (err) {
            console.error(`[HistoryLoader] Failed to fetch history for ${symbol}:`, err);
            return [];
        }
    }
};
