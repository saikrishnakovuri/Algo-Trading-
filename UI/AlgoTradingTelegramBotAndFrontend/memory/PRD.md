# TradeAlert Bot — Product Requirements Document

## Overview
A modular, production-ready Telegram alert bot integrated with an algorithmic trading system.
Sends real-time structured trade notifications (entry, exit, SL, TP, signals) with a full analytics dashboard.

**App URL:** https://algo-telegram-trade.preview.emergentagent.com
**Telegram Bot:** @algo_trading_22042026_bot

---

## Architecture

### Backend (FastAPI + MongoDB)
- `server.py` — Main FastAPI app with all API endpoints
- `notification_service.py` — Standalone Telegram notification module (importable)
- Database: MongoDB `tradealert_db`, collections: `trades`, `alerts`

### Frontend (React + Recharts + Tailwind)
- Dark "Terminal" theme — #050505 bg, JetBrains Mono for data
- Pages: Dashboard, Trade History, Alert Logs, New Trade, Analytics
- Component: Layout (sidebar nav)

---

## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/trades/notify | Submit trade event + send Telegram alert |
| POST | /api/trades/test | Send test alert (no DB write) |
| POST | /api/trades/preview | Preview message without sending |
| GET | /api/trades | List trades (filterable) |
| GET | /api/trades/count | Total trade count |
| GET | /api/alerts | List alert logs |
| GET | /api/analytics/summary | Overall stats |
| GET | /api/analytics/pnl-history | Cumulative PnL data |
| GET | /api/bot/status | Bot configuration status |
| GET | /api/bot/discover-chat | Discover Telegram chat IDs from getUpdates |

---

## Python Module Integration
```python
# In your existing algo code:
from notification_service import notify_trade_sync, on_trade_event

# Sync (non-async code)
notify_trade_sync(trade_data, "entry")

# Async (FastAPI / asyncio)
await on_trade_event("entry", trade_data)
```

---

## Trade Data Schema
```python
{
    "trade_id": "TRD-001",         # optional, auto-generated
    "symbol": "BTCUSDT",
    "direction": "BUY" | "SELL",
    "event_type": "entry" | "exit" | "sl" | "tp" | "signal",
    "entry_price": 67500.00,
    "exit_price": None,            # optional
    "position_size": 0.05,
    "strategy_name": "Momentum Alpha",
    "confidence_score": 0.82,      # 0-1 or 0-100
    "market_regime": "trend",      # trend|mean_reverting|volatile|sideways
    "timestamp": "2024-01-15 14:32:01 UTC",  # optional
    "pnl_abs": 350.00,             # optional
    "pnl_pct": 2.5,                # optional
    "timeframe": "1h",             # optional
    "rr_ratio": 2.5,               # optional
    "indicators": {"RSI": "62.3", "MACD": "+0.0012"}  # optional
}
```

---

## User Choices
1. Has Telegram Bot Token + Chat ID (provided)
2. Full dashboard with analytics
3. Both REST API + Python module
4. Telegram only (no email)
5. MongoDB persistence

---

## What's Been Implemented
- [2026-04-22] Full backend API with all endpoints
- [2026-04-22] `notification_service.py` standalone module with rate limiting + deduplication + retry
- [2026-04-22] Dark trading terminal dashboard UI
- [2026-04-22] Trade History page with filters
- [2026-04-22] Alert Logs page with expandable messages
- [2026-04-22] Manual Trade Entry form with preview
- [2026-04-22] Analytics page with PnL charts, strategy breakdown, symbol distribution
- [2026-04-22] Chat ID discovery endpoint
- [2026-04-22] Full quant risk suite: Sharpe, Sortino, Calmar, Kelly, Max Drawdown, Profit Factor, Expectancy, W/L streaks
- [2026-04-22] Monte Carlo simulation (500 bootstrap resamples) — percentile equity fan chart + prob of profit
- [2026-04-22] Position Sizing Calculator — Risk-based, Full Kelly, Half-Kelly, Quarter-Kelly with unit sizing
- [2026-04-22] Kelly Criterion per strategy table
- [2026-04-22] Integration page — execution_engine.py template (download + copy), curl examples, full endpoint reference
- [2026-04-22] ExecutionEngine class template with on_signal/on_entry/on_exit/on_stop_loss methods
- [2026-04-22] `format_daily_summary` — full summary: PnL, best/worst trade, strategy breakdown, regime distribution, alert stats
- [2026-04-22] Settings page — bot config, scheduler status, manual trigger, seed data
- [2026-04-22] 36 sample trades seeded across 14 days (NIFTY, BANKNIFTY, BTCUSDT, ETHUSDT, RELIANCE, TCS)
- [2026-04-22] Telegram confirmed working (chat ID 1003383502, @Saikrishna)

---

## Pending / Backlog
- P0: User must send /start to @algo_trading_22042026_bot to activate Telegram alerts
- P1: WebSocket for real-time dashboard updates (currently polling every 30s)
- P1: Email notifications fallback
- P2: Strategy backtesting integration
- P2: Multiple chat IDs / group support
- P2: Alert scheduling (daily P&L summary)
- P3: Dark/light theme toggle
