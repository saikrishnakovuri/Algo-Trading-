/**
 * Chart Theme definitions
 */
export const chartTheme = {
    dark: {
        background: '#131722',
        text: '#d1d4dc',
        grid: '#2a2e39',
        candles: {
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderUpColor: '#26a69a',
            borderDownColor: '#ef5350',
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        },
        volume: {
            upColor: 'rgba(38, 166, 154, 0.5)',
            downColor: 'rgba(239, 83, 80, 0.5)',
        }
    },
    // Kite/Zerodha style
    kite: {
        background: '#ffffff',
        text: '#444444',
        grid: '#f0f3fa',
        candles: {
            upColor: '#4caf50',
            downColor: '#f44336',
            borderUpColor: '#4caf50',
            borderDownColor: '#f44336',
            wickUpColor: '#4caf50',
            wickDownColor: '#f44336',
        }
    }
};
