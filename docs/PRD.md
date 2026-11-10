# AlgoTrading V2 — WebSocket Architecture PRD
**Last Updated:** April 2026

## Original Problem Statement
Transition the live trading bot from REST API polling (13 stocks, rate-limited) to real-time WebSocket streaming (1500+ NSE stocks) using Angel One SmartWebSocketV2, Redis as in-memory store, and a tiered scanning architecture.

## Architecture Overview
```
WebSocket Feed (3 connections) → Redis Pub/Sub → Candle Builder → Redis Lists
                                                                      ↓
                                                              Live Trader V2
                                                              (reads from Redis)
                                                                      ↓
                                                              Order Execution
                                                              (REST API - Angel One)
```

## Core Components Implemented

### Phase 1: WebSocket Feed Manager (modules/data/websocket_feed.py)
- SmartWebSocketV2 integration with Angel One
- Authentication via existing broker credentials
- Robust reconnection with exponential backoff
- Tick data pushed to Redis pub/sub and hash keys
- **Status: COMPLETE**

### Phase 2: Real-Time Candle Builder (modules/data/candle_builder.py)
- Consumes ticks from Redis pub/sub
- Builds 1m and 5m OHLCV candles with IST boundary alignment
- Rolling 100 candles per stock in Redis lists
- Live (forming) candle tracking
- Day reset at 09:15 and cache save at 15:30
- Verification script: scripts/verify_candles.py
- **Status: COMPLETE**

### Phase 3: Live Trader V2 (live_trader_v2.py)
- Redis-powered data reads via modules/data/redis_data_reader.py
- Live tick price for accurate exit monitoring (not stale 5m close)
- 5-second exit monitoring loop, 5m entry scanning gate
- Warm-up phase: waits for 20+ candles before trading
- Stale data detection and graceful Redis fallback
- All existing logic preserved: TSL, journal, Telegram, meta_log
- **Status: COMPLETE**

### Phase 4: Scale to 1500+ Stocks
- scripts/generate_full_universe.py — auto-generates universe_full.yaml
- 3-tier stock classification (NIFTY50 / NIFTY200 / Rest)
- WebSocketPool: 3 connections (Mode 3/2/1 per tier)
- Tiered scan frequency: T1/T2 every 5m, T3 every 15m
- Signal ranking: sorts by tier + confidence for position slot allocation
- scripts/backfill_at_open.py — REST API backfill at market open
- Previous-day candle cache for cold-start resilience
- run_live_v2.py — production watchdog launcher with auto-restart
- System monitoring: CPU, memory, Redis health, Telegram alerts
- **Status: COMPLETE**

## Configuration
- max_open_positions_v2: **10** (in config/paper_mode.yaml)
- Scan tiers: T1 (50 stocks), T2 (150 stocks), T3 (~1300 stocks)
- WebSocket modes: T1=Full(3), T2=Quote(2), T3=LTP(1)
- Risk per trade: 1% of capital
- Daily loss cap: 2%, Weekly loss cap: 4%

## User Personas
- **Primary**: Algorithmic trader running intraday momentum + mean reversion strategies on NSE
- **Mode**: Paper trading (validation phase) → Live trading

## What's Been Implemented (Timeline)
- Day 1: Phase 1 (WebSocket) + Phase 2 (Candle Builder) + Paper trading
- Day 2: Phase 3 (Live Trader V2) + Phase 4 (Scale + Orchestration)
- Day 2 P&L: TATASTEEL -4,049.50 | TCS -5,178.80 | RELIANCE +7,181.10 = Net -2,047.20
- Overall: +45k from Day 1

## Tech Stack
- Python 3.x (standalone CLI, no web UI)
- Angel One SmartAPI (SmartConnect + SmartWebSocketV2)
- Redis (in-memory store, pub/sub)
- Telegram Bot (notifications)
- Pandas, NumPy, pandas-ta (analysis)

## Backlog / Future Enhancements
- P0: Run Paper Mode on full 1500 stocks for 3-5 days to validate stability
- P1: Add dynamic position sizing based on account equity (not fixed 1% of 10L)
- P1: Implement sector-level correlation limits (e.g., max 3 bank stocks simultaneously)
- P2: Add a lightweight web dashboard (Streamlit/Dash) for real-time P&L monitoring
- P2: ML-based signal confidence scoring using historical meta_db data
- P3: Options chain integration for hedged entries
