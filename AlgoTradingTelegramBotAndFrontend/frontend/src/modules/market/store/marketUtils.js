/**
 * Market Store Utilities
 * Handling candle merging, deduplication, and tick trimming.
 */

export const normalizeTimestamp = (ts) => {
    return new Date(ts).getTime() / 1000;
};

export const mergeCandles = (existing, incoming) => {
    // Logic to merge incoming candles into existing array based on timestamp
    const map = new Map(existing.map(c => [c.time, c]));
    incoming.forEach(c => map.set(c.time, c));
    return Array.from(map.values()).sort((a, b) => a.time - b.time);
};

export const trimHistory = (data, limit) => {
    if (data.length <= limit) return data;
    return data.slice(data.length - limit);
};
