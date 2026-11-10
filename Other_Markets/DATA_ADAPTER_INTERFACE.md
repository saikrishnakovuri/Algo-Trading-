
Action: file_editor create /app/DATA_ADAPTER_INTERFACE.md --file-text "# 🔌 DATA ADAPTER INTERFACE SPEC

> Defines the abstract base class every market-specific adapter must implement.
> This is the contract. Implementations are interchangeable.

---

## 1. THE INTERFACE — `modules/data_adapters/base_adapter.py`

```python
\"\"\"
modules/data_adapters/base_adapter.py
\"\"\"
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, time
from typing import Callable, Optional
import pandas as pd


@dataclass
class InstrumentInfo:
    \"\"\"Metadata for a tradable instrument.\"\"\"
    symbol: str                  # canonical strategy-side symbol (e.g., \"NIFTY\")
    native_symbol: str           # adapter-side symbol (e.g., \"BTCUSDT\" or \"EUR/USD\")
    asset_class: str             # \"INDEX\" | \"CRYPTO\" | \"FOREX\" | \"OPTION\" | \"EQUITY\"
    tick_size: float             # minimum price increment
    lot_size: int                # contract size (1 for crypto/forex, 65 for NIFTY)
    quote_currency: str          # \"INR\" | \"USD\" | \"USDT\"
    is_24x7: bool                # crypto=True, forex=False, NSE=False


@dataclass
class MarketHoursConfig:
    \"\"\"Trading hours for an asset class.\"\"\"
    market_open: time            # e.g., 09:15 for NSE
    market_close: time           # e.g., 15:30 for NSE
    signal_gate: time            # earliest entry time (e.g., 10:00)
    no_entry_after: time         # latest entry time (e.g., 12:00)
    force_close_at: time         # auto-exit time (e.g., 15:15)
    timezone: str                # \"Asia/Kolkata\" | \"UTC\" | \"America/New_York\"
    is_24x7: bool                # crypto markets
    trading_days: list           # e.g., [\"Mon\",\"Tue\",\"Wed\",\"Thu\",\"Fri\"]


class DataAdapter(ABC):
    \"\"\"
    Abstract base class for market data adapters.
    Strategy engines only interact with this interface.
    Concrete implementations: AngelOneAdapter, BinanceAdapter,
    AlphaVantageAdapter, MemoryAdapter.
    \"\"\"

    name: str = \"base\"                 # override in subclass

    # ── REQUIRED METHODS ──────────────────────────────────────

    @abstractmethod
    def get_bars(
        self,
        symbol: str,
        timeframe: str = \"5m\",
        count: int = 200
    ) -> pd.DataFrame:
        \"\"\"
        Return the last `count` OHLCV bars for `symbol`.

        Returns:
            DataFrame with columns: open, high, low, close, volume
            Index: DatetimeIndex (timezone-aware in adapter's local tz)
            Length: exactly `count` rows (or all available if fewer exist)

        Raises:
            AdapterError if symbol unknown or data unavailable.
        \"\"\"
        ...

    @abstractmethod
    def get_live_price(self, symbol: str) -> float:
        \"\"\"Latest LTP for symbol. Used by trade_executor for fills.\"\"\"
        ...

    @abstractmethod
    def get_instrument_info(self, symbol: str) -> InstrumentInfo:
        \"\"\"Metadata about the instrument (tick size, lot size, etc.).\"\"\"
        ...

    @abstractmethod
    def get_market_hours(self) -> MarketHoursConfig:
        \"\"\"Trading hours for this adapter's primary market.\"\"\"
        ...

    # ── OPTIONAL METHODS (default to no-op) ───────────────────

    def subscribe_ticks(self, symbol: str, callback: Callable) -> None:
        \"\"\"Subscribe to tick stream. callback(price, timestamp) on each tick.
        Adapters without streaming should poll instead — default is poll loop.\"\"\"
        pass

    def unsubscribe_ticks(self, symbol: str) -> None:
        pass

    # ── EXECUTION METHODS (DISABLED ON NON-PRODUCTION ADAPTERS) ──

    def place_order(self, *args, **kwargs):
        \"\"\"Real-money trading is HARD-DISABLED on non-AngelOne adapters.
        AngelOne adapter overrides this with real implementation.
        All paper trades are logged via the existing paper_trades.jsonl path,
        NOT via this method.\"\"\"
        import os
        paper_mode = os.getenv(\"PAPER_MODE\", \"true\").strip().lower() == \"true\"
        if not paper_mode and self.name != \"angelone\":
            raise PermissionError(
                f\"Real-money trading is permanently disabled on adapter '{self.name}'. \"
                f\"Set PAPER_MODE=true or switch active_adapter to 'angelone'.\"
            )
        # Paper mode: delegate to existing PaperOrderManager / JSONL logger
        # (this method is rarely called — most adapters do not implement execution)
        raise NotImplementedError(f\"Adapter '{self.name}' does not support order placement\")

    # ── HEALTH ──────────────────────────────────────────────

    @abstractmethod
    def health_check(self) -> dict:
        \"\"\"Return adapter health status.
        {\"status\": \"OK\"|\"DEGRADED\"|\"DOWN\", \"details\": \"...\", \"last_tick_age_sec\": int}
        \"\"\"
        ...

    def __repr__(self):
        return f\"<DataAdapter name={self.name}>\"


class AdapterError(Exception):
    \"\"\"Raised by adapters for data unavailability, auth failures, etc.\"\"\"
    pass
```

