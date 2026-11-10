# Test Credentials

## Application
- URL: https://algo-telegram-trade.preview.emergentagent.com
- No authentication required (public app)

## Telegram Bot
- Bot Username: @algo_trading_22042026_bot
- Bot Token: 8588455217:AAE7beZ-5rfz4ypWpy_HHc9w3yacKgaUs_A
- Chat ID (configured): 1003383502
- NOTE: User must send /start to @algo_trading_22042026_bot to activate alerts

## MongoDB
- URL: mongodb://localhost:27017
- Database: tradealert_db
- Collections: trades, alerts

## Python Module Usage
```python
from notification_service import notify_trade_sync
notify_trade_sync({
    "trade_id": "TRD-001",
    "symbol": "BTCUSDT",
    "direction": "BUY",
    "entry_price": 67500.00,
    "position_size": 0.05,
    "strategy_name": "Momentum Alpha",
    "confidence_score": 0.82,
    "market_regime": "trend",
}, "entry")
```
