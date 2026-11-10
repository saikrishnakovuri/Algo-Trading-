/**
 * Market Store Configuration
 * Memory limits and retention settings.
 */

export const STORE_CONFIG = {
    RETENTION: {
        TICKS: 1000,
        CANDLES: 500,
        SIGNALS: 100
    },
    UPDATE_THROTTLE_MS: 100, // Min time between store updates for high-freq ticks
};
