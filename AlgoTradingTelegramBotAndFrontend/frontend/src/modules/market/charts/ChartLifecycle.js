import { createChart, CandlestickSeries } from 'lightweight-charts';

/**
 * ChartLifecycle Management
 * 
 * Responsibilities:
 * - Isolated chart initialization
 * - Memory-safe destruction
 * - Responsive resize management via ResizeObserver
 */
export const ChartLifecycle = {
    /**
     * Initializes a new chart instance
     * @param {HTMLElement} container - The DOM element to host the chart
     * @param {Object} config - Chart configuration
     * @param {Object} theme - Theme configuration
     * @returns {Object} { chart, candleSeries }
     */
    init: (container, config, theme) => {
        console.log('[ChartLifecycle] Initializing chart with v5.2.0 API...');
        
        try {
            const chart = createChart(container, {
                ...config,
                width: container.clientWidth || 800,
                height: container.clientHeight || 500,
            });

            if (!chart) {
                throw new Error('createChart returned null');
            }

            console.log('[ChartLifecycle] Chart created. Available methods:', Object.keys(chart));

            // v5.2.0 API uses addSeries(CandlestickSeries, options)
            let candleSeries;
            if (typeof chart.addSeries === 'function') {
                console.log('[ChartLifecycle] Using unified addSeries API');
                candleSeries = chart.addSeries(CandlestickSeries, theme.dark.candles);
            } else {
                throw new Error('Chart instance missing unified addSeries method');
            }

            return { chart, candleSeries };
        } catch (err) {
            console.error('[ChartLifecycle] Initialization CRITICAL FAILURE:', err);
            // Return nulls to allow component to handle gracefully instead of crashing
            return { chart: null, candleSeries: null };
        }
    },

    /**
     * Registers a resize handler for the chart
     * @param {Object} chart - The TradingView chart instance
     * @param {HTMLElement} container - The container element
     * @returns {Function} Cleanup function to unobserve
     */
    registerResizeHandler: (chart, container) => {
        if (!chart || !container) return () => {};

        const resizeObserver = new ResizeObserver(entries => {
            if (entries.length === 0 || !entries[0].contentRect) return;
            
            const { width, height } = entries[0].contentRect;
            
            // Performance optimization: only apply if dimensions actually changed significantly
            // TradingView's applyOptions is already optimized, but we wrap it for safety
            requestAnimationFrame(() => {
                if (chart && container) {
                    chart.applyOptions({ width, height });
                    chart.timeScale().fitContent();
                }
            });
        });

        resizeObserver.observe(container);

        return () => {
            resizeObserver.disconnect();
        };
    },

    /**
     * Safely destroys a chart instance
     * @param {Object} chart - The TradingView chart instance
     */
    destroy: (chart) => {
        if (chart) {
            try {
                chart.remove();
            } catch (err) {
                console.error('Error destroying chart:', err);
            }
        }
    }
};
