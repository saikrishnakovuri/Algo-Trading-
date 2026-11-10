/**
 * Chart Configuration for TradingView Lightweight Charts
 */
export const chartConfig = {
    layout: {
        background: { type: 'solid', color: '#131722' },
        textColor: '#d1d4dc',
        fontSize: 12,
        fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    },
    grid: {
        vertLines: { color: '#2a2e39', style: 1 },
        horzLines: { color: '#2a2e39', style: 1 },
    },
    crosshair: {
        mode: 1, // CrosshairMode.Normal
        vertLine: {
            width: 1,
            color: '#758696',
            style: 3, // Dashed
            labelBackgroundColor: '#4c525e',
        },
        horzLine: {
            width: 1,
            color: '#758696',
            style: 3, // Dashed
            labelBackgroundColor: '#4c525e',
        },
    },
    priceScale: {
        borderColor: '#2a2e39',
        autoScale: true,
        alignLabels: true,
        borderVisible: true,
    },
    timeScale: {
        borderColor: '#2a2e39',
        timeVisible: true,
        secondsVisible: false,
        borderVisible: true,
        fixLeftEdge: true,
        rightOffset: 12,
        barSpacing: 6,
    },
    localization: {
        locale: 'en-IN',
        priceFormatter: price => price.toFixed(2),
        timeFormatter: (timestamp) => {
            const date = new Date(timestamp * 1000);
            return date.toLocaleString('en-IN', {
                timeZone: 'Asia/Kolkata',
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            });
        },
    },
};
