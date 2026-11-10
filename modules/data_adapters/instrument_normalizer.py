#
# modules/data_adapters/instrument_normalizer.py
#
from dataclasses import dataclass
from typing import Optional
import pandas as pd

from .base_adapter import InstrumentInfo


@dataclass
class NormalizationProfile:
    """
    Per-instrument scaling profile.
    Used to translate strategy concepts (ATR multiples, R-multiples) into
    market-appropriate values without changing strategy code.
    """
    canonical_symbol: str           # strategy uses this (e.g., "NIFTY")
    native_symbol: str              # adapter-side symbol (e.g., "BTCUSDT" or "EUR/USD")
    asset_class: str                # "INDEX" | "CRYPTO" | "FOREX" | "OPTION" | "EQUITY"
    tick_size: float                # minimum price increment
    lot_size: int                   # contract multiplier (NIFTY=65, BTC=1, forex=1)
    price_decimals: int             # 0 for NIFTY, 2 for BTC, 4 for EUR/USD, 2 for JPY
    notional_per_lot_quote: float   # how many quote units 1 lot represents
    typical_atr_pct: float          # typical ATR as % of price (sanity check)


# Pre-built profiles for known instruments
PROFILES = {
    # NSE Index Options
    "NIFTY": NormalizationProfile(
        canonical_symbol="NIFTY",
        native_symbol="NIFTY",
        asset_class="INDEX",
        tick_size=0.05,
        lot_size=65,
        price_decimals=2,
        notional_per_lot_quote=1.0,
        typical_atr_pct=0.30,  # NIFTY 5m ATR ~ 0.3% of price
    ),
    "BANKNIFTY": NormalizationProfile(
        canonical_symbol="BANKNIFTY",
        native_symbol="BANKNIFTY",
        asset_class="INDEX",
        tick_size=0.05,
        lot_size=30,
        price_decimals=2,
        notional_per_lot_quote=1.0,
        typical_atr_pct=0.40,
    ),
    # Crypto (via Binance)
    "BTCUSDT": NormalizationProfile(
        canonical_symbol="NIFTY",      # NIFTY-equivalent for strategy
        native_symbol="BTCUSDT",
        asset_class="CRYPTO",
        tick_size=0.01,
        lot_size=1,                    # crypto is fractional, lot=1
        price_decimals=2,
        notional_per_lot_quote=1.0,
        typical_atr_pct=0.50,  # crypto more volatile
    ),
    "ETHUSDT": NormalizationProfile(
        canonical_symbol="BANKNIFTY",
        native_symbol="ETHUSDT",
        asset_class="CRYPTO",
        tick_size=0.01,
        lot_size=1,
        price_decimals=2,
        notional_per_lot_quote=1.0,
        typical_atr_pct=0.60,
    ),
    # Forex (via Alpha Vantage)
    "EUR/USD": NormalizationProfile(
        canonical_symbol="NIFTY",
        native_symbol="EUR/USD",
        asset_class="FOREX",
        tick_size=0.0001,
        lot_size=1,                    # we use lot=1 for forex paper testing
        price_decimals=5,
        notional_per_lot_quote=1.0,
        typical_atr_pct=0.10,  # forex calmer
    ),
    "GBP/USD": NormalizationProfile(
        canonical_symbol="BANKNIFTY",
        native_symbol="GBP/USD",
        asset_class="FOREX",
        tick_size=0.0001,
        lot_size=1,
        price_decimals=5,
        notional_per_lot_quote=1.0,
        typical_atr_pct=0.10,
    ),
    "USD/JPY": NormalizationProfile(
        canonical_symbol="NIFTY",
        native_symbol="USD/JPY",
        asset_class="FOREX",
        tick_size=0.01,                # JPY pairs different
        lot_size=1,
        price_decimals=3,
        notional_per_lot_quote=1.0,
        typical_atr_pct=0.10,
    ),
}


def get_profile(native_symbol: str) -> Optional[NormalizationProfile]:
    """Look up normalization profile by adapter-side symbol."""
    return PROFILES.get(native_symbol)


def normalize_price(price: float, profile: NormalizationProfile) -> float:
    """Round price to instrument's tick size."""
    return round(price / profile.tick_size) * profile.tick_size


def pnl_in_quote_currency(
    entry: float, exit_price: float, lots: int, profile: NormalizationProfile,
    direction: str = "CE"
) -> float:
    """Compute PnL in the instrument's quote currency (USD for crypto/forex, INR for NSE)."""
    delta = (exit_price - entry) if direction.upper() in ("CE", "LONG", "BUY") else (entry - exit_price)
    return delta * lots * profile.lot_size * profile.notional_per_lot_quote


def sanity_check_atr(atr: float, current_price: float, profile: NormalizationProfile) -> bool:
    """
    Sanity check: ATR should be roughly within 0.5× to 3× the typical for this instrument.
    Detects feed errors (e.g., adapter returning prices in wrong unit).
    """
    atr_pct = (atr / current_price) * 100
    return (profile.typical_atr_pct * 0.5) <= atr_pct <= (profile.typical_atr_pct * 3)


__all__ = ["NormalizationProfile", "PROFILES", "get_profile",
           "normalize_price", "pnl_in_quote_currency", "sanity_check_atr"]
