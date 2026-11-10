import os
import time
import logging
from datetime import datetime, time as dtime, timedelta
from typing import Callable, Optional
import requests
import pandas as pd

from .base_adapter import (
    DataAdapter, InstrumentInfo, MarketHoursConfig, AdapterError
)

logger = logging.getLogger("AlphaVantageAdapter")


class AlphaVantageAdapter(DataAdapter):
    """
    Alpha Vantage REST adapter for forex data.
    """

    name = "alphavantage"
    REST_BASE = "https://www.alphavantage.co/query"

    TF_MAP = {
        "1m":  "1min",
        "5m":  "5min",
        "15m": "15min",
        "30m": "30min",
        "1h":  "60min",
    }

    def __init__(self, cfg: dict):
        self.cfg = cfg or {}
        self.symbol_mapping = self.cfg.get("symbol_mapping", {
            "NIFTY": "EUR/USD",
            "BANKNIFTY": "GBP/USD",
        })
        self.poll_interval_sec = int(self.cfg.get("poll_interval_sec", 60))

        self.api_key = os.getenv("ALPHAVANTAGE_API_KEY", "").strip()
        if not self.api_key:
            self.api_key = self.cfg.get("api_key", "").strip()

        self.session = requests.Session()
        self._call_times = []
        self._daily_count = 0
        self._daily_reset_at = time.time() + 86400
        self._bar_cache = {}
        self._price_cache = {}
        self.cache_ttl_sec = 60

    def _call(self, params: dict) -> dict:
        params["apikey"] = self.api_key
        r = self.session.get(self.REST_BASE, params=params, timeout=15)
        r.raise_for_status()
        j = r.json()
        if "Error Message" in j:
            raise AdapterError(f"Alpha Vantage error: {j['Error Message']}")
        return j

    def _to_native(self, symbol: str) -> tuple[str, str]:
        pair = self.symbol_mapping.get(symbol.upper(), symbol.upper())
        if "/" not in pair:
            return pair[:3], pair[3:]
        return pair.split("/")

    def get_bars(self, symbol: str, timeframe: str = "5m", count: int = 200) -> pd.DataFrame:
        from_c, to_c = self._to_native(symbol)
        tf = self.TF_MAP.get(timeframe)
        params = {"function": "FX_INTRADAY", "from_symbol": from_c, "to_symbol": to_c, "interval": tf}
        j = self._call(params)
        
        series_key = next((k for k in j.keys() if k.startswith("Time Series FX")), None)
        rows = []
        for ts_str, bar in j[series_key].items():
            rows.append({
                "timestamp": pd.to_datetime(ts_str),
                "open": float(bar["1. open"]),
                "high": float(bar["2. high"]),
                "low":  float(bar["3. low"]),
                "close": float(bar["4. close"]),
                "volume": 0.0,
            })
        df = pd.DataFrame(rows).sort_values("timestamp").set_index("timestamp")
        df.index = df.index.tz_localize("US/Eastern").tz_convert("Asia/Kolkata")
        return df.tail(count)

    def get_live_price(self, symbol: str) -> float:
        from_c, to_c = self._to_native(symbol)
        j = self._call({
            "function": "CURRENCY_EXCHANGE_RATE",
            "from_currency": from_c,
            "to_currency": to_c,
        })
        return float(j["Realtime Currency Exchange Rate"]["5. Exchange Rate"])

    def get_instrument_info(self, symbol: str) -> InstrumentInfo:
        from_c, to_c = self._to_native(symbol)
        return InstrumentInfo(
            symbol=symbol.upper(),
            native_symbol=f"{from_c}/{to_c}",
            asset_class="FOREX",
            tick_size=0.0001,
            lot_size=1,
            quote_currency=to_c,
            is_24x7=False,
        )

    def get_market_hours(self) -> MarketHoursConfig:
        return MarketHoursConfig(
            market_open=dtime(0, 0),
            market_close=dtime(23, 59, 59),
            signal_gate=dtime(10, 0),
            no_entry_after=dtime(12, 0),
            force_close_at=dtime(15, 15),
            timezone="Asia/Kolkata",
            is_24x7=False,
            trading_days=["Mon", "Tue", "Wed", "Thu", "Fri"],
        )

    def health_check(self) -> dict:
        return {"status": "OK", "details": "REST connected", "last_tick_age_sec": None}
