
Action: file_editor create /app/ALPHAVANTAGE_FOREX_ADAPTER_SPEC.md --file-text "# 💱 ALPHA VANTAGE FOREX ADAPTER SPEC

> Forex data adapter for paper-trading the strategy on EUR/USD, GBP/USD, USD/JPY during forex hours (24/5).

---

## 1. THE ADAPTER — `modules/data_adapters/alphavantage_adapter.py`

```python
\"\"\"
modules/data_adapters/alphavantage_adapter.py
\"\"\"
import os
import time
import logging
from datetime import datetime, time as dtime, timedelta
from threading import Thread, Event
from typing import Callable, Optional
import requests
import pandas as pd

from .base_adapter import (
    DataAdapter, InstrumentInfo, MarketHoursConfig, AdapterError
)

logger = logging.getLogger(\"AlphaVantageAdapter\")


class AlphaVantageAdapter(DataAdapter):
    \"\"\"
    Alpha Vantage REST adapter for forex data.
    Free tier: 5 calls/min, 500 calls/day. Polls every 60s by default.
    Strategy requests \"NIFTY\" → adapter translates to \"EUR/USD\".
    \"\"\"

    name = \"alphavantage\"

    REST_BASE = \"https://www.alphavantage.co/query\"

    # Alpha Vantage forex intraday intervals (their naming)
    TF_MAP = {
        \"1m\":  \"1min\",
        \"5m\":  \"5min\",
        \"15m\": \"15min\",
        \"30m\": \"30min\",
        \"1h\":  \"60min\",
    }

    def __init__(self, cfg: dict):
        self.cfg = cfg or {}
        self.symbol_mapping = self.cfg.get(\"symbol_mapping\", {
            \"NIFTY\": \"EUR/USD\",
            \"BANKNIFTY\": \"GBP/USD\",
        })
        self.poll_interval_sec = int(self.cfg.get(\"poll_interval_sec\", 60))

        # API key from env or config
        self.api_key = os.getenv(\"ALPHAVANTAGE_API_KEY\", \"\").strip()
        if not self.api_key:
            self.api_key = self.cfg.get(\"api_key\", \"\").strip()
        if not self.api_key or self.api_key.startswith(\"ENV:\"):
            raise AdapterError(
                \"ALPHAVANTAGE_API_KEY not set. Get free key at \"
                \"https://www.alphavantage.co/support/#api-key and add to .env\"
            )

        self.session = requests.Session()

        # Rate limit tracking (free tier: 5 calls/min, 500/day)
        self._call_times: list[float] = []
        self._daily_count = 0
        self._daily_reset_at = time.time() + 86400

        # Cache (since polling)
        self._bar_cache: dict[str, tuple[pd.DataFrame, float]] = {}
        self._price_cache: dict[str, tuple[float, float]] = {}
        self.cache_ttl_sec = 60

        # Tick subscribers (simulated via polling)
        self._tick_subscribers: dict[str, list[Callable]] = {}
        self._poll_stop = Event()

        # Sanity check
        self._test_key()

    def _test_key(self):
        try:
            r = self._call({
                \"function\": \"CURRENCY_EXCHANGE_RATE\",
                \"from_currency\": \"EUR\",
                \"to_currency\": \"USD\",
            })
            if \"Realtime Currency Exchange Rate\" not in r:
                raise AdapterError(f\"Alpha Vantage rejected key. Response: {r}\")
            logger.info(\"[AlphaVantage] API key validated OK\")
        except Exception as e:
            raise AdapterError(f\"Alpha Vantage init failed: {e}\")

    # ── Rate-limited call ─────────────────────────────

    def _call(self, params: dict) -> dict:
        # Daily reset
        if time.time() > self._daily_reset_at:
            self._daily_count = 0
            self._daily_reset_at = time.time() + 86400

        if self._daily_count >= 500:
            raise AdapterError(\"Alpha Vantage daily limit (500) reached. Resets in 24h.\")

        # Per-minute rate limit: max 5 in 60s
        now = time.time()
        self._call_times = [t for t in self._call_times if now - t < 60]
        if len(self._call_times) >= 5:
            wait = 60 - (now - self._call_times[0]) + 1
            logger.warning(f\"[AlphaVantage] rate limit pause {wait:.1f}s\")
            time.sleep(wait)

        params[\"apikey\"] = self.api_key
        r = self.session.get(self.REST_BASE, params=params, timeout=15)
        r.raise_for_status()
        j = r.json()

        # Alpha Vantage error wrappers
        if \"Error Message\" in j:
            raise AdapterError(f\"Alpha Vantage error: {j['Error Message']}\")
        if \"Note\" in j:
            raise AdapterError(f\"Alpha Vantage throttled: {j['Note']}\")

        self._call_times.append(time.time())
        self._daily_count += 1
        return j

    # ── Symbol translation ────────────────────────────

    def _to_native(self, symbol: str) -> tuple[str, str]:
        \"\"\"Returns (from_currency, to_currency).\"\"\"
        pair = self.symbol_mapping.get(symbol.upper(), symbol.upper())
        if \"/\" not in pair:
            raise AdapterError(f\"Invalid forex pair format: {pair}. Expected 'EUR/USD'.\")
        return pair.split(\"/\")

    # ── get_bars ──────────────────────────────────────

    def get_bars(self, symbol: str, timeframe: str = \"5m\", count: int = 200) -> pd.DataFrame:
        cache_key = f\"{symbol}_{timeframe}\"
        cached = self._bar_cache.get(cache_key)
        if cached and time.time() - cached[1] < self.cache_ttl_sec:
            return cached[0].tail(count)

        from_c, to_c = self._to_native(symbol)
        tf = self.TF_MAP.get(timeframe)
        if tf is None:
            raise AdapterError(f\"Unsupported timeframe: {timeframe}. Supported: {list(self.TF_MAP)}\")

        params = {
            \"function\": \"FX_INTRADAY\",
            \"from_symbol\": from_c,
            \"to_symbol\": to_c,
            \"interval\": tf,
            \"outputsize\": \"compact\",  # last 100 bars
        }
        if count > 100:
            params[\"outputsize\"] = \"full\"  # up to ~3000 bars but slower

        try:
            j = self._call(params)
        except AdapterError:
            raise

        # Find the time series key (varies by interval)
        series_key = next(
            (k for k in j.keys() if k.startswith(\"Time Series FX\")), None
        )
        if not series_key:
            raise AdapterError(f\"Alpha Vantage response missing FX time series: {list(j.keys())}\")

        rows = []
        for ts_str, bar in j[series_key].items():
            rows.append({
                \"timestamp\": pd.to_datetime(ts_str),
                \"open\": float(bar[\"1. open\"]),
                \"high\": float(bar[\"2. high\"]),
                \"low\":  float(bar[\"3. low\"]),
                \"close\": float(bar[\"4. close\"]),
                \"volume\": 0.0,  # forex has no centralized volume
            })

        df = pd.DataFrame(rows).sort_values(\"timestamp\").set_index(\"timestamp\")
        df.index = df.index.tz_localize(\"US/Eastern\").tz_convert(\"Asia/Kolkata\")
        df = df.tail(count)

        self._bar_cache[cache_key] = (df, time.time())
        return df

    # ── get_live_price ────────────────────────────────

    def get_live_price(self, symbol: str) -> float:
        cached = self._price_cache.get(symbol)
        if cached and time.time() - cached[1] < 30:  # 30s cache
            return cached[0]

        from_c, to_c = self._to_native(symbol)
        try:
            j = self._call({
                \"function\": \"CURRENCY_EXCHANGE_RATE\",
                \"from_currency\": from_c,
                \"to_currency\": to_c,
            })
            rate = float(j[\"Realtime Currency Exchange Rate\"][\"5. Exchange Rate\"])
            self._price_cache[symbol] = (rate, time.time())
            return rate
        except Exception as e:
            raise AdapterError(f\"Alpha Vantage get_live_price failed: {e}\")

    # ── get_instrument_info ──────────────────────────

    def get_instrument_info(self, symbol: str) -> InstrumentInfo:
        from_c, to_c = self._to_native(symbol)
        # Forex pip = 0.0001 for most majors, 0.01 for JPY pairs
        tick = 0.01 if \"JPY\" in (from_c, to_c) else 0.0001
        return InstrumentInfo(
            symbol=symbol.upper(),
            native_symbol=f\"{from_c}/{to_c}\",
            asset_class=\"FOREX\",
            tick_size=tick,
            lot_size=100_000,  # standard forex lot (but strategy uses lots=1)
            quote_currency=to_c,
            is_24x7=False,  # forex closed weekends
        )

    # ── get_market_hours ─────────────────────────────

    def get_market_hours(self) -> MarketHoursConfig:
        \"\"\"
        Forex: Sunday 17:00 ET (Mon 03:30 IST) - Friday 17:00 ET (Sat 03:30 IST).
        For strategy parity with NSE, apply 10:00–12:00 IST signal window.
        \"\"\"
        return MarketHoursConfig(
            market_open=dtime(0, 0),
            market_close=dtime(23, 59, 59),
            signal_gate=dtime(10, 0),
            no_entry_after=dtime(12, 0),
            force_close_at=dtime(15, 15),
            timezone=\"Asia/Kolkata\",
            is_24x7=False,
            trading_days=[\"Mon\", \"Tue\", \"Wed\", \"Thu\", \"Fri\"],
        )

    # ── subscribe_ticks (simulated via polling) ──────

    def subscribe_ticks(self, symbol: str, callback: Callable) -> None:
        self._tick_subscribers.setdefault(symbol, []).append(callback)
        # Start poll thread if not running
        if not hasattr(self, \"_poll_thread\") or not self._poll_thread.is_alive():
            self._poll_thread = Thread(target=self._poll_loop, daemon=True)
            self._poll_thread.start()

    def _poll_loop(self):
        while not self._poll_stop.is_set():
            for sym, subs in list(self._tick_subscribers.items()):
                try:
                    px = self.get_live_price(sym)
                    now = datetime.now()
                    for cb in subs:
                        try:
                            cb(px, now)
                        except Exception as e:
                            logger.error(f\"[AlphaVantage] tick callback failed: {e}\")
                except Exception as e:
                    logger.warning(f\"[AlphaVantage] poll for {sym} failed: {e}\")
            self._poll_stop.wait(self.poll_interval_sec)

    # ── health_check ─────────────────────────────────

    def health_check(self) -> dict:
        rate_remaining = max(0, 500 - self._daily_count)
        status = \"OK\" if rate_remaining > 50 else \"DEGRADED\"
        return {
            \"status\": status,
            \"details\": f\"calls_today={self._daily_count}/500, calls_in_last_min={len(self._call_times)}/5\",
            \"last_tick_age_sec\": None,
        }
```