---

## 2. THE FACTORY — `modules/data_adapters/__init__.py`

```python
\"\"\"
modules/data_adapters/__init__.py
\"\"\"
import os
import yaml
from pathlib import Path
from typing import Optional
from .base_adapter import DataAdapter, InstrumentInfo, MarketHoursConfig, AdapterError

_CONFIG_PATH = Path(\"config/data_source.yaml\")
_ACTIVE: Optional[DataAdapter] = None


def _load_config() -> dict:
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(
            f\"Missing config/data_source.yaml — required for adapter selection. \"
            f\"Create it with: active_adapter: 'angelone'  (or binance/alphavantage/memory)\"
        )
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


def get_active_adapter(force_reload: bool = False) -> DataAdapter:
    \"\"\"
    Returns the currently configured DataAdapter instance (singleton).
    Reads config/data_source.yaml.
    \"\"\"
    global _ACTIVE
    if _ACTIVE is not None and not force_reload:
        return _ACTIVE

    cfg = _load_config()
    name = cfg.get(\"active_adapter\", \"\").strip().lower()

    if name == \"angelone\":
        from .angelone_adapter import AngelOneAdapter
        _ACTIVE = AngelOneAdapter(cfg.get(\"angelone\", {}))
    elif name == \"binance\":
        from .binance_adapter import BinanceAdapter
        _ACTIVE = BinanceAdapter(cfg.get(\"binance\", {}))
    elif name == \"alphavantage\":
        from .alphavantage_adapter import AlphaVantageAdapter
        _ACTIVE = AlphaVantageAdapter(cfg.get(\"alphavantage\", {}))
    elif name == \"memory\":
        from .memory_adapter import MemoryAdapter
        _ACTIVE = MemoryAdapter(cfg.get(\"memory\", {}))
    else:
        raise AdapterError(
            f\"Unknown active_adapter: '{name}'. \"
            f\"Must be one of: angelone | binance | alphavantage | memory\"
        )

    return _ACTIVE


__all__ = [
    \"get_active_adapter\",
    \"DataAdapter\",
    \"InstrumentInfo\",
    \"MarketHoursConfig\",
    \"AdapterError\",
]
```

---

## 3. THE CLI TEST HARNESS — `scripts/test_adapter.py`

