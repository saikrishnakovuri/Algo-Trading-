# Frontend Button & Interactive Element Audit Report

## Summary
The audit was performed on the React frontend source code and cross-referenced with the FastAPI backend.
Overall, the code structure is solid, but there is a major connectivity issue ("Network Error") preventing any interaction from working.

## Status Overview
- **WORKING (✅):** 0 (Cannot verify due to server down)
- **BROKEN (🔴):** ALL (Network Error)
- **MISMATCH (⚠️):** Heuristic mismatches in PADashboard

## Detailed Catalog

| # | Page/Component | Element | Handler | API Endpoint | Status | Notes |
|---|---|---|---|---|---|---|
| 1 | Dashboard | Summary Stats | useApi | `/api/analytics/summary` | 🔴 | Network Error |
| 2 | Dashboard | PnL Chart | useApi | `/api/analytics/pnl-history` | 🔴 | Network Error |
| 3 | Dashboard | Live Signals | useApi | `/api/live/signals` | 🔴 | Network Error |
| 4 | Trades | Export Button | `handleExport` | None | 🔴 | Network Error |
| 5 | New Trade | Resume Bot | `handleControl` | `/api/control/resume-bot` | 🔴 | Network Error |
| 6 | New Trade | Pause Bot | `handleControl` | `/api/control/pause-bot` | 🔴 | Network Error |
| 7 | New Trade | Close All | `handleControl` | `/api/control/close-all` | 🔴 | Network Error |
| 8 | New Trade | Place Trade | `handlePlaceTrade` | `/api/control/manual-trade` | 🔴 | Network Error |
| 9 | Backtesting | Run Backtest | `handleRun` | `/api/backtest/run` | 🔴 | **Network Error (Reported by User)** |
| 10 | Settings | Save Changes | `handleSave` | `/api/settings` | 🔴 | Network Error |
| 11 | PA Engine | Toggle Strategy | `toggle` | `/api/pa/strategies/{name}/toggle` | 🔴 | Network Error |
| 12 | PA Engine | Save Config | `handleSave` | `/api/pa/config` | 🔴 | Network Error |

## Root Cause Analysis
The "Network Error" is caused by the backend server not being active on port 8000. 
The user's attempt to start the server failed:
`uvicorn server:app --reload --port` (Missing argument 8000 on the same line).

## Next Steps
1. Start backend with `uvicorn server:app --reload --port 8000`
2. Start frontend with `npm start`
3. Re-test all buttons.