---

## 2. CONFIG — entry in `config/data_source.yaml`

```yaml
active_adapter: \"alphavantage\"

alphavantage:
  symbol_mapping:
    NIFTY: \"EUR/USD\"
    BANKNIFTY: \"GBP/USD\"
  poll_interval_sec: 60
  rest_base: \"https://www.alphavantage.co/query\"
  # API key read from env: ALPHAVANTAGE_API_KEY
```

---

## 3. .env entry (operator does this manually)

```bash
# Add to .env (NOT data_source.yaml — keep keys out of YAML)
ALPHAVANTAGE_API_KEY=\"your_actual_key_here\"
```

---

## 4. SELF-TEST

```bash
# After Gemini writes alphavantage_adapter.py and operator adds the env key:
python scripts/test_adapter.py alphavantage EUR/USD 5m 100
```

Expected:
- ~100 bars of EUR/USD 5-min data (may be fewer if outside forex hours)
- Latest EUR/USD rate (~1.08 typically)
- Instrument info: asset_class=FOREX, tick_size=0.0001
- Market hours: trading_days = Mon-Fri
- Health: OK with calls_today < 50

```bash
# Strategy-side symbol test
python -c \"
from modules.data_adapters import get_active_adapter
a = get_active_adapter(force_reload=True)
df = a.get_bars('NIFTY', '5m', 50)
print(df.tail(3))
print('Pair price:', a.get_live_price('NIFTY'))
\"
```

