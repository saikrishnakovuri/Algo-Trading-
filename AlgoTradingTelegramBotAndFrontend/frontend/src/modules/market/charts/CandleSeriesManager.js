import { normalizeCandle, isValidCandle } from './chartUtils';

/**
 * CandleSeriesManager Class
 * 
 * Responsibilities:
 * - Manage TradingView series updates
 * - Distinguish between series.update() (realtime) and series.setData() (historical)
 * - Prevent duplicate candles and ensure strict chronological ordering
 * - Centralized data transformation for the chart engine
 */
export class CandleSeriesManager {
    /**
     * @param {Object} series - TradingView Candlestick Series object
     */
    constructor(series) {
        if (!series) throw new Error('CandleSeriesManager requires a series instance');
        this.series = series;
        this.lastCandleTime = null;
    }

    /**
     * Set initial historical data
     * Use series.setData() for bulk initialization
     * @param {Array<Object>} data - Array of raw candle data
     */
    setInitialData(data) {
        if (!Array.isArray(data)) return;

        // 1. Normalize and Validate
        const normalizedData = data
            .map(normalizeCandle)
            .filter(isValidCandle);

        // 2. Sort chronologically (TradingView requirement)
        normalizedData.sort((a, b) => a.time - b.time);

        // 3. Deduplicate by timestamp
        const uniqueData = [];
        const seenTimes = new Set();
        for (const candle of normalizedData) {
            if (!seenTimes.has(candle.time)) {
                uniqueData.push(candle);
                seenTimes.add(candle.time);
            }
        }

        if (uniqueData.length > 0) {
            this.series.setData(uniqueData);
            this.lastCandleTime = uniqueData[uniqueData.length - 1].time;
        }
    }

    /**
     * Update latest candle or append a new one
     * Use series.update() for incremental updates as per Rule 1
     * @param {Object} candle - Raw candle data
     */
    updateCandle(candle) {
        const normalized = normalizeCandle(candle);
        if (!isValidCandle(normalized)) return;

        // Safety check: Don't update with older candles than the last known time
        // unless it's the exact same timestamp (which is an update to the current candle)
        if (this.lastCandleTime !== null && normalized.time < this.lastCandleTime) {
            console.warn(`[Chart] Ignoring out-of-order candle: ${normalized.time} < ${this.lastCandleTime}`);
            return;
        }

        // series.update() handles:
        // - Replacement if time matches latest
        // - Append if time is greater than latest
        this.series.update(normalized);
        this.lastCandleTime = normalized.time;
    }

    /**
     * Clears the series data
     */
    clear() {
        this.series.setData([]);
        this.lastCandleTime = null;
    }
}
