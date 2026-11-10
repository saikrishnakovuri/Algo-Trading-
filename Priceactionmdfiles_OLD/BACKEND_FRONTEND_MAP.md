# Backend → Frontend Component Mapping

| # | Backend Source | Capability | API Route | Frontend Component | Status |
|---|---|---|---|---|---|
| 1 | server.py | Live Status | GET /api/live/status | Dashboard.jsx | ✅ |
| 2 | server.py | Summary Stats | GET /api/analytics/summary | Dashboard.jsx | ✅ |
| 3 | server.py | PnL Chart | GET /api/analytics/pnl-history | Dashboard.jsx | ✅ |
| 4 | server.py | Live Signals | GET /api/live/signals | Dashboard.jsx | ✅ |
| 5 | server.py | Trade List | GET /api/trades | Trades.jsx | ✅ |
| 6 | server.py | Bot Control | POST /api/control/{type} | NewTrade.jsx | ✅ |
| 7 | server.py | Open Positions | GET /api/live/positions | NewTrade.jsx | ✅ |
| 8 | server.py | Manual Trade | POST /api/control/manual-trade | NewTrade.jsx | ✅ |
| 9 | server.py | Backtest History | GET /api/backtest/history | Backtesting.jsx | ✅ |
| 10 | server.py | Run Backtest | POST /api/backtest/run | Backtesting.jsx | ✅ |
| 11 | server.py | Get Backtest Result| GET /api/backtest/result/{id} | Backtesting.jsx | ✅ |
| 12 | server.py | App Settings | GET/PUT /api/settings | Settings.jsx | ✅ |
| 13 | pa_engine_bridge.py | PA Config | GET/PUT /api/pa/config | PADashboard.js | ✅ |
| 14 | pa_engine_bridge.py | PA Strategies | GET /api/pa/strategies | PADashboard.js | ✅ |
| 15 | pa_engine_bridge.py | PA Edge Monitor | GET /api/pa/edge | PADashboard.js | ✅ |
| 16 | pa_engine_bridge.py | PA Monte Carlo | GET /api/pa/montecarlo | PADashboard.js | ✅ |
| 17 | pa_engine_bridge.py | PA Backtest Files | GET /api/pa/backtest/files | PADashboard.js | ✅ |
| 18 | server.py | Journal Trades | GET /api/journal/trades | TradeJournal.js | ✅ |
| 19 | server.py | Journal Summary | GET /api/journal/summary | TradeJournal.js | ✅ |
| 20 | server.py | Loss Analysis | GET /api/journal/losses/analysis | TradeJournal.js | ✅ |
| 21 | server.py | Export Journal | GET /api/journal/export | TradeJournal.js | ✅ |
| 22 | risk_calculator.py | Position Sizing | POST /api/analytics/position-size | ??? | 🔴 MISSING |
| 23 | live_state.py | Market Context | GET /api/live/context | ??? | 🔴 MISSING |
| 24 | modules/indicator_engine.py | Indicator Data | ??? | ??? | 🔴 MISSING |
| 25 | modules/smc/analysis.py | SMC Analysis | ??? | ??? | 🔴 MISSING |
| 26 | modules/reporting/ | Daily Reports | ??? | ??? | 🔴 MISSING |
| 27 | modules/data_layer.py | Data Status | ??? | ??? | 🔴 MISSING |
| 28 | server.py | Bot Discover Chat | GET /api/bot/discover-chat | ??? | 🔴 MISSING |
| 29 | server.py | Scheduler Status | GET /api/scheduler/status | ??? | 🔴 MISSING |
| 30 | server.py | Trigger Scheduler | POST /api/scheduler/trigger/{type}| ??? | 🔴 MISSING |

**TOTAL CAPABILITIES:** 30
**COVERED:** 21
**MISSING:** 9