---

## 5. RATE-LIMIT MANAGEMENT (built into adapter)

The adapter respects both:
- **Per-minute:** ≤5 calls in any 60-second window (sleeps if needed)
- **Per-day:** ≤500 calls in any 24-hour window (raises AdapterError when exhausted)

If `health_check()` returns `DEGRADED`, you're close to the daily limit. Reduce poll frequency or switch adapter.

---

## 6. WHEN TO USE FOREX vs CRYPTO FOR TESTING

| Scenario | Use Binance (crypto) | Use AlphaVantage (forex) |
|---|---|---|
| Friday 11 PM IST | ✅ | ✅ (until Sat 03:30) |
| Saturday all day | ✅ | ❌ closed |
| Sunday all day | ✅ | ❌ closed |
| Weekday 10 PM IST | ✅ | ✅ |
| Bandwidth-constrained | ❌ (WS = ~200KB/min) | ✅ (poll = 1KB/min) |
| Closer to NSE behavior | ❌ (crypto more volatile) | ✅ (calmer, similar to indices) |
| Need most signals to validate | ✅ (more volatility = more signals) | ❌ (slow regime detection) |

**Recommendation:** Use **Binance first** for bot mechanics testing tonight. Switch to **AlphaVantage** later in the week for behavior validation closer to NSE patterns.

---

## 7. KNOWN GOTCHAS

1. **No volume data:** Forex is decentralized; spot forex has no volume. The adapter returns `volume=0.0` for all bars. If your strategy uses volume confirmation (e.g., 1.5× avg filter), that filter will reject every trade. **Either disable volume filter when on AlphaVantage, or set volume_multiplier=0 in config.**

2. **Bar timestamps are US/Eastern:** Alpha Vantage uses ET internally. Adapter converts to IST automatically.

3. **Free tier delay:** Live price may be 1-5 minutes delayed. For 5-min strategy bars, this is negligible.

4. **Forex weekend:** Friday 23:30 IST → Monday 03:30 IST is closed. `get_bars()` will return the last available data — stale but valid. Strategy should detect via `get_market_hours().trading_days` check.

5. **JPY pairs have different tick size:** Tick = 0.01 for `*/JPY` pairs instead of 0.0001. Adapter handles this in `get_instrument_info`.

---

**END OF ALPHA VANTAGE SPEC. Continue to INSTRUMENT_NORMALIZATION_SPEC.md.**
"
Observation: Create successful: /app/ALPHAVANTAGE_FOREX_ADAPTER_SPEC.md