```python
\"\"\"
scripts/test_adapter.py
Usage:
    python scripts/test_adapter.py <adapter_name> <symbol> <timeframe> <count>
Example:
    python scripts/test_adapter.py binance BTCUSDT 5m 100
\"\"\"
import sys
import os
import yaml
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CFG_PATH = Path(\"config/data_source.yaml\")


def main():
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(1)

    adapter_name, symbol, timeframe, count = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])

    # Force the requested adapter temporarily
    cfg = yaml.safe_load(open(CFG_PATH)) if CFG_PATH.exists() else {}
    cfg[\"active_adapter\"] = adapter_name
    yaml.safe_dump(cfg, open(CFG_PATH, \"w\"))

    from modules.data_adapters import get_active_adapter
    adapter = get_active_adapter(force_reload=True)

    print(f\"\n[TEST] Adapter loaded: {adapter}\")
    print(f\"[TEST] Requesting: symbol={symbol} timeframe={timeframe} count={count}\")

    # Bars
    df = adapter.get_bars(symbol, timeframe, count)
    print(f\"\n[TEST] Returned {len(df)} bars\")
    print(df.head(3).to_string())
    print(\"...\")
    print(df.tail(3).to_string())

    # Live price
    px = adapter.get_live_price(symbol)
    print(f\"\n[TEST] Live price for {symbol}: {px}\")

    # Instrument info
    info = adapter.get_instrument_info(symbol)
    print(f\"\n[TEST] Instrument info: {info}\")

    # Market hours
    hours = adapter.get_market_hours()
    print(f\"\n[TEST] Market hours: open={hours.market_open} close={hours.market_close} 24x7={hours.is_24x7}\")

    # Health
    health = adapter.health_check()
    print(f\"\n[TEST] Health: {health}\")

    # Assertions
    assert len(df) > 0, \"FAIL: get_bars returned empty DataFrame\"
    assert set([\"open\",\"high\",\"low\",\"close\",\"volume\"]).issubset(df.columns), \"FAIL: missing OHLCV columns\"
    assert df[\"close\"].iloc[-1] > 0, \"FAIL: latest close is non-positive\"
    assert px > 0, \"FAIL: live price is non-positive\"
    assert health[\"status\"] in (\"OK\",\"DEGRADED\"), f\"FAIL: health status = {health['status']}\"

    print(f\"\n[TEST] ✅ All assertions passed.\")


if __name__ == \"__main__\":
    main()
```

---

## 4. ACCEPTANCE TESTS

After implementing each adapter, this command MUST pass:

```bash
python scripts/test_adapter.py <adapter_name> <symbol> 5m 100
```

Expected output (truncated):
```
[TEST] Adapter loaded: <BinanceAdapter ...>
[TEST] Returned 100 bars
                          open      high       low     close       volume
timestamp
2026-05-09 21:50:00  104320.5  104410.0  104300.0  104380.5  120.532
...
[TEST] Live price for BTCUSDT: 104380.5
[TEST] Instrument info: InstrumentInfo(symbol='BTCUSDT', ...)
[TEST] Market hours: open=00:00:00 close=23:59:59 24x7=True
[TEST] Health: {'status': 'OK', 'details': 'WS connected', 'last_tick_age_sec': 1}
[TEST] ✅ All assertions passed.
```

**If this test fails for an adapter, do NOT proceed to use it in live_options_trader.py.**

---

## 5. INVARIANTS (what the interface guarantees to strategy code)

Strategy code can rely on these regardless of which adapter is active:

1. `get_bars()` always returns a non-empty DataFrame (raises AdapterError otherwise)
2. Columns are exactly `open, high, low, close, volume` — lowercase
3. Index is `DatetimeIndex` and timezone-aware
4. Bars are sorted oldest → newest
5. No gaps within a single trading session (gaps between sessions are OK)
6. `volume` is always non-negative
7. `high >= open, close, low` and `low <= open, close, high` per bar

Adapters that cannot satisfy these MUST raise `AdapterError` rather than return malformed data.

---

**END OF INTERFACE SPEC. Continue to BINANCE_CRYPTO_ADAPTER_SPEC.md.**
"
Observation: Create successful: /app/DATA_ADAPTER_INTERFACE.md