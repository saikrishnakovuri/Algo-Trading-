# Strategy routing based on regime + volatility context
STRATEGY_REGIME_MAP = {
    "TRENDING_UP": [
        "VWAP_BOUNCE",       # primary - validated #1
        "MOMENTUM_BREAKOUT", # secondary - validated #2
        "STRUCTURE_BOUNCE",  # pullback entries
        "CANDLESTICK",       # engulfing patterns
        "EMA_CROSSOVER",     # trend continuation
    ],
    "TRENDING_DOWN": [
        "VWAP_BOUNCE",       # short side
        "SWEEP_RETEST",      # liquidity sweeps
        "SMC_CORE",          # BOS/CHoCH entries
        "MOMENTUM_BREAKOUT", # continuation
        "CANDLESTICK",       # engulfing patterns
    ],
    "RANGING": [
        "STRUCTURE_BOUNCE",  # S/R bounces only
        "MEAN_REVERSION",    # ±2.5σ fades
        "CANDLESTICK",       # reversal confirmation
        "SWEEP_RETEST",      # liquidity grabs at range extremes
    ],
    "LOW_VOL": [
        "MOMENTUM_BREAKOUT", # breakout from compression
        "STRUCTURE_BOUNCE",  # tight S/R plays
        "SWEEP_RETEST",      # pre-breakout sweeps
    ],
    "HIGH_VOL": [
        "MEAN_REVERSION",    # fade extremes
        "SWEEP_RETEST",      # liquidity grabs
    ],
    "VOLATILE": [
        "SWEEP_RETEST",      # only SMC plays
        "SMC_CORE",          # institutional flow
    ],
    "CHOPPY": [],            # NO TRADE
}

# Max simultaneous strategies per regime
MAX_STRATEGIES_ACTIVE = {
    "TRENDING_UP": 4,
    "TRENDING_DOWN": 4,
    "RANGING": 3,
    "LOW_VOL": 3,
    "HIGH_VOL": 2,
    "VOLATILE": 2,
    "CHOPPY": 0,
}
