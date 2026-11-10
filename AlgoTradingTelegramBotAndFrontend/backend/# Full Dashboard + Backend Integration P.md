# Full Dashboard + Backend Integration Prompt

## OBJECTIVE
Replicate the TradeAlert dashboard UI (https://algo-telegram-trade.preview.emergentagent.com/) and connect it to our live options trading bot (live_options_trader.py). The dashboard must show REAL data from our bot, allow manual trade control, and include a custom backtesting module.

**STRICTLY PRESERVE all existing trading logic in live_options_trader.py.**

---

## REFERENCE UI (What to Replicate)

Dark-themed professional trading terminal with:
- **Sidebar Navigation**: Dashboard, Trades, Alert Logs, New Trade, Analytics, Risk Lab, Backtesting, Integration, Settings
- **Theme**: Dark background (#0f1117), card borders (#1e2130), green for profit, red for loss, cyan accents
- **Font**: Monospace for numbers, sans-serif for labels
- **Status indicators**: Green "LIVE" dot, "ACTIVE/INACTIVE" bot status

---

## PAGES TO BUILD (React Frontend)

### PAGE 1: DASHBOARD (Main)
```
┌─────────────────────────────────────────────────────────────────┐
│ Header: "TradeAlert BOT TERMINAL"     [Refresh] [Test Alert] ● LIVE │
├─────────────────────────────────────────────────────────────────┤
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐    │
│ │TOTAL     │ │WIN RATE  │ │TOTAL PNL │ │BOT STATUS        │    │
│ │TRADES: 40│ │48.6%     │ │+₹3,450   │ │ACTIVE            │    │
│ │37 done   │ │18W / 19L │ │Avg: +₹93 │ │Chat: 1003385502  │    │
│ └──────────┘ └──────────┘ └──────────┘ └──────────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│ CUMULATIVE PNL (line chart w/ green fill) │ RECENT ALERTS       │
│ [Interactive chart with dates on X-axis] │ EXIT TRD-xxx  sent   │
│                                          │ ENTRY TRD-xxx sent   │
│                                          │ ENTRY TRD-xxx failed │
├─────────────────────────────────────────────────────────────────┤
│ RECENT TRADES table:                                            │
│ Trade ID | Symbol | Dir | Event | Entry | PNL | Strategy | Time │
│ TRD-xxx  | NIFTY  | BUY | EXIT  |₹22000 |+₹500| MR      | 11:55│
└─────────────────────────────────────────────────────────────────┘

ALSO ADD (not in reference, our custom additions):
- Current Regime badge: "TRENDING_UP" / "RANGING" / etc.
- Current VIX value display
- Active Context: "VWAP_PULL + TRAIL_ATR"
- Trades Today counter: "1/3 (1-loss stop: NOT triggered)"
- Capital display: "₹10,03,200"
```

### PAGE 2: TRADES (Full History)
```
- Filterable table with ALL trades from MongoDB
- Columns: Date, Time, Stock, Direction(CE/PE), Entry Price, Exit Price,
  Exit Reason, Context Tags, SL Type, TP Type, Gross PnL, Costs, Net PnL,
  R-Multiple, Duration(mins), Strategy
- Filters: Date range, Stock dropdown, Direction, Win/Loss, Strategy, Context
- Export to CSV button
- Summary row at bottom: Total Trades, Total P&L, Avg Win, Avg Loss
```

### PAGE 3: ALERT LOGS
```
- All Telegram notifications sent/failed
- Columns: Timestamp, Trade ID, Alert Type (ENTRY/EXIT/TP/SL/HEARTBEAT),
  Message Preview, Status (sent/failed/pending)
- Filter by type and status
```

### PAGE 4: NEW TRADE (Manual Entry)
```
- Form to place manual trades (bypasses signal generation):
  - Stock: Dropdown (NIFTY, BANKNIFTY, RELIANCE, etc.)
  - Direction: CE (Long) / PE (Short) toggle
  - Lots: Number input (1-5)
  - Entry Type: MARKET / LIMIT (with price input for limit)
  - Stop Loss: Input (₹ or % or ATR-based dropdown)
  - Target: Input (₹ or R-multiple or Trail)
  - [PLACE TRADE] button (with confirmation modal)
  
- Active Positions Panel:
  - Show all currently open positions
  - Each position has: [CLOSE] button, current P&L (live updating)
  - [CLOSE ALL] emergency button (red, with double-confirm)
  
- Bot Control:
  - [PAUSE BOT] / [RESUME BOT] toggle
  - Status: "Bot is ACTIVE" or "Bot is PAUSED (exits still monitored)"
```

### PAGE 5: ANALYTICS
```
- Equity Curve Chart (daily capital, area chart with green fill)
- Monthly P&L Bar Chart (green bars for profit months, red for loss)
- Win Rate Donut Chart
- Performance Metrics Cards:
  - Sharpe Ratio, Sortino Ratio, Calmar Ratio
  - Max Drawdown %, Max DD Duration
  - Profit Factor, Expectancy per trade
  - Best Day, Worst Day
- Context Performance Table:
  | Context | Trades | Win Rate | Net PnL | Avg R |
  | TRENDING_DOWN + TRAIL | 45 | 40% | +₹18K | 1.8 |
  | SUPPORT_BOUNCE + PARTIAL | 30 | 54% | +₹12K | 0.9 |
- Stock Leaderboard:
  | Stock | Trades | Net PnL | Best Context |
```

### PAGE 6: RISK LAB
```
- Monte Carlo Simulation:
  - Input: number of simulations (1000-10000), trading days (252)
  - Output: Probability distribution chart, confidence intervals
  - Shows: P(ruin), P(target), Expected range of outcomes
  
- Position Size Calculator:
  - Input: Capital, Risk %, Stop Distance, Stock Price
  - Output: Shares/Lots to buy, Position Value, Max Loss
  
- Kelly Criterion Calculator:
  - Based on historical win rate and avg win/loss ratio
  - Shows: Optimal fraction, Half-Kelly (recommended)
  
- Drawdown Analysis:
  - Chart showing historical drawdown periods
  - Recovery time for each drawdown
  - Current drawdown status
```

### PAGE 7: BACKTESTING (NEW - Our Custom Addition)
```
THIS IS THE KEY ADDITION. Allow running backtests from the dashboard.

- Backtest Configuration Form:
  - Stock Universe: Multi-select (NIFTY50, Midcap, Custom list)
  - Date Range: Start date, End date picker
  - Entry Strategy: Dropdown (VWAP_BOUNCE, MOMENTUM_FOLLOW, LIQUIDITY_TRAP, etc.)
  - SL Type: Dropdown (ATR_1, ATR_2, EMA20, EMA50, SWING, CANDLE, FIXED_1PCT)
  - TP Type: Dropdown (FIX_1.5R, FIX_2R, FIB, SR, PARTIAL_1R, PARTIAL_1.5R, TRAIL_ATR)
  - Capital: Input (default ₹10,00,000)
  - Risk per trade: Input (default 1%)
  - Confidence threshold: Slider (50-90%)
  - Context filter: Checkboxes (TRENDING_UP, TRENDING_DOWN, LOW_VOL, SUPPORT_BOUNCE, VWAP_PULL)
  
  [RUN BACKTEST] button
  
- Results Display (after backtest completes):
  - Summary cards: Total Return, Max DD, Win Rate, Profit Factor, Trades
  - Equity curve chart
  - Trade-by-trade table
  - Monthly breakdown
  - Exit reason pie chart (TARGET/SL/TRAIL/TIME/EOD)
  - Context breakdown table
  
- Backtest History: List of previously run backtests with results
- Compare: Select 2-3 backtests and show side-by-side comparison

- GRID SEARCH MODE:
  - Select multiple SL types + multiple TP types
  - Runs all combinations
  - Shows ranked results table (like our 343-combo test)
  - Highlight top 5 winners
```

### PAGE 8: INTEGRATION
```
- Connection Status Panel:
  - Bot Heartbeat: Last received timestamp, latency
  - MongoDB: Connected/Disconnected
  - Telegram: Bot active, chat ID confirmed
  - Angel One API: Authenticated/Expired
  
- API Configuration (read-only display, edit in .env):
  - Telegram Bot Token: ****masked****
  - Chat ID: displayed
  - Angel One Client ID: ****masked****
  - MongoDB URL: ****masked****
  
- Webhook/Event Log: Last 20 events received from bot
```

### PAGE 9: SETTINGS
```
- Risk Parameters (read from bot config, editable):
  - Max Daily Loss: ₹30,000
  - Max Weekly Loss: ₹60,000
  - Max Trades/Day: 3
  - Consecutive Loss Stop: 1
  - Risk per Trade: 1%
  - Leverage Cap: 5x
  
- No Trade Zones (toggleable):
  - [✓] RANGING
  - [✓] HIGH_VOL
  - [✓] VWAP_PUSH
  - [✓] EMA_BOUNCE
  
- Decision Tree Display (visual/table):
  - Shows current adaptive exit rules
  
- Bot Mode Toggle: PAPER / LIVE (with confirmation for LIVE)
```

---

## BACKEND ENDPOINTS (FastAPI - Add to existing server.py)

### Bot Communication:
```
POST /api/bot/{event_type}       — Receive events from trading bot
GET  /api/live/status            — Current bot state (from heartbeat)
GET  /api/live/positions         — Active open positions
GET  /api/live/signals           — Recent signals (taken + skipped)
```

### Manual Control:
```
POST /api/control/close-position — Force close a position
POST /api/control/close-all      — Emergency close all
POST /api/control/manual-trade   — Place manual trade via command queue
POST /api/control/pause-bot      — Pause signal generation
POST /api/control/resume-bot     — Resume bot
GET  /api/control/command-history — Recent manual commands
```

### Analytics:
```
GET  /api/analytics/summary      — Overall performance metrics
GET  /api/analytics/pnl-history  — Daily P&L array for charting
GET  /api/analytics/equity-curve — Capital over time
GET  /api/analytics/context-perf — Performance by context tag
GET  /api/analytics/stock-perf   — Performance by stock
GET  /api/analytics/risk         — Sharpe, Sortino, Calmar, Max DD
GET  /api/analytics/monte-carlo  — Run MC simulation
GET  /api/analytics/position-size — Calculate position size
```

### Backtesting:
```
POST /api/backtest/run           — Start a backtest (async, returns job_id)
GET  /api/backtest/status/{id}   — Check backtest progress
GET  /api/backtest/result/{id}   — Get completed backtest results
GET  /api/backtest/history       — List all past backtests
POST /api/backtest/grid-search   — Run multi-combo grid search
DELETE /api/backtest/{id}        — Delete a backtest
```

### Existing endpoints (KEEP):
```
All existing /api/trades/*, /api/alerts/*, /api/scheduler/* endpoints stay unchanged
```

---

## BACKTESTING BACKEND (Key Addition)

Create: `backend/backtest_engine.py`

This module receives backtest parameters from the frontend and runs the simulation:

```python
class BacktestEngine:
    def run(self, config: dict) -> dict:
        """
        config = {
            "stocks": ["RELIANCE", "HDFCBANK", ...],
            "start_date": "2025-12-01",
            "end_date": "2026-03-31",
            "entry_strategy": "VWAP_BOUNCE",
            "sl_type": "ATR_2",
            "tp_type": "TRAIL_ATR",
            "capital": 1000000,
            "risk_pct": 1.0,
            "confidence_threshold": 75,
            "contexts_allowed": ["TRENDING_DOWN", "LOW_VOL", "VWAP_PULL"]
        }
        """
        # Load historical data from data/angel_historical/{stock}_1m.csv
        # Resample to 5m
        # Run signal detection (same engines as live bot)
        # Simulate trades with exact same exit logic
        # Return results dict with trade log, metrics, equity curve
```

For grid search:
```python
def grid_search(self, config: dict) -> dict:
    """
    config = {
        ...same as above...
        "sl_types": ["ATR_1", "ATR_2", "EMA20", "SWING"],
        "tp_types": ["FIX_2R", "FIB", "TRAIL_ATR", "PARTIAL_1R"]
    }
    """
    # Run all combinations in parallel
    # Return ranked results
```

IMPORTANT: The backtest engine must import and use the SAME signal detection and exit logic from the live bot modules. DO NOT rewrite the strategy. Import from:
- modules/options/signal_adapter.py (for signal generation)
- modules/options/exit_selector.py (for adaptive exits)
- modules/options/risk_manager.py (for risk rules)

---

## TRADING BOT SIDE (Add to live_options_trader.py)

Create: `modules/dashboard_bridge.py`
- Non-blocking HTTP push to backend on every event
- Fire-and-forget pattern (threading, never blocks main loop)
- Events: BOOT, SIGNAL, TRADE_OPEN, TRADE_CLOSE, TRADE_UPDATE, HEARTBEAT (60s), DAILY_SUMMARY

Add to main loop:
- Command listener: checks Redis/file for manual commands every iteration
- Pause support: if paused, skip signal scanning but keep exit monitoring

---

## CRITICAL RULES

1. NEVER modify trading logic (signal generation, exit decisions, adaptive tree)
2. Dashboard bridge must be fault-tolerant (backend down = bot continues silently)
3. All HTTP pushes from bot are non-blocking (threading/async)
4. Manual commands go through a queue (Redis or file) — never directly mutate bot state
5. Backtest engine imports REAL modules — no reimplementation
6. Use INR (₹) not USD ($) for all amounts
7. Dark theme matching reference UI exactly
8. Auto-refresh dashboard every 5 seconds for live data
9. Telegram notifications continue working alongside dashboard
10. MongoDB for persistence (trades, alerts, backtest results, analytics)

---

## IMPLEMENTATION ORDER

1. Backend: Add new endpoints to server.py
2. Backend: Create backtest_engine.py (imports real modules)
3. Trading Bot: Create modules/dashboard_bridge.py
4. Trading Bot: Add bridge calls + command listener to live_options_trader.py
5. Frontend: Build all 9 pages with React components
6. Frontend: Connect to backend APIs
7. Test: Run bot in paper mode, verify data flows to dashboard
8. Test: Run a backtest from UI, verify results display

---

## DATA FLOW DIAGRAM

```
┌──────────────────┐        ┌─────────────────┐        ┌──────────────┐
│ live_options_    │ HTTP   │ FastAPI Backend  │  REST  │ React        │
│ trader.py        │───────►│ server.py        │◄──────│ Frontend     │
│                  │        │                 │        │              │
│ Pushes:          │        │ Stores: MongoDB │        │ Displays:    │
│ - Heartbeats     │        │ Serves: REST API│        │ - Live data  │
│ - Trade events   │        │ Runs: Backtests │        │ - Charts     │
│ - Signals        │        │                 │        │ - Controls   │
│                  │◄───────│ Commands:       │        │              │
│ Reads:           │  Queue │ - Close pos     │◄──────│ Sends:       │
│ - Manual cmds    │        │ - Manual trade  │ POST  │ - Commands   │
│ - Pause/Resume   │        │ - Pause/Resume  │        │ - Backtest   │
└──────────────────┘        └────────┬────────┘        └──────────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │ Telegram Bot    │
                            │ (Notifications) │
                            └─────────────────┘
```

---

## NOW — RE-THINK AND ADD:

Before implementing, consider:
- Should the dashboard have a "Paper vs Live" visual indicator (green border = paper, red = live)?
- Should backtests save to MongoDB so you can track backtest history over time?
- Should there be a "Strategy Optimizer" page that auto-runs grid search weekly?
- Any websocket support for real-time position updates (instead of 5s polling)?
- Should the dashboard show a "Market Status" indicator (Pre-open, Open, Closed)?
- Add dark/light theme toggle? (probably keep dark only for trading focus)

Add your own enhancements. Implement.