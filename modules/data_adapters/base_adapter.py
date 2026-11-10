#
# modules/data_adapters/base_adapter.py
#
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, time
from typing import Callable, Optional
import pandas as pd


@dataclass
class InstrumentInfo:
    """Metadata for a tradable instrument."""
    symbol: str                  # canonical strategy-side symbol (e.g., "NIFTY")
    native_symbol: str           # adapter-side symbol (e.g., "BTCUSDT" or "EUR/USD")
    asset_class: str             # "INDEX" | "CRYPTO" | "FOREX" | "OPTION" | "EQUITY"
    tick_size: float             # minimum price increment
    lot_size: int                # contract size (1 for crypto/forex, 65 for NIFTY)
    quote_currency: str          # "INR" | "USD" | "USDT"
    is_24x7: bool                # crypto=True, forex=False, NSE=False


@dataclass
class MarketHoursConfig:
    """Trading hours for an asset class."""
    market_open: time            # e.g., 09:15 for NSE
    market_close: time           # e.g., 15:30 for NSE
    signal_gate: time            # earliest entry time (e.g., 10:00)
    no_entry_after: time         # latest entry time (e.g., 12:00)
    force_close_at: time         # auto-exit time (e.g., 15:15)
    timezone: str                # "Asia/Kolkata" | "UTC" | "America/New_York"
    is_24x7: bool                # crypto markets
    trading_days: list           # e.g., ["Mon","Tue","Wed","Thu","Fri"]


class DataAdapter(ABC):
    """
    Abstract base class for market data adapters.
    Strategy engines only interact with this interface.
    Concrete implementations: AngelOneAdapter, BinanceAdapter,
    AlphaVantageAdapter, MemoryAdapter.
    """

    name: str = "base"                 # override in subclass

    # ── REQUIRED METHODS ──────────────────────────────────────

    @abstractmethod
    def get_bars(
        self,
        symbol: str,
        timeframe: str = "5m",
        count: int = 200
    ) -> pd.DataFrame:
        """
        Return the last `count` OHLCV bars for `symbol`.

        Returns:
            DataFrame with columns: open, high, low, close, volume
            Index: DatetimeIndex (timezone-aware in adapter's local tz)
            Length: exactly `count` rows (or all available if fewer exist)

        Raises:
            AdapterError if symbol unknown or data unavailable.
        """
        ...

    @abstractmethod
    def get_live_price(self, symbol: str) -> float:
        """Latest LTP for symbol. Used by trade_executor for fills."""
        ...

    @abstractmethod
    def get_instrument_info(self, symbol: str) -> InstrumentInfo:
        """Metadata about the instrument (tick size, lot size, etc.)."""
        ...

    @abstractmethod
    def get_market_hours(self) -> MarketHoursConfig:
        """Trading hours for this adapter's primary market."""
        ...

    # ── OPTIONAL METHODS (default to no-op) ───────────────────

    def subscribe_ticks(self, symbol: str, callback: Callable) -> None:
        """Subscribe to tick stream. callback(price, timestamp) on each tick.
        Adapters without streaming should poll instead — default is poll loop."""
        pass

    def unsubscribe_ticks(self, symbol: str) -> None:
        pass

    # ── EXECUTION METHODS (DISABLED ON NON-PRODUCTION ADAPTERS) ──

    def place_order(self, *args, **kwargs):
        """Real-money trading is HARD-DISABLED on non-AngelOne adapters.
        AngelOne adapter overrides this with real implementation.
        All paper trades are logged via the existing paper_trades.jsonl path,
        NOT via this method."""
        import os
        paper_mode = os.getenv("PAPER_MODE", "true").strip().lower() == "true"
        if not paper_mode and self.name != "angelone":
            raise PermissionError(
                f"Real-money trading is permanently disabled on adapter '{self.name}'. "
                f"Set PAPER_MODE=true or switch active_adapter to 'angelone'."
            )
        # Paper mode: delegate to existing PaperOrderManager / JSONL logger
        # (this method is rarely called — most adapters do not implement execution)
        raise NotImplementedError(f"Adapter '{self.name}' does not support order placement")

    # ── HEALTH ──────────────────────────────────────────────

    @abstractmethod
    def health_check(self) -> dict:
        """Return adapter health status.
        {"status": "OK"|"DEGRADED"|"DOWN", "details": "...", "last_tick_age_sec": int}
        """
        ...

    # ── LEGACY COMPATIBILITY METHODS ────────────────────────

    def initialize_data(self, symbols_map: dict, tier1_symbols: list = None):
        """Legacy compatibility: Stores reverse mapping from token to symbol."""
        self._token_to_symbol = {v: k for k, v in symbols_map.items()}

    def start_streaming(self, tokens: list):
        """Legacy compatibility: No-op for adapters that manage their own streams."""
        pass

    def get_5m_candles(self, token: str, count: int = 100) -> Optional[pd.DataFrame]:
        """Legacy compatibility: Maps token to symbol and calls get_bars."""
        symbol = getattr(self, "_token_to_symbol", {}).get(token, token)
        try:
            return self.get_bars(symbol, "5m", count)
        except AdapterError:
            return None

    def __repr__(self):
        return f"<DataAdapter name={self.name}>"


class AdapterError(Exception):
    """Raised by adapters for data unavailability, auth failures, etc."""
    pass
