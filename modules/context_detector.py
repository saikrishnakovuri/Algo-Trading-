"""
Context Detector — classifies market into actionable regime.
Runs every 5m bar. Output feeds Strategy Mapper.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

RegimeType = Literal[
    "TRENDING_UP", "TRENDING_DOWN",
    "RANGING", "LOW_VOL", "HIGH_VOL",
    "BREAKOUT_SETUP", "VOLATILE", "CHOPPY"
]

VolatilityType = Literal["LOW", "NORMAL", "HIGH", "EXTREME"]
StructureType  = Literal["STRONG_TREND", "WEAK_PULLBACK",
                          "CLEAN_RANGE", "COMPRESSION", "BROKEN"]
TimeZoneType   = Literal["OPENING", "MORNING", "MIDDAY",
                          "AFTERNOON", "CLOSING"]

@dataclass
class MarketContext:
    regime: RegimeType
    volatility: VolatilityType
    structure: StructureType
    time_zone: TimeZoneType
    vix_state: str          # LOW/NORMAL/HIGH/EXTREME
    atr_pct: float          # ATR as % of price
    vwap_distance_pct: float # How far price is from VWAP %
    trend_strength: float   # 0-100
    volume_ratio: float     # current vol / avg vol
    confidence: float       # detector confidence 0-100


class ContextDetector:
    """
    Detects market context using:
    - EMA alignment (9/20/50)
    - ATR-based volatility
    - VWAP position
    - Structure (HH/HL or LH/LL)
    - Volume profile
    - Time of day (IST)
    - VIX level
    """

    # ── Thresholds (tuned for NIFTY 5m) ─────────────────
    ATR_LOW_PCT     = 0.003   # ATR < 0.3% of price = LOW_VOL
    ATR_HIGH_PCT    = 0.008   # ATR > 0.8% of price = HIGH_VOL
    ATR_EXTREME_PCT = 0.015   # ATR > 1.5% = EXTREME
    VWAP_FAR_PCT    = 0.004   # Price > 0.4% from VWAP = extended
    VOLUME_SURGE    = 1.8     # 1.8x avg volume = surge
    VOLUME_LOW      = 0.6     # 0.6x avg volume = dry
    VIX_LOW         = 12.0
    VIX_HIGH        = 20.0
    VIX_EXTREME     = 28.0
    STABILITY_BARS  = 3       # regime must hold N bars before flip

    def __init__(self):
        self._regime_buffer = []  # for stability filter

    def detect(self, df: pd.DataFrame, vix: float,
               current_time=None, df_1m: pd.DataFrame = None) -> MarketContext:
        """
        df: 5m OHLCV with at least 50 bars
        vix: current India VIX value
        current_time: datetime (IST) for time zone
        df_1m: optional 1m OHLCV for high-resolution structure shift detection
        """
        if df is None or len(df) < 50:
            return self._default_context()

        # Handle potential capitalization variations in OHLCV
        df_lower = df.copy()
        df_lower.columns = [c.lower() for c in df_lower.columns]
        
        close  = df_lower["close"]
        high   = df_lower["high"]
        low    = df_lower["low"]
        volume = df_lower["volume"]

        # ── Step 0: 1m Structure Shift (MSS/CHoCH) ───
        mss_bullish = False
        mss_bearish = False
        if df_1m is not None and len(df_1m) >= 20:
            d1 = df_1m.copy()
            d1.columns = [c.lower() for c in d1.columns]
            # Detect HH/HL or LH/LL on 1m basis to see "Internal Structure"
            # 1m MSS often leads 5m Trend by 10-15 minutes
            recent_1m_highs = d1['high'].iloc[-15:]
            recent_1m_lows  = d1['low'].iloc[-15:]
            
            # Simple Swing High/Low Break detection
            prev_swing_high = recent_1m_highs.iloc[:-3].max()
            prev_swing_low  = recent_1m_lows.iloc[:-3].min()
            
            # CHoCH: Latest close breaks previous swing after a consolidation
            if d1['close'].iloc[-1] > prev_swing_high: mss_bullish = True
            if d1['close'].iloc[-1] < prev_swing_low:  mss_bearish = True

        # ── Indicators ─────────────────────────────────
        ema9  = close.ewm(span=9, adjust=False).mean()
        ema20 = close.ewm(span=20, adjust=False).mean()
        ema50 = close.ewm(span=50, adjust=False).mean()
        atr   = (high - low).rolling(14).mean()
        
        # Standard VWAP = cumsum(price * volume) / cumsum(volume) reset daily
        # Ensure we have date information for grouping
        df_today = df_lower.copy()
        df_today['date'] = df_today.index.date
        
        # Calculate daily VWAP
        v = df_today['volume'].replace(0, 1)
        df_today['cum_vol'] = v.groupby(df_today['date']).cumsum()
        df_today['cum_vol_price'] = (df_today['close'] * v).groupby(df_today['date']).cumsum()
        vwap = df_today['cum_vol_price'] / df_today['cum_vol']

        c    = close.iloc[-1]
        atr_ = atr.iloc[-1]
        atr_pct = atr_ / c if c > 0 else 0

        # ── Trend Detection ─────────────────────────────
        ema_bullish = (ema9.iloc[-1] > ema20.iloc[-1] > ema50.iloc[-1])
        ema_bearish = (ema9.iloc[-1] < ema20.iloc[-1] < ema50.iloc[-1])

        # Structure: slope-based trend detection over last 10 bars (robust to 1-bar noise)
        recent_highs = high.iloc[-10:].values
        recent_lows  = low.iloc[-10:].values
        x = np.arange(len(recent_highs))
        high_slope = np.polyfit(x, recent_highs, 1)[0]
        low_slope  = np.polyfit(x, recent_lows, 1)[0]
        c_val = close.iloc[-1]
        # Normalize slope to % of price per bar
        high_slope_pct = high_slope / c_val if c_val > 0 else 0
        low_slope_pct  = low_slope  / c_val if c_val > 0 else 0
        # Trend if BOTH slopes same sign and |slope| > 0.01% per bar
        hh_hl = (high_slope_pct >  0.0001 and low_slope_pct >  0.0001)
        lh_ll = (high_slope_pct < -0.0001 and low_slope_pct < -0.0001)

        # Trend strength: EMA spread %
        ema_spread = abs(ema9.iloc[-1] - ema50.iloc[-1]) / c * 100 if c > 0 else 0
        trend_strength = min(100, ema_spread * 20)

        # ── Volatility ──────────────────────────────────
        if atr_pct < self.ATR_LOW_PCT:
            volatility = "LOW"
        elif atr_pct > self.ATR_EXTREME_PCT:
            volatility = "EXTREME"
        elif atr_pct > self.ATR_HIGH_PCT:
            volatility = "HIGH"
        else:
            volatility = "NORMAL"

        # ── VIX State ───────────────────────────────────
        if vix < self.VIX_LOW:
            vix_state = "LOW"
        elif vix > self.VIX_EXTREME:
            vix_state = "EXTREME"
        elif vix > self.VIX_HIGH:
            vix_state = "HIGH"
        else:
            vix_state = "NORMAL"

        # ── Volume ──────────────────────────────────────
        avg_vol    = volume.rolling(20).mean().iloc[-1]
        vol_ratio  = volume.iloc[-1] / avg_vol if avg_vol > 0 else 1.0

        # ── VWAP Distance ───────────────────────────────
        vwap_dist = abs(c - vwap.iloc[-1]) / c if c > 0 else 0

        # ── Structure Type ──────────────────────────────
        price_range = high.iloc[-20:].max() - low.iloc[-20:].min()
        range_tight = price_range / c < 0.005 if c > 0 else False # <0.5% = compression

        if range_tight and volatility == "LOW":
            structure = "COMPRESSION"
        elif hh_hl and ema_bullish:
            structure = "STRONG_TREND"
        elif lh_ll and ema_bearish:
            structure = "STRONG_TREND"
        elif (not hh_hl and not lh_ll):
            structure = "CLEAN_RANGE"
        elif volatility in ["HIGH", "EXTREME"]:
            structure = "BROKEN"
        else:
            structure = "WEAK_PULLBACK"

        # ── Time Zone (IST) ─────────────────────────────
        if current_time:
            h, m = current_time.hour, current_time.minute
            mins = h * 60 + m
            if   mins < 9*60+45:  time_zone = "OPENING"
            elif mins < 11*60:    time_zone = "MORNING"
            elif mins < 13*60:    time_zone = "MIDDAY"
            elif mins < 14*60+30: time_zone = "AFTERNOON"
            else:                  time_zone = "CLOSING"
        else:
            time_zone = "MORNING"

        # ── Regime Classification ───────────────────────
        if volatility == "EXTREME" or vix_state == "EXTREME":
            raw_regime = "VOLATILE"
        elif range_tight and volatility == "LOW":
            raw_regime = "BREAKOUT_SETUP"
        elif ema_bullish and hh_hl and volatility != "HIGH":
            raw_regime = "TRENDING_UP"
        elif ema_bearish and lh_ll and volatility != "HIGH":
            raw_regime = "TRENDING_DOWN"
        elif volatility == "HIGH":
            raw_regime = "HIGH_VOL"
        elif volatility == "LOW" and not range_tight:
            raw_regime = "LOW_VOL"
        elif structure == "CLEAN_RANGE":
            raw_regime = "RANGING"
        else:
            raw_regime = "CHOPPY"

        # --- MSS UPGRADE: Catch early rallies from chop ---
        if mss_bullish and raw_regime in ["CHOPPY", "RANGING", "LOW_VOL"]:
            raw_regime = "TRENDING_UP"
        elif mss_bearish and raw_regime in ["CHOPPY", "RANGING", "LOW_VOL"]:
            raw_regime = "TRENDING_DOWN"
        # --------------------------------------------------

        # ── Stability Filter (3-bar majority vote) ─────────
        from collections import Counter
        self._regime_buffer.append(raw_regime)
        if len(self._regime_buffer) > self.STABILITY_BARS:
            self._regime_buffer.pop(0)

        counts = Counter(self._regime_buffer)
        most_common_regime, most_common_count = counts.most_common(1)[0]
        # Use majority regime if at least 2 of last 3 agree, else fall back to latest
        if most_common_count >= 2:
            stable_regime = most_common_regime
        else:
            stable_regime = raw_regime

        unique_regimes = len(set(self._regime_buffer))
        if unique_regimes == 1:
            detector_confidence = 85
        elif unique_regimes == 2:
            detector_confidence = 70
        else:
            detector_confidence = 55

        return MarketContext(
            regime=stable_regime,
            volatility=volatility,
            structure=structure,
            time_zone=time_zone,
            vix_state=vix_state,
            atr_pct=round(atr_pct, 5),
            vwap_distance_pct=round(vwap_dist, 5),
            trend_strength=round(trend_strength, 1),
            volume_ratio=round(vol_ratio, 2),
            confidence=detector_confidence
        )

    def _default_context(self) -> MarketContext:
        return MarketContext("CHOPPY","NORMAL","BROKEN",
                             "MORNING","NORMAL",0,0,0,1,0)
