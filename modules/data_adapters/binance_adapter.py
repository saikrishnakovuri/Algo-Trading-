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

logger = logging.getLogger("BinanceAdapter")


class BinanceAdapter(DataAdapter):
    """
    Binance Spot market data adapter.
    Strategy still requests 'NIFTY' / 'BANKNIFTY' — we translate to BTC/ETH.
    """

    name = "binance"

    REST_BASE = "https://api.binance.com/api/v3"
    WS_BASE   = "wss://stream.binance.com:9443/ws"

    # Binance interval mapping
    TF_MAP = {
        "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m",
        "30m": "30m", "1h": "1h", "4h": "4h", "1d": "1d",
    }

    def __init__(self, cfg: dict):
        self.cfg = cfg or {}
        self.symbol_mapping = self.cfg.get("symbol_mapping", {
            "NIFTY": "BTCUSDT",
            "BANKNIFTY": "ETHUSDT",
        })
        self.api_key = os.getenv("BINANCE_API_KEY", "").strip()
        self.session = requests.Session()
        if self.api_key:
            self.session.headers["X-MBX-APIKEY"] = self.api_key

        self._last_tick_at: dict[str, float] = {}
        self._tick_subscribers: dict[str, list[Callable]] = {}
        self._ws_thread: Optional[threading.Thread] = None

        self._ping()

    def _ping(self):
        try:
            r = self.session.get(f"{self.REST_BASE}/ping", timeout=5)
            r.raise_for_status()
            logger.info(f"[Binance] REST ping OK ({r.elapsed.total_seconds()*1000:.0f}ms)")
        except Exception as e:
            raise AdapterError(f"Binance REST unreachable: {e}")

    def _to_native(self, symbol: str) -> str:
        return self.symbol_mapping.get(symbol.upper(), symbol.upper())

    def get_bars(self, symbol: str, timeframe: str = "5m", count: int = 200) -> pd.DataFrame:
        native = self._to_native(symbol)
        tf = self.TF_MAP.get(timeframe)
        if tf is None:
            raise AdapterError(f"Unsupported timeframe: {timeframe}")

        params = {"symbol": native, "interval": tf, "limit": min(count, 1000)}
        try:
            r = self.session.get(f"{self.REST_BASE}/klines", params=params, timeout=10)
            r.raise_for_status()
            klines = r.json()
        except requests.RequestException as e:
            raise AdapterError(f"Binance get_bars failed: {e}")

        df = pd.DataFrame(klines, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore"
        ])
        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        df.set_index("timestamp", inplace=True)
        df = df[["open", "high", "low", "close", "volume"]].astype(float)
        df.index = df.index.tz_convert("Asia/Kolkata")
        return df

    def get_live_price(self, symbol: str) -> float:
        native = self._to_native(symbol)
        try:
            r = self.session.get(f"{self.REST_BASE}/ticker/price", params={"symbol": native}, timeout=5)
            r.raise_for_status()
            return float(r.json()["price"])
        except Exception as e:
            raise AdapterError(f"Binance get_live_price failed: {e}")

    def get_instrument_info(self, symbol: str) -> InstrumentInfo:
        native = self._to_native(symbol)
        return InstrumentInfo(
            symbol=symbol.upper(),
            native_symbol=native,
            asset_class="CRYPTO",
            tick_size=0.01,
            lot_size=1,
            quote_currency="USDT",
            is_24x7=True,
        )

    def get_market_hours(self) -> MarketHoursConfig:
        return MarketHoursConfig(
            market_open=dtime(0, 0),
            market_close=dtime(23, 59, 59),
            signal_gate=dtime(10, 0),
            no_entry_after=dtime(12, 0),
            force_close_at=dtime(15, 15),
            timezone="Asia/Kolkata",
            is_24x7=True,
            trading_days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        )

    def health_check(self) -> dict:
        return {"status": "OK", "details": "REST ping OK", "last_tick_age_sec": None}
