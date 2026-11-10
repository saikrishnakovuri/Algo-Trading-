
Action: file_editor create /app/BINANCE_CRYPTO_ADAPTER_SPEC.md --file-text "# ₿ BINANCE CRYPTO ADAPTER SPEC

> 24/7 crypto data feed for after-hours testing of your existing strategy engine.
>
> **What you'll use it for:** Test the entire bot pipeline (signal generation, execution simulation, RiskGuard, exits, Telegram alerts) at 22:00 IST tonight without waiting for NSE open.

---

## 1. WHAT YOU NEED FROM BINANCE (no money, no KYC for read-only)

### Step-by-step API key creation (5 minutes)

1. Go to https://www.binance.com/en/my/settings/api-management
2. Sign in (or create free account)
3. Click \"Create API\"
4. Choose \"System Generated\"
5. Label it: `algobot_readonly_test`
6. Pass 2FA
7. ⚠️ **CRITICAL — UNCHECK these permissions:**
   - ❌ Enable Spot & Margin Trading
   - ❌ Enable Margin Loan, Repay & Transfer
   - ❌ Enable Withdrawals
8. ✅ **CHECK these permissions:**
   - ✅ Enable Reading
9. **IP restriction:** for safety, restrict to your Windows machine's public IP (Google \"what is my ip\")
10. Save the API Key + Secret. You'll need them in `.env`:

```bash
# Add to your .env file:
BINANCE_API_KEY=\"<your_key>\"
BINANCE_SECRET=\"<your_secret>\"
```

**Note:** For pure market data (klines, ticker), Binance does not even require an API key for many public endpoints. You'd only need keys if you want authenticated rate-limit increases or want to read your account balance (not needed for our use case). **If you want to skip API key setup entirely, the adapter works fine with public endpoints.**

---

## 2. THE ADAPTER — `modules/data_adapters/binance_adapter.py`

