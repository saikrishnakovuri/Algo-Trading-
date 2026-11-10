import os
import yaml
from pathlib import Path
from typing import Optional
from .base_adapter import DataAdapter, InstrumentInfo, MarketHoursConfig, AdapterError

_CONFIG_PATH = Path("config/data_source.yaml")
_ACTIVE: Optional[DataAdapter] = None


def _load_config() -> dict:
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(
            "Missing config/data_source.yaml — required for adapter selection. "
            "Create it with: active_adapter: 'angelone'  (or binance/alphavantage/memory)"
        )
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


def get_active_adapter(force_reload: bool = False) -> DataAdapter:
    """
    Returns the currently configured DataAdapter instance (singleton).
    Reads config/data_source.yaml.
    """
    global _ACTIVE
    if _ACTIVE is not None and not force_reload:
        return _ACTIVE

    cfg = _load_config()
    name = cfg.get("active_adapter", "").strip().lower()

    if name == "angelone":
        from .angelone_adapter import AngelOneAdapter
        _ACTIVE = AngelOneAdapter(cfg.get("angelone", {}))
    elif name == "binance":
        from .binance_adapter import BinanceAdapter
        _ACTIVE = BinanceAdapter(cfg.get("binance", {}))
    elif name == "alphavantage":
        from .alphavantage_adapter import AlphaVantageAdapter
        _ACTIVE = AlphaVantageAdapter(cfg.get("alphavantage", {}))
    elif name == "memory":
        from .memory_adapter import MemoryAdapter
        _ACTIVE = MemoryAdapter(cfg.get("memory", {}))
    else:
        raise AdapterError(
            f"Unknown active_adapter: '{name}'. "
            f"Must be one of: angelone | binance | alphavantage | memory"
        )

    return _ACTIVE


__all__ = [
    "get_active_adapter",
    "DataAdapter",
    "InstrumentInfo",
    "MarketHoursConfig",
    "AdapterError",
]
