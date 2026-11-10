# AlgoTradingTelegramBotAndFrontend

## Repository Overview

This repository contains a multi-part algo trading assistant project with both backend trade alert infrastructure and a local developer assistant utility.

### Main components

- `backend/` — FastAPI-based TradeAlert bot backend.
- `frontend/` — Create React App frontend scaffold and configuration files.
- `gemini-dev-assistant/` — Local CLI developer assistant integrated with Google Gemini.
- `memory/` — Notes and product documentation.
- `test_reports/` — Stored test output and pytest XML reports.
- `tests/` — Root-level Python test package placeholder.

## Backend (`backend/`)

The backend implements a TradeAlert API for algorithmic trading notifications, analytics, and scheduled reports.

### Key files

- `backend/server.py` — FastAPI application with endpoints for:
  - trade notifications (`/api/trades/notify`)
  - previewing alert messages (`/api/trades/preview`)
  - sample/test alerts (`/api/trades/test`)
  - trade listing and counts (`/api/trades`, `/api/trades/count`)
  - alerts logs (`/api/alerts`)
  - analytics summary and PnL history (`/api/analytics/summary`, `/api/analytics/pnl-history`)
  - risk metrics (`/api/analytics/risk`)
  - Monte Carlo simulation (`/api/analytics/monte-carlo`)
  - position sizing calculator (`/api/analytics/position-size`)
  - scheduler status and manual trigger (`/api/scheduler/status`, `/api/scheduler/trigger/{summary_type}`)
  - sample trade seeding (`/api/seed-trades`)
  - Telegram chat discovery (`/api/bot/discover-chat`)
  - Gemini code analysis integration (`/api/analyze`)

- `backend/notification_service.py` — Telegram message formatting, deduplication, rate limiting, and send logic.
- `backend/risk_calculator.py` — Trading analytics helpers including equity curve, drawdown, Sharpe, Sortino, Calmar, Kelly, Monte Carlo, profit factor, expectancy, and streaks.
- `backend/requirements.txt` — Python dependencies for FastAPI, MongoDB, Telegram integration, Gemini, and testing.
- `backend/tests/` — Pytest tests validating TradeAlert endpoints, analytics, risk metrics, Monte Carlo output, and position-sizing functionality.

### Backend features

- Trade event ingestion with optional Telegram alert send.
- MongoDB persistence for trades, alerts, and summary logs.
- Analytics endpoints for risk and performance data.
- Daily summary scheduler with open/close session reporting.
- Sample data seeding for development and demo.
- Gemini-based code analysis endpoint for `fix`, `optimize`, `explain`, and `refactor` commands.

## Frontend (`frontend/`)

The frontend contains a Create React App scaffold with configuration files for custom builds.

### Files included

- `frontend/README.md` — generic CRA usage instructions.
- `frontend/craco.config.js` — CRACO configuration.
- `frontend/jsconfig.json` — JS config for module resolution.
- `frontend/components.json` — likely UI component metadata.
- `frontend/.env` — environment settings for frontend deployment.

> Note: `frontend/` does not include a `package.json` in the current workspace listing, so the frontend may require restoring project metadata before install.

## Gemini Dev Assistant (`gemini-dev-assistant/`)

This directory contains a local CLI-based developer assistant built around Google Gemini.

### Key files

- `gemini-dev-assistant/index.js` — main interactive CLI entrypoint.
- `gemini-dev-assistant/gemini.js` — Gemini API integration and prompt handling.
- `gemini-dev-assistant/fileReader.js` — file I/O, backup, and supported file detection.
- `gemini-dev-assistant/utils.js` — validation, formatting, and command utilities.
- `gemini-dev-assistant/package.json` — Node package metadata.
- `gemini-dev-assistant/.env.example` — example environment config.
- `gemini-dev-assistant/vscode-extension/` — extension support files for VS Code.

### Assistant capabilities

- Fix, optimize, explain, and refactor code using Gemini.
- Interactive prompts for command selection and file choice.
- Automatic backup creation before saving modifications.
- Support for many programming languages and file types.

## Additional files

- `design_guidelines.json` — design requirements or style guidance.
- `gitignore.txt` — repository ignore patterns.
- `test_result.md` — recorded test outcomes.
- `test_reports/` — saved JSON and pytest XML test results.

## Getting started

### Backend

1. Create a `.env` file in `backend/` with required vars:
   - `MONGO_URL`
   - `DB_NAME`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `GEMINI_API_KEY`
   - Optional: `CORS_ORIGINS`

2. Install dependencies:
   - `pip install -r backend/requirements.txt`

3. Run the API:
   - `uvicorn backend.server:app --reload --host 0.0.0.0 --port 8000`

### Gemini Dev Assistant

1. Install dependencies:
   - `cd gemini-dev-assistant`
   - `npm install`

2. Configure `.env` from `.env.example`.
3. Start the assistant:
   - `npm start`

### Frontend

- The frontend is based on Create React App.
- No `package.json` is present here, so restore or recreate frontend dependencies before running.

## Notes

- The backend uses MongoDB and Telegram for live alerting.
- The Gemini assistant is a standalone developer tool separate from the trading backend.
- Backend tests use `REACT_APP_BACKEND_URL` to target the running API.

