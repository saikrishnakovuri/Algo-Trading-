"""
Scores each strategy signal 0-100.
Only signals above threshold are executed.
Different weights per factor per strategy type.
"""
import pandas as pd
from modules.strategy_definitions import STRATEGY_DEFINITIONS

class ConfidenceScorer:

    # ── Base weights by factor ────────────────────────
    WEIGHTS = {
        "trend_alignment":    30,  # is trade in regime direction?
        "volume_confirmation":20,  # volume supports move?
        "structure_clarity":  25,  # clean S/R / pattern?
        "volatility_fit":     15,  # ATR matches strategy needs?
        "time_quality":       10,  # best time of day?
    }

    # ── Time quality multipliers (IST) ───────────────
    TIME_QUALITY = {
        "OPENING":   0.0,   # 09:15-09:45 → SKIP (noise)
        "MORNING":   1.0,   # 09:45-11:00 → BEST
        "MIDDAY":    0.8,   # 11:00-13:00 → GOOD
        "AFTERNOON": 0.6,   # 13:00-14:30 → CAUTION
        "CLOSING":   0.0,   # 14:30+      → SKIP
    }

    STRATEGY_BONUS = {
        "VWAP_BOUNCE":       0,
        "MOMENTUM_BREAKOUT": 6,
        "STRUCTURE_BOUNCE":  4,
        "SWEEP_RETEST":      5,
        "SMC_CORE":          0,
        "CANDLESTICK":       3,
        "MEAN_REVERSION":    3,
    }

    def score(self, strategy_name: str, signal: dict,
              ctx, df: pd.DataFrame) -> float:
        """
        Returns confidence score 0-100.
        signal: raw signal from strategy engine
        ctx: MarketContext from ContextDetector
        df: 5m OHLCV dataframe
        """
        score = 0.0
        defn = STRATEGY_DEFINITIONS.get(strategy_name, {})

        # 1. TREND ALIGNMENT (30 pts)
        signal_dir = signal.get("direction", "")
        if ctx.regime == "TRENDING_UP"   and signal_dir == "CE": score += 30
        elif ctx.regime == "TRENDING_DOWN" and signal_dir == "PE": score += 30
        elif ctx.regime in ["RANGING", "BREAKOUT_SETUP"]: score += 20
        else: score += 10  # partial credit

        # 2. VOLUME CONFIRMATION (20 pts)
        vol_ratio = ctx.volume_ratio
        
        # For index symbols or zero-volume data, give neutral volume score
        if vol_ratio == 0 or vol_ratio != vol_ratio: # nan check
            score += 10
        elif vol_ratio > 2.0:   score += 20
        elif vol_ratio > 1.5: score += 16
        elif vol_ratio > 1.0: score += 10
        elif vol_ratio > 0.7: score += 5
        # <0.7 = dead volume, no points

        # 3. STRUCTURE CLARITY (25 pts)
        structure_scores = {
            "STRONG_TREND":  25,
            "COMPRESSION":   22,
            "CLEAN_RANGE":   20,
            "WEAK_PULLBACK": 12,
            "BROKEN":         5,
        }
        score += structure_scores.get(ctx.structure, 10)

        # 4. VOLATILITY FIT (15 pts)
        valid_vols = {
            "VWAP_BOUNCE":       ["NORMAL", "LOW"],
            "MOMENTUM_BREAKOUT": ["NORMAL", "HIGH"],
            "MEAN_REVERSION":    ["HIGH", "NORMAL"],
            "SWEEP_RETEST":      ["NORMAL", "HIGH", "LOW"],
            "STRUCTURE_BOUNCE":  ["LOW", "NORMAL"],
            "CANDLESTICK":       ["NORMAL", "LOW"],
            "SMC_CORE":          ["NORMAL", "LOW"],
            "LIQUIDITY_TRAP":    ["NORMAL"],
        }
        if ctx.volatility in valid_vols.get(strategy_name, []):
            score += 15
        elif ctx.volatility == "NORMAL":
            score += 8  # neutral

        # 5. TIME QUALITY (10 pts)
        tq = self.TIME_QUALITY.get(ctx.time_zone, 0.5)
        score += 10 * tq

        # ── Bonus Conditions ─────────────────────────
        # VIX alignment bonus
        if ctx.vix_state == "NORMAL": score += 5
        if ctx.vix_state == "LOW" and strategy_name in [
            "MOMENTUM_BREAKOUT", "BREAKOUT_SETUP"]: score += 8

        # Detector confidence bonus
        if ctx.confidence >= 80: score += 5

        # Strategy-specific raw signal confidence
        raw_conf = signal.get("confidence", 50)
        if 0 <= raw_conf <= 1.0:
            raw_conf = raw_conf * 100
        score += (raw_conf - 50) * 0.15

        score += self.STRATEGY_BONUS.get(strategy_name, 0)

        return min(100, max(0, round(score, 1)))


# ── Thresholds ───────────────────────────────────────
CONFIDENCE_THRESHOLDS = {
    "default":                 52,
    "TRENDING_UP_regime":      48,    # looser — we want trend participation
    "TRENDING_DOWN_regime":    48,
    "RANGING_regime":          55,
    "BREAKOUT_SETUP_regime":   50,
    "LOW_VOL_regime":          52,
    "HIGH_VOL_regime":         60,
    "CHOPPY_regime":           58,    # stricter — only high conviction in chop
    "reduced_size":            45,
    "aggressive_mode":         35,
}