```python
\"\"\"
modules/data_adapters/binance_adapter.py
\"\"\"
import os
import time
import threading
import logging
from datetime import datetime, time as dtime, timezone
from typing import Callable, Optional
import requests
import pandas as pd

from .base_adapter import (
    DataAdapter, InstrumentInfo, MarketHoursConfig, AdapterError
)

logger = logging.getLogger(\"BinanceAdapter\")


class BinanceAdapter(DataAdapter):
    \"\"\"
    Binance Spot market data adapter.
    Strategy still requests 'NIFTY' / 'BANKNIFTY' — we translate to BTC/ETH.
    \"\"\"

    name = \"binance\"

    REST_BASE = \"https://api.binance.com/api/v3\"
    WS_BASE   = \"wss://stream.binance.com:9443/ws\"

    # Binance interval mapping (matches their API exactly)
    TF_MAP = {
        \"1m\": \"1m\", \"3m\": \"3m\", \"5m\": \"5m\", \"15m\": \"15m\",
        \"30m\": \"30m\", \"1h\": \"1h\", \"4h\": \"4h\", \"1d\": \"1d\",
    }

    def __init__(self, cfg: dict):
        self.cfg = cfg or {}
        self.symbol_mapping = self.cfg.get(\"symbol_mapping\", {
            \"NIFTY\": \"BTCUSDT\",
            \"BANKNIFTY\": \"ETHUSDT\",
        })
        # Reverse mapping for live price lookups
        self._reverse_map = {v: k for k, v in self.symbol_mapping.items()}

        self.api_key = os.getenv(\"BINANCE_API_KEY\", \"\").strip()
        self.session = requests.Session()
        if self.api_key:
            self.session.headers[\"X-MBX-APIKEY\"] = self.api_key

        self._last_tick_at: dict[str, float] = {}
        self._tick_subscribers: dict[str, list[Callable]] = {}
        self._ws_thread: Optional[threading.Thread] = None

        # Sanity ping
        self._ping()

    def _ping(self):
        try:
            r = self.session.get(f\"{self.REST_BASE}/ping\", timeout=5)
            r.raise_for_status()
            logger.info(f\"[Binance] REST ping OK ({r.elapsed.total_seconds()*1000:.0f}ms)\")
        except Exception as e:
            raise AdapterError(f\"Binance REST unreachable: {e}\")

    # ── Symbol translation ──────────────────────────────

    def _to_native(self, symbol: str) -> str:
        \"\"\"Strategy-side symbol → Binance-side symbol.\"\"\"
        return self.symbol_mapping.get(symbol.upper(), symbol.upper())

    # ── get_bars ────────────────────────────────────────

    def get_bars(self, symbol: str, timeframe: str = \"5m\", count: int = 200) -> pd.DataFrame:
        native = self._to_native(symbol)
        tf = self.TF_MAP.get(timeframe)
        if tf is None:
            raise AdapterError(f\"Unsupported timeframe: {timeframe}. Supported: {list(self.TF_MAP)}\")

        # Binance max 1000 per call — chunk if needed
        all_klines = []
        remaining = min(count, 1000)
        url = f\"{self.REST_BASE}/klines\"
        params = {\"symbol\": native, \"interval\": tf, \"limit\": remaining}

        try:
            r = self.session.get(url, params=params, timeout=10)
            r.raise_for_status()
            all_klines = r.json()
        except requests.RequestException as e:
            raise AdapterError(f\"Binance get_bars failed: {e}\")

        if not all_klines:
            raise AdapterError(f\"Binance returned no data for {native} {tf}\")

        # Klines format: [open_time, open, high, low, close, volume, close_time, ...]
        df = pd.DataFrame(all_klines, columns=[
            \"open_time\", \"open\", \"high\", \"low\", \"close\", \"volume\",
            \"close_time\", \"quote_volume\", \"trades\", \"taker_buy_base\",
            \"taker_buy_quote\", \"ignore\"
        ])
        df[\"timestamp\"] = pd.to_datetime(df[\"open_time\"], unit=\"ms\", utc=True)
        df.set_index(\"timestamp\", inplace=True)
        df = df[[\"open\", \"high\", \"low\", \"close\", \"volume\"]].astype(float)
        df.index = df.index.tz_convert(\"Asia/Kolkata\")  # align with NSE timezone for strategy
        return df

    # ── get_live_price ──────────────────────────────────

    def get_live_price(self, symbol: str) -> float:
        native = self._to_native(symbol)
        try:
            r = self.session.get(
                f\"{self.REST_BASE}/ticker/price\",
                params={\"symbol\": native}, timeout=5
            )
            r.raise_for_status()
            return float(r.json()[\"price\"])
        except Exception as e:
            raise AdapterError(f\"Binance get_live_price failed: {e}\")

    # ── get_instrument_info ────────────────────────────

    def get_instrument_info(self, symbol: str) -> InstrumentInfo:
        native = self._to_native(symbol)
        try:
            r = self.session.get(
                f\"{self.REST_BASE}/exchangeInfo\",
                params={\"symbol\": native}, timeout=5
            )
            r.raise_for_status()
            symbols = r.json().get(\"symbols\", [])
            if not symbols:
                raise AdapterError(f\"Binance: symbol {native} not found\")
            s = symbols[0]
            filters = {f[\"filterType\"]: f for f in s[\"filters\"]}
            tick = float(filters.get(\"PRICE_FILTER\", {}).get(\"tickSize\", 0.01))
            return InstrumentInfo(
                symbol=symbol.upper(),
                native_symbol=native,
                asset_class=\"CRYPTO\",
                tick_size=tick,
                lot_size=1,  # crypto trades fractional, lot=1
                quote_currency=s[\"quoteAsset\"],
                is_24x7=True,
            )
        except Exception as e:
            raise AdapterError(f\"Binance get_instrument_info failed: {e}\")

    # ── get_market_hours ───────────────────────────────

    def get_market_hours(self) -> MarketHoursConfig:
        \"\"\"Crypto is 24/7. Apply NSE-like time gates for testing parity.\"\"\"
        return MarketHoursConfig(
            market_open=dtime(0, 0),
            market_close=dtime(23, 59, 59),
            signal_gate=dtime(10, 0),    # IST 10:00 — match NSE for parity testing
            no_entry_after=dtime(12, 0), # IST 12:00 — match NSE
            force_close_at=dtime(15, 15),
            timezone=\"Asia/Kolkata\",
            is_24x7=True,
            trading_days=[\"Mon\",\"Tue\",\"Wed\",\"Thu\",\"Fri\",\"Sat\",\"Sun\"],
        )

    # ── subscribe_ticks (optional, for live tick streaming) ──

    def subscribe_ticks(self, symbol: str, callback: Callable) -> None:
        \"\"\"Subscribe to 1-second kline updates via WebSocket.\"\"\"
        native = self._to_native(symbol).lower()
        stream = f\"{native}@kline_1m\"
        self._tick_subscribers.setdefault(stream, []).append(callback)

        if self._ws_thread is None or not self._ws_thread.is_alive():
            self._ws_thread = threading.Thread(target=self._ws_loop, daemon=True)
            self._ws_thread.start()

    def _ws_loop(self):
        \"\"\"Background WS connection. Reconnects on drop.\"\"\"
        try:
            import websocket
        except ImportError:
            logger.warning(\"[Binance] websocket-client not installed; tick stream disabled. pip install websocket-client\")
            return

        streams = list(self._tick_subscribers.keys())
        if not streams:
            return
        url = f\"{self.WS_BASE}/{'/'.join(streams)}\"

        def _on_msg(ws, msg):
            import json
            d = json.loads(msg)
            kline = d.get(\"k\", d)
            if not kline:
                return
            price = float(kline.get(\"c\", 0))
            ts = kline.get(\"T\", int(time.time() * 1000)) / 1000
            stream = d.get(\"s\", \"\").lower() + \"@kline_1m\"
            self._last_tick_at[stream] = time.time()
            for cb in self._tick_subscribers.get(stream, []):
                try:
                    cb(price, datetime.fromtimestamp(ts, tz=timezone.utc))
                except Exception as e:
                    logger.error(f\"[Binance] tick callback failed: {e}\")

        ws = websocket.WebSocketApp(url, on_message=_on_msg)
        while True:
            try:
                ws.run_forever(ping_interval=20)
                time.sleep(2)  # brief pause before reconnect
            except Exception as e:
                logger.error(f\"[Binance] WS error, reconnecting: {e}\")
                time.sleep(5)

    # ── health_check ───────────────────────────────────

    def health_check(self) -> dict:
        try:
            t0 = time.time()
            r = self.session.get(f\"{self.REST_BASE}/ping\", timeout=3)
            r.raise_for_status()
            latency_ms = (time.time() - t0) * 1000
            last_tick = max(self._last_tick_at.values()) if self._last_tick_at else None
            tick_age = (time.time() - last_tick) if last_tick else None
            return {
                \"status\": \"OK\",
                \"details\": f\"REST ping {latency_ms:.0f}ms\",
                \"last_tick_age_sec\": tick_age,
            }
        except Exception as e:
            return {\"status\": \"DOWN\", \"details\": str(e), \"last_tick_age_sec\": None}
```

