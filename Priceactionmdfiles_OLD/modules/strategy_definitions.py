"""
Each strategy defined as a template.
Contains: entry_logic, sl_type, tp_type, 
          min_bars_needed, instruments, 
          cost_viable (passes Indian STT test)
"""

STRATEGY_DEFINITIONS = {

    "VWAP_BOUNCE": {
        "description": "Price pulls to VWAP, trend intact, closes back in direction",
        "entry": {
            "condition":  "price touches session VWAP ±0.1% AND closes back in trend direction",
            "confirmation": "next bar confirms (no immediate reversal)",
            "volume":     "volume >= 0.8x avg (not dead bounce)",
            "trend_req":  "EMA9 > EMA20 for long, EMA9 < EMA20 for short",
        },
        "sl":     "1.0x ATR below entry (or last swing low)",
        "tp":     "Fixed 2.0R (TRENDING) / Trail 1.5x ATR (LOW_VOL)",
        "be_move": "0.7R",
        "valid_regimes": ["TRENDING_UP", "TRENDING_DOWN", "LOW_VOL"],
        "invalid_regimes": ["RANGING", "VOLATILE", "CHOPPY"],
        "instruments": ["NIFTY", "BANKNIFTY", "ALL_MIDCAP"],
        "cost_viable": True,
        "min_bars": 20,
    },

    "MOMENTUM_BREAKOUT": {
        "description": "ATR-defined range breakout with volume surge",
        "entry": {
            "condition":  "price closes outside 20-bar ATR range",
            "confirmation": "volume > 1.5x 20-bar average",
            "candle":     "breakout candle body > 60% of candle range",
        },
        "sl":     "inside the broken range (opposite boundary)",
        "tp":     "measured move (range height projected) or 2.5R",
        "be_move": "1.0R",
        "valid_regimes": ["TRENDING_UP", "TRENDING_DOWN",
                          "LOW_VOL", "BREAKOUT_SETUP"],
        "invalid_regimes": ["RANGING", "HIGH_VOL", "CHOPPY"],
        "instruments": ["NIFTY", "BANKNIFTY"],
        "cost_viable": True,
        "min_bars": 20,
    },

    "MEAN_REVERSION": {
        "description": "Statistical fade at ±2.5σ VWAP or Bollinger extremes",
        "entry": {
            "condition":  "price > 2.5σ from VWAP OR outside upper/lower BB",
            "rsi_filter": "RSI > 75 for short, RSI < 25 for long",
            "candle":     "reversal candle (pin bar / engulfing) at extreme",
        },
        "sl":     "further extension (1.5x current distance from VWAP)",
        "tp":     "return to VWAP OR 1.5R fixed",
        "be_move": "0.5R",
        "valid_regimes": ["RANGING", "HIGH_VOL"],
        "invalid_regimes": ["TRENDING_UP", "TRENDING_DOWN",
                            "BREAKOUT_SETUP"],
        "instruments": ["NIFTY", "BANKNIFTY", "ALL_MIDCAP"],
        "cost_viable": True,
        "min_bars": 30,
        "warning": "FAILS on trending NIFTY — regime check critical",
    },

    "SWEEP_RETEST": {
        "description": "Liquidity sweep above/below key level → retest → reversal",
        "entry": {
            "condition":  "price sweeps above previous high/below previous low",
            "confirmation": "closes back inside range within 2 bars",
            "volume":     "sweep bar volume > 2x avg (institutional)",
            "fvg_check":  "ideally leaves a Fair Value Gap on sweep bar",
        },
        "sl":     "beyond the sweep wick (2.0x ATR)",
        "tp":     "opposite side of range / previous structure",
        "be_move": "0.8R",
        "valid_regimes": ["TRENDING_DOWN", "LOW_VOL",
                          "HIGH_VOL", "BREAKOUT_SETUP"],
        "invalid_regimes": ["CHOPPY"],
        "instruments": ["NIFTY", "BANKNIFTY"],
        "cost_viable": True,
        "min_bars": 30,
    },

    "STRUCTURE_BOUNCE": {
        "description": "Rejection at major S/R with pattern confirmation",
        "entry": {
            "condition":  "price reaches major historical S/R zone (±0.2%)",
            "pattern":    "pin bar OR inside bar rejection at zone",
            "ema_check":  "EMA20/50 confluence with S/R level (double confirmation)",
        },
        "sl":     "beyond zone (1.5x ATR through zone)",
        "tp":     "next major S/R level or 2.0R",
        "be_move": "0.7R",
        "valid_regimes": ["RANGING", "TRENDING_UP",
                          "TRENDING_DOWN", "LOW_VOL"],
        "invalid_regimes": ["VOLATILE", "CHOPPY"],
        "instruments": ["NIFTY", "BANKNIFTY", "LARGE_CAP"],
        "cost_viable": True,
        "min_bars": 50,
    },

    "CANDLESTICK": {
        "description": "Bullish/bearish engulfing at confluence zones",
        "entry": {
            "condition":  "engulfing candle at VWAP / EMA / S/R confluence",
            "size_req":   "engulfing body > previous candle body by 1.5x",
            "rsi_filter": "RSI not overbought/oversold in opposite direction",
            "volume":     "engulfing candle volume > avg",
        },
        "sl":     "below/above engulfing candle wick",
        "tp":     "1.5R fixed (short-term pattern, not trend)",
        "be_move": "0.5R",
        "valid_regimes": ["TRENDING_UP", "TRENDING_DOWN", "RANGING"],
        "invalid_regimes": ["HIGH_VOL", "VOLATILE", "CHOPPY"],
        "instruments": ["NIFTY", "BANKNIFTY", "ALL"],
        "cost_viable": True,
        "min_bars": 10,
        "note": "Best used as CONFLUENCE filter, not standalone",
    },

    "SMC_CORE": {
        "description": "Market Structure Shift + Break of Structure entries",
        "entry": {
            "condition":  "CHoCH (Change of Character) confirmed on 5m",
            "bos_filter": "BOS (Break of Structure) in direction of trade",
            "ob_entry":   "enter at Order Block that caused BOS",
            "fvg":        "Fair Value Gap present between impulse and retest",
        },
        "sl":     "below/above the Order Block origin",
        "tp":     "next opposing Order Block or liquidity pool",
        "be_move": "1.0R",
        "valid_regimes": ["TRENDING_DOWN", "TRENDING_UP",
                          "BREAKOUT_SETUP"],
        "invalid_regimes": ["RANGING", "CHOPPY"],
        "instruments": ["NIFTY", "BANKNIFTY"],
        "cost_viable": True,
        "min_bars": 50,
        "note": "Highest accuracy but lowest frequency — quality over qty",
    },

    "LIQUIDITY_TRAP": {
        "description": "Fake breakout above resistance → fade the trap",
        "entry": {
            "condition":  "price breaks above resistance → no follow-through within 3 bars → closes back below",
            "volume":     "breakout bar volume > 1.5x avg (retail chasing)",
            "wick_check": "long wick above breakout level",
        },
        "sl":     "above the fake breakout wick high",
        "tp":     "return to pre-breakout base or 2.0R",
        "be_move": "0.7R",
        "valid_regimes": ["RANGING", "TRENDING_DOWN"],
        "invalid_regimes": ["TRENDING_UP", "VOLATILE"],
        "instruments": ["BANKNIFTY", "ALL_MIDCAP"],
        "cost_viable": True,
        "min_bars": 20,
        "warning": "FAILS on NIFTY index (trends through traps). Use BANKNIFTY only.",
    },
}
