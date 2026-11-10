# LIVE_CANDLE_SYSTEM_PHASE1.md

## 1. Overview
This module implements a real-time WebSocket-based candle streaming architecture.

## 2. Backend Implementation
- **Router:** `AlgoTradingTelegramBotAndFrontend/backend/routers/candles.py`
- **Utility:** `AlgoTradingTelegramBotAndFrontend/backend/utils/candle_manager.py`

## 3. Frontend Implementation
- **Component:** `AlgoTradingTelegramBotAndFrontend/frontend/src/components/CandleChart.tsx`
- **Hook:** `AlgoTradingTelegramBotAndFrontend/frontend/src/hooks/useLiveCandles.ts`

## 4. Execution Flow
1. Broker WebSocket (AngelOne/Binance) -> `candle_manager.py` (aggregation)
2. `candle_manager.py` -> Broadcast to `/ws/live-candles`
3. React Frontend -> `useLiveCandles` hook -> TradingView LightWeight Charts.