---

## 3. CONFIG — entry in `config/data_source.yaml`

```yaml
active_adapter: \"binance\"

binance:
  symbol_mapping:
    NIFTY: \"BTCUSDT\"
    BANKNIFTY: \"ETHUSDT\"
  rest_base: \"https://api.binance.com/api/v3\"
  ws_base: \"wss://stream.binance.com:9443/ws\"
  # API key is optional — read from environment variable BINANCE_API_KEY
  # If empty, public endpoints are used (no auth)
```

---

## 4. SELF-TEST CHECKLIST

After Gemini writes `binance_adapter.py`, run:

```bash
# 1. Install dependency
pip install websocket-client requests

# 2. Test the adapter
python scripts/test_adapter.py binance BTCUSDT 5m 100
```

Expected:
- 100 OHLCV bars from the last ~8 hours
- Latest BTC price displayed
- Instrument info shows asset_class=CRYPTO, lot_size=1
- Market hours: 24/7=True
- Health: OK

```bash
# 3. Test that strategy-side \"NIFTY\" maps to BTCUSDT
python -c \"
from modules.data_adapters import get_active_adapter
a = get_active_adapter()
df = a.get_bars('NIFTY', '5m', 10)
print(df.tail(3))
print('Price:', a.get_live_price('NIFTY'))
\"
```

Expected: same BTC data, but called with \"NIFTY\" — symbol translation working.

---

## 5. RATE LIMITS (free tier)

| Endpoint | Limit |
|---|---|
| Public REST (/klines, /ticker, /ping) | 1200 requests/minute |
| WebSocket | Unlimited connections |
| Account endpoints (need API key) | 1200 weight/minute |

**Our usage:** 1 kline call per 5-min cycle = 12 calls/hour = 288 calls/day. **Far below any limit.**

---

## 6. KNOWN GOTCHAS

1. **Timezone:** Binance returns UTC. We convert to Asia/Kolkata in the adapter to match NSE strategy timing. Bars at \"10:00 IST\" map to \"04:30 UTC\" — fine for strategy logic since it sees `10:00` in the index.

2. **Volume units:** Binance volume is in BASE asset (BTC), not quote (USDT). Strategy doesn't care about units, only ratios. Volume filters (1.5× avg) work identically.

3. **Weekend gaps:** Crypto trades 24/7 — there are no weekend gaps. This is actually better for strategy testing than forex.

4. **Bar close timing:** Binance kline closes at `:00, :05, :10, ...` UTC. After conversion to IST, this lands on weird minute marks like `:30, :35, :40, ...`. Strategy doesn't care — it reads whatever bars come.

5. **Symbol case:** Binance is case-sensitive — use `BTCUSDT` not `btcusdt`. Adapter handles uppercase internally.

---

## 7. EXTENSIONS (not required for v1, document for later)

- **Futures vs Spot:** This adapter uses Spot. For perpetual futures with funding rates, use `https://fapi.binance.com/fapi/v1/...`. Different volume profile, more leveraged liquidations to chase.
- **Multiple symbols:** Add ADAUSDT, SOLUSDT to symbol_mapping for portfolio testing.
- **Order book depth:** Can pull L2 book for slippage modeling. Not needed for v1.

---

**END OF BINANCE SPEC. Continue to FOREX_API_FREE_SETUP_GUIDE.md.**
"
Observation: Create successful: /app/BINANCE_CRYPTO_ADAPTER_SPEC.md