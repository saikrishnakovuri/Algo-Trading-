import React, { useEffect, useState, useRef } from 'react';
import { createChart, ColorType } from 'lightweight-charts';

const CandleChart = ({ symbol, timeframe }) => {
    const chartContainerRef = useRef();
    const chartRef = useRef(null);
    const candleSeriesRef = useRef(null);

    useEffect(() => {
        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: '#0f1117' },
                textColor: '#DDD',
            },
            grid: {
                vertLines: { color: '#333' },
                horzLines: { color: '#333' },
            },
            width: chartContainerRef.current.clientWidth,
            height: 400,
            localization: {
                locale: 'en-IN',
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
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
            },
        });

        const candleSeries = chart.addCandlestickSeries();
        candleSeriesRef.current = candleSeries;
        chartRef.current = chart;

        // WebSocket Integration
        const ws = new WebSocket('ws://localhost:8000/api/candles/ws/live-candles');
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.symbol === symbol && data.timeframe === timeframe) {
                // IMPORTANT: Use data.time (bucket start) instead of data.timestamp (tick time)
                // to ensure the charting engine updates the CURRENT candle instead of 
                // appending a new one for every tick.
                candleSeries.update({
                    time: data.time || data.timestamp,
                    open: data.open,
                    high: data.high,
                    low: data.low,
                    close: data.close,
                });
            }
        };

        return () => chart.remove();
    }, [symbol, timeframe]);

    return <div ref={chartContainerRef} />;
};

export default CandleChart;
