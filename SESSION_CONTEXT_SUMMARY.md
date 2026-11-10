# AlgoTrading Project Context & Architecture

## 1. Core Architecture
The project is a sophisticated multi-strategy framework built for automated trading on the Indian stock market (NSE) using the Angel One SmartApi.
- **live_trader_v1.py**: The legacy live/paper trader relying on the REST API polling method.
- **live_trader_v2.py**: The next-generation production trader. It uses a **WebSocket + Redis** architecture (`modules/data/websocket_feed.py` and `candle_builder.py`) for high-speed, tick-by-tick data access, completely bypassing the old REST API rate limits and 0.5s sleep intervals.
- **Strategy Selector (`modules/strategy_selector.py`)**: Evaluates signals from multiple engines simultaneously and selects the one with the highest confidence.

## 2. Active Trading Engines
- **Mean Reversion Engine (`modules/mean_reversion_engine.py`)**: The top-performing strategy (+0.985R expectancy). It fades price extremes using Bollinger Bands, VWAP Bands, and RSI. Crucially, it includes an **anti-trend filter** to avoid trading into strong momentum.
- **Momentum Breakout Engine (`modules/momentum_engine.py`)**: Detects tight consolidations and volume-backed breakouts.
- **Candlestick Engine**: Currently disabled due to underperformance.

## 3. Trade & Risk Management
- **Trailing SL Manager (`modules/trailing_sl_manager.py`)**: Manages graduated partial profit booking at pre-defined R-multiples (e.g., T1 at 1R, T2 at 2R) and automatically trails the stop-loss to protect profits.
- **State Persistence (`active_trades.json`)**: Ensures the bot remembers open positions and TSL levels across restarts.
- **Position Sizing**: Currently, both `v1` and `v2` live traders are hardcoded to a **flat 1% risk** (e.g., 10,000 INR on 10L capital). The proposed "Confidence-Based Scaling" (0.5% to 2.0% risk) or the advanced SMC-tier sizer (`modules/risk_exec/sizer.py`) are **not yet integrated** into the main execution loop.
- **Concurrency Limit**: Hardcoded to a maximum of 3 active trades to prevent systemic risk.

## 4. Operational Rules & Limitations
- **Trading Window**: 09:15 AM to 03:30 PM IST. No new entries are allowed after 02:30 PM.
- **Confidence Threshold**: Only signals with `> 60%` confidence are executed.
- **Data Architecture**: `live_trader_v2.py` successfully implements the WebSocket + Redis pipeline, allowing for high-frequency scanning without REST API polling limits. `live_trader_v1.py` still suffers from the Angel One REST API strict limits (AB1021 error) and uses a 0.5s sleep interval.
- **Notifications**: Integrated Telegram bot alerts for entries, exits, heartbeats, and rejected signals